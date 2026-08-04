"""
Liberia EHR Encounter Views

File:
apps/encounters/views.py

Purpose:
- Display, search, create, update, complete, cancel, and delete encounters.
- Pass the authenticated user to encounter workflow operations.
- Provide selected-patient and active-encounter context to the sidebar.
- Allow the Encounter model to automatically generate workflow timestamps,
  recorder fields, encounter numbers, and active-state changes.
- Support full-page and HTMX workspace responses.

Important:
- Encounter uses a UUID primary key.
- Creation and update modes are passed explicitly to EncounterForm.
- New encounters are saved with:

      encounter.save(actor=request.user)
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    UpdateView,
)

from apps.patients.models import Patient

from .forms import EncounterForm
from .models import Encounter


# =====================================================================
# SHARED ENCOUNTER WORKFLOW VALUES
# =====================================================================


OPEN_ENCOUNTER_STATUSES = {
    Encounter.EncounterStatus.PLANNED,
    Encounter.EncounterStatus.SCHEDULED,
    Encounter.EncounterStatus.ARRIVED,
    Encounter.EncounterStatus.TRIAGED,
    Encounter.EncounterStatus.IN_PROGRESS,
    Encounter.EncounterStatus.ON_HOLD,
}


TERMINAL_ENCOUNTER_STATUSES = {
    Encounter.EncounterStatus.COMPLETED,
    Encounter.EncounterStatus.CANCELLED,
    Encounter.EncounterStatus.ENTERED_IN_ERROR,
}


# =====================================================================
# NAVIGATION CONTEXT
# =====================================================================


class EncounterNavigationMixin:
    """
    Provide navigation context required by layouts/app_shell.html.
    """

    active_primary_nav = "clinical"
    active_clinical_module = "encounters"
    active_encounter_module = ""

    def get_context_data(self, **kwargs):
        """
        Add encounter navigation values to the template context.
        """

        context = super().get_context_data(**kwargs)

        context.update(
            {
                "active_primary_nav": self.active_primary_nav,
                "active_clinical_module": self.active_clinical_module,
                "active_encounter_module": self.active_encounter_module,
            }
        )

        return context


# =====================================================================
# HTMX TEMPLATE SUPPORT
# =====================================================================


class HTMXTemplateMixin:
    """
    Return a partial template for HTMX requests when one is configured.
    """

    htmx_template_name = None

    def get_template_names(self):
        """
        Select the full-page or HTMX partial template.
        """

        is_htmx = self.request.headers.get("HX-Request") == "true"

        if is_htmx and self.htmx_template_name:
            return [self.htmx_template_name]

        return super().get_template_names()


# =====================================================================
# VALIDATION SUPPORT
# =====================================================================


class EncounterValidationMixin:
    """
    Transfer model ValidationError messages to the encounter form.
    """

    def add_validation_errors_to_form(self, form, exception):
        """
        Add model validation errors to the form safely.

        Errors associated with automatic model fields are converted into
        non-field errors because those fields are intentionally excluded
        from EncounterForm.
        """

        if hasattr(exception, "message_dict"):
            for field_name, error_messages in exception.message_dict.items():
                if isinstance(error_messages, str):
                    error_messages = [error_messages]

                for error_message in error_messages:
                    if field_name in form.fields:
                        form.add_error(
                            field_name,
                            error_message,
                        )
                    else:
                        form.add_error(
                            None,
                            error_message,
                        )

            return

        error_messages = getattr(
            exception,
            "messages",
            [str(exception)],
        )

        for error_message in error_messages:
            form.add_error(
                None,
                error_message,
            )

            return

        error_messages = getattr(
            exception,
            "messages",
            [str(exception)],
        )

        for error_message in error_messages:
            form.add_error(
                None,
                error_message,
            )

    @staticmethod
    def validation_message(exception):
        """
        Return a readable message for Django messages.
        """

        if hasattr(exception, "message_dict"):
            messages_list = []

            for field_messages in exception.message_dict.values():
                if isinstance(field_messages, str):
                    messages_list.append(field_messages)
                else:
                    messages_list.extend(field_messages)

            return " ".join(messages_list)

        if hasattr(exception, "messages"):
            return " ".join(exception.messages)

        return str(exception)


# =====================================================================
# PATIENT AND SIDEBAR CONTEXT SUPPORT
# =====================================================================


class EncounterPatientContextMixin:
    """
    Resolve selected patient and active encounter information.

    The selected patient may come from:
    - ?patient=<patient UUID>
    - self.object.patient
    - a submitted form patient value
    """

    selected_patient = None

    def get_patient_id_from_request(self):
        """
        Return the patient identifier from GET or POST.
        """

        return (
            self.request.GET.get("patient")
            or self.request.POST.get("patient")
            or ""
        ).strip()

    def get_selected_patient(self):
        """
        Return the selected patient, when available.
        """

        if self.selected_patient is not None:
            return self.selected_patient

        if getattr(self, "object", None) is not None:
            object_patient = getattr(
                self.object,
                "patient",
                None,
            )

            if object_patient is not None:
                self.selected_patient = object_patient
                return self.selected_patient

        patient_id = self.get_patient_id_from_request()

        if not patient_id:
            return None

        self.selected_patient = get_object_or_404(
            Patient,
            pk=patient_id,
        )

        return self.selected_patient

    def get_active_encounter_for_patient(
        self,
        patient,
        exclude_pk=None,
    ):
        """
        Return the patient's most recent active, open encounter.
        """

        if patient is None:
            return None

        queryset = Encounter.objects.filter(
            patient=patient,
            is_active=True,
            status__in=OPEN_ENCOUNTER_STATUSES,
        ).select_related(
            "patient",
            "attending_provider",
            "created_by",
        )

        if exclude_pk:
            queryset = queryset.exclude(
                pk=exclude_pk,
            )

        return queryset.order_by(
            "-start_datetime",
            "-created_at",
        ).first()

    def get_patient_sidebar_context(
        self,
        patient=None,
        active_encounter=None,
        active_patient_section=None,
    ):
        """
        Build patient-sidebar template context.
        """

        patient = patient or self.get_selected_patient()

        if active_encounter is None and patient is not None:
            active_encounter = self.get_active_encounter_for_patient(
                patient,
            )

        return {
            "selected_patient": patient,
            "active_encounter": active_encounter,
            "active_patient_section": active_patient_section,
        }


# =====================================================================
# ENCOUNTER LIST
# =====================================================================


class EncounterListView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    EncounterPatientContextMixin,
    HTMXTemplateMixin,
    ListView,
):
    """
    Display and filter encounter records.
    """

    model = Encounter
    template_name = "encounters/encounter_list.html"
    htmx_template_name = "encounters/partials/list_content.html"
    context_object_name = "encounters"
    paginate_by = 25
    active_encounter_module = "list"

    def get_queryset(self):
        """
        Return encounters matching patient, search, and filter values.
        """

        queryset = Encounter.objects.select_related(
            "patient",
            "attending_provider",
            "created_by",
            "registered_by",
            "identity_verified_by",
            "check_in_user",
            "triaged_by",
            "clinical_started_by",
            "completed_by",
            "cancelled_by",
            "entered_in_error_by",
        )

        selected_patient = self.get_selected_patient()

        if selected_patient:
            queryset = queryset.filter(
                patient=selected_patient,
            )

        query = self.request.GET.get(
            "q",
            "",
        ).strip()

        status = self.request.GET.get(
            "status",
            "",
        ).strip()

        encounter_type = self.request.GET.get(
            "encounter_type",
            "",
        ).strip()

        priority = self.request.GET.get(
            "priority",
            "",
        ).strip()

        # -------------------------------------------------------------
        # FREE-TEXT SEARCH
        # -------------------------------------------------------------

        if query:
            queryset = queryset.filter(
                Q(encounter_number__icontains=query)
                | Q(reason_for_visit__icontains=query)
                | Q(patient__first_name__icontains=query)
                | Q(patient__middle_name__icontains=query)
                | Q(patient__last_name__icontains=query)
                | Q(patient__preferred_name__icontains=query)
            )

        # -------------------------------------------------------------
        # STATUS FILTER
        # -------------------------------------------------------------

        valid_statuses = {
            value
            for value, _ in Encounter.EncounterStatus.choices
        }

        if status in valid_statuses:
            queryset = queryset.filter(
                status=status,
            )

        # -------------------------------------------------------------
        # ENCOUNTER TYPE FILTER
        # -------------------------------------------------------------

        valid_encounter_types = {
            value
            for value, _ in Encounter.EncounterType.choices
        }

        if encounter_type in valid_encounter_types:
            queryset = queryset.filter(
                encounter_type=encounter_type,
            )

        # -------------------------------------------------------------
        # PRIORITY FILTER
        # -------------------------------------------------------------

        valid_priorities = {
            value
            for value, _ in Encounter.Priority.choices
        }

        if priority in valid_priorities:
            queryset = queryset.filter(
                priority=priority,
            )

        return queryset.order_by(
            "-start_datetime",
            "-created_at",
        )

    def get_context_data(self, **kwargs):
        """
        Add filters, counts, selected patient, and active encounter.
        """

        context = super().get_context_data(**kwargs)

        selected_patient = self.get_selected_patient()

        summary_queryset = Encounter.objects.all()

        if selected_patient:
            summary_queryset = summary_queryset.filter(
                patient=selected_patient,
            )

        active_encounter = self.get_active_encounter_for_patient(
            selected_patient,
        )

        context.update(
            {
                "page_title": (
                    f"Encounters — {selected_patient}"
                    if selected_patient
                    else "Encounters"
                ),
                "search_query": self.request.GET.get(
                    "q",
                    "",
                ),
                "selected_status": self.request.GET.get(
                    "status",
                    "",
                ),
                "selected_encounter_type": self.request.GET.get(
                    "encounter_type",
                    "",
                ),
                "selected_priority": self.request.GET.get(
                    "priority",
                    "",
                ),
                "encounter_status_choices": (
                    Encounter.EncounterStatus.choices
                ),
                "encounter_type_choices": (
                    Encounter.EncounterType.choices
                ),
                "priority_choices": Encounter.Priority.choices,
                "total_encounters": summary_queryset.count(),
                "open_encounters": summary_queryset.filter(
                    status__in=OPEN_ENCOUNTER_STATUSES,
                    is_active=True,
                ).count(),
                "completed_encounters": summary_queryset.filter(
                    status=Encounter.EncounterStatus.COMPLETED,
                ).count(),
                "today_encounters": summary_queryset.filter(
                    start_datetime__date=timezone.localdate(),
                ).count(),
                "selected_patient": selected_patient,
                "active_encounter": active_encounter,
                "active_patient_section": "encounters",
            }
        )

        return context


# =====================================================================
# ENCOUNTER DETAIL
# =====================================================================


class EncounterDetailView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    EncounterPatientContextMixin,
    HTMXTemplateMixin,
    DetailView,
):
    """
    Display one encounter and its related clinical information.
    """

    model = Encounter
    template_name = "encounters/encounter_detail.html"
    htmx_template_name = "encounters/partials/detail_content.html"
    context_object_name = "encounter"
    active_encounter_module = "detail"

    def get_queryset(self):
        """
        Load the encounter and commonly displayed related objects.
        """

        return Encounter.objects.select_related(
            "patient",
            "attending_provider",
            "created_by",
            "registered_by",
            "identity_verified_by",
            "check_in_user",
            "triaged_by",
            "clinical_started_by",
            "completed_by",
            "cancelled_by",
            "entered_in_error_by",
        ).prefetch_related(
            "diagnoses",
            "diagnoses__concept",
        )

    def get_context_data(self, **kwargs):
        """
        Provide the patient, active encounter, and selected sidebar section.
        """

        context = super().get_context_data(**kwargs)

        requested_section = self.request.GET.get(
            "section",
            "summary",
        ).strip()

        allowed_sections = {
            "summary",
            "triage",
            "vitals",
            "notes",
            "diagnoses",
            "orders",
            "laboratory",
            "imaging",
            "medications",
            "flowsheets",
            "care-plan",
        }

        if requested_section not in allowed_sections:
            requested_section = "summary"

        context.update(
            {
                "page_title": (
                    f"Encounter {self.object.encounter_number}"
                ),
                "selected_patient": self.object.patient,
                "active_encounter": self.object,
                "active_patient_section": requested_section,
            }
        )

        return context


# =====================================================================
# ENCOUNTER CREATE
# =====================================================================


class EncounterCreateView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    EncounterPatientContextMixin,
    EncounterValidationMixin,
    CreateView,
):
    """
    Create a new patient encounter.

    Staff enter only clinically relevant information. Generated fields
    are populated by Encounter.save(actor=request.user).
    """

    model = Encounter
    form_class = EncounterForm
    template_name = "encounters/form.html"
    active_encounter_module = "create"

    def get_initial(self):
        """
        Preselect a patient supplied by the patient sidebar.
        """

        initial = super().get_initial()
        selected_patient = self.get_selected_patient()

        if selected_patient:
            initial["patient"] = selected_patient.pk

        return initial

    def get_form_kwargs(self):
        """
        Pass the authenticated user and explicit create mode.
        """

        kwargs = super().get_form_kwargs()

        kwargs["current_user"] = self.request.user
        kwargs["form_mode"] = "create"

        return kwargs

    def get_context_data(self, **kwargs):
        """
        Add explicit create-mode and patient-sidebar context.
        """

        context = super().get_context_data(**kwargs)

        selected_patient = self.get_selected_patient()

        existing_active_encounter = (
            self.get_active_encounter_for_patient(
                selected_patient,
            )
        )

        context.update(
            {
                "page_title": "Start Encounter",
                "selected_patient": selected_patient,
                "active_encounter": existing_active_encounter,
                "active_patient_section": "encounters",
                "is_create": True,
                "is_update": False,
                "submit_label": "Create Encounter",
            }
        )

        return context

    def form_valid(self, form):
        """
        Save the encounter once using the authenticated workflow actor.
        """

        self.object = form.save(
            commit=False,
        )

        selected_patient = self.get_selected_patient()

        if selected_patient:
            self.object.patient = selected_patient

        # -------------------------------------------------------------
        # PREVENT DUPLICATE OPEN ENCOUNTERS
        # -------------------------------------------------------------

        existing_active_encounter = (
            self.get_active_encounter_for_patient(
                self.object.patient,
            )
        )

        if existing_active_encounter:
            form.add_error(
                None,
                (
                    "This patient already has an active encounter: "
                    f"{existing_active_encounter.encounter_number}. "
                    "Open or update the existing encounter instead."
                ),
            )

            return self.form_invalid(form)

        # -------------------------------------------------------------
        # SAVE NEW ENCOUNTER
        # -------------------------------------------------------------

        try:
            with transaction.atomic():
                self.object.save(
                    actor=self.request.user,
                )

                form.save_m2m()

        except ValidationError as exception:
            self.add_validation_errors_to_form(
                form,
                exception,
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Encounter {self.object.encounter_number} "
                "was created successfully."
            ),
        )

        return HttpResponseRedirect(
            self.get_success_url()
        )

    def form_invalid(self, form):
        """
        Redisplay the create form with explicit create-mode context.
        """

        self.object = None

        return self.render_to_response(
            self.get_context_data(
                form=form,
            )
        )

    def get_success_url(self):
        """
        Redirect to the newly created encounter.
        """

        return reverse(
            "encounters:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )


# =====================================================================
# ENCOUNTER UPDATE
# =====================================================================


class EncounterUpdateView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    EncounterPatientContextMixin,
    EncounterValidationMixin,
    UpdateView,
):
    """
    Update an existing encounter.

    Workflow changes are saved with the authenticated user so the model
    can populate recorder and timestamp fields.
    """

    model = Encounter
    form_class = EncounterForm
    template_name = "encounters/form.html"
    context_object_name = "encounter"
    active_encounter_module = "update"

    def get_queryset(self):
        """
        Load related patient and workflow information.
        """

        return Encounter.objects.select_related(
            "patient",
            "attending_provider",
            "created_by",
            "registered_by",
            "identity_verified_by",
            "check_in_user",
            "triaged_by",
            "clinical_started_by",
            "completed_by",
            "cancelled_by",
            "entered_in_error_by",
        )

    def get_form_kwargs(self):
        """
        Pass the authenticated user and explicit update mode.
        """

        kwargs = super().get_form_kwargs()

        kwargs["current_user"] = self.request.user
        kwargs["form_mode"] = "update"

        return kwargs

    def get_context_data(self, **kwargs):
        """
        Add explicit update-mode and patient-sidebar context.
        """

        context = super().get_context_data(**kwargs)

        encounter = self.object

        context.update(
            {
                "page_title": (
                    f"Update Encounter {encounter.encounter_number}"
                ),
                "selected_patient": encounter.patient,
                "active_encounter": encounter,
                "active_patient_section": "encounters",
                "is_create": False,
                "is_update": True,
                "submit_label": "Save Changes",
            }
        )

        return context

    def form_valid(self, form):
        """
        Save the encounter update with the authenticated workflow actor.
        """

        self.object = form.save(
            commit=False,
        )

        try:
            with transaction.atomic():
                self.object.save(
                    actor=self.request.user,
                )

                form.save_m2m()

        except ValidationError as exception:
            self.add_validation_errors_to_form(
                form,
                exception,
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (
                f"Encounter {self.object.encounter_number} "
                "was updated successfully."
            ),
        )

        return HttpResponseRedirect(
            self.get_success_url()
        )

    def form_invalid(self, form):
        """
        Redisplay the update form with explicit update-mode context.
        """

        return self.render_to_response(
            self.get_context_data(
                form=form,
            )
        )

    def get_success_url(self):
        """
        Redirect to the updated encounter.
        """

        return reverse(
            "encounters:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )


# =====================================================================
# COMPLETE ENCOUNTER
# =====================================================================


class EncounterCompleteView(
    LoginRequiredMixin,
    EncounterValidationMixin,
    View,
):
    """
    Complete and close an encounter.
    """

    http_method_names = [
        "post",
    ]

    def post(self, request, pk):
        """
        Complete the selected encounter.
        """

        encounter = get_object_or_404(
            Encounter,
            pk=pk,
        )

        if encounter.status == Encounter.EncounterStatus.COMPLETED:
            messages.info(
                request,
                (
                    f"Encounter {encounter.encounter_number} "
                    "is already completed."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        if encounter.status in {
            Encounter.EncounterStatus.CANCELLED,
            Encounter.EncounterStatus.ENTERED_IN_ERROR,
        }:
            messages.error(
                request,
                (
                    "A cancelled encounter or an encounter entered in "
                    "error cannot be completed."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        try:
            with transaction.atomic():
                encounter.complete(
                    user=request.user,
                )

        except ValidationError as exception:
            messages.error(
                request,
                self.validation_message(exception),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        messages.success(
            request,
            (
                f"Encounter {encounter.encounter_number} "
                "was completed successfully."
            ),
        )

        return redirect(
            "encounters:detail",
            pk=encounter.pk,
        )


# =====================================================================
# CANCEL ENCOUNTER
# =====================================================================


class EncounterCancelView(
    LoginRequiredMixin,
    EncounterValidationMixin,
    View,
):
    """
    Cancel an encounter and record the responsible user and reason.
    """

    http_method_names = [
        "post",
    ]

    def post(self, request, pk):
        """
        Cancel the selected encounter.
        """

        encounter = get_object_or_404(
            Encounter,
            pk=pk,
        )

        if encounter.status == Encounter.EncounterStatus.COMPLETED:
            messages.error(
                request,
                "A completed encounter cannot be cancelled.",
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        if encounter.status == Encounter.EncounterStatus.CANCELLED:
            messages.info(
                request,
                (
                    f"Encounter {encounter.encounter_number} "
                    "is already cancelled."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        if (
            encounter.status
            == Encounter.EncounterStatus.ENTERED_IN_ERROR
        ):
            messages.error(
                request,
                (
                    "An encounter entered in error cannot also be "
                    "cancelled."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        cancellation_reason = (
            request.POST.get("status_reason")
            or request.POST.get("reason")
            or ""
        ).strip()

        if not cancellation_reason:
            messages.error(
                request,
                "Enter a reason before cancelling the encounter.",
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        try:
            with transaction.atomic():
                encounter.cancel(
                    user=request.user,
                    reason=cancellation_reason,
                )

        except ValidationError as exception:
            messages.error(
                request,
                self.validation_message(exception),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        messages.success(
            request,
            (
                f"Encounter {encounter.encounter_number} "
                "was cancelled successfully."
            ),
        )

        return redirect(
            "encounters:detail",
            pk=encounter.pk,
        )


# =====================================================================
# MARK ENCOUNTER ENTERED IN ERROR
# =====================================================================


class EncounterEnteredInErrorView(
    LoginRequiredMixin,
    EncounterValidationMixin,
    View,
):
    """
    Mark an encounter as entered in error without deleting it.
    """

    http_method_names = [
        "post",
    ]

    def post(self, request, pk):
        """
        Mark the selected encounter as entered in error.
        """

        encounter = get_object_or_404(
            Encounter,
            pk=pk,
        )

        if (
            encounter.status
            == Encounter.EncounterStatus.ENTERED_IN_ERROR
        ):
            messages.info(
                request,
                (
                    f"Encounter {encounter.encounter_number} "
                    "is already marked as entered in error."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        error_reason = (
            request.POST.get("status_reason")
            or request.POST.get("reason")
            or ""
        ).strip()

        if not error_reason:
            messages.error(
                request,
                (
                    "Enter a reason before marking the encounter "
                    "as entered in error."
                ),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        try:
            with transaction.atomic():
                encounter.mark_entered_in_error(
                    user=request.user,
                    reason=error_reason,
                )

        except ValidationError as exception:
            messages.error(
                request,
                self.validation_message(exception),
            )

            return redirect(
                "encounters:detail",
                pk=encounter.pk,
            )

        messages.success(
            request,
            (
                f"Encounter {encounter.encounter_number} "
                "was marked as entered in error."
            ),
        )

        return redirect(
            "encounters:detail",
            pk=encounter.pk,
        )


# =====================================================================
# DELETE ENCOUNTER
# =====================================================================


class EncounterDeleteView(
    LoginRequiredMixin,
    EncounterNavigationMixin,
    EncounterPatientContextMixin,
    DeleteView,
):
    """
    Permanently delete an encounter.

    Clinical records should normally be marked entered in error rather
    than deleted. Permanent deletion should be restricted through your
    authorization system.
    """

    model = Encounter
    template_name = "encounters/confirm_delete.html"
    context_object_name = "encounter"
    active_encounter_module = "delete"

    def get_queryset(self):
        """
        Load patient and creator information.
        """

        return Encounter.objects.select_related(
            "patient",
            "created_by",
        )

    def get_context_data(self, **kwargs):
        """
        Add patient-sidebar and deletion context.
        """

        context = super().get_context_data(**kwargs)

        encounter = self.object

        alternative_active_encounter = (
            self.get_active_encounter_for_patient(
                encounter.patient,
                exclude_pk=encounter.pk,
            )
        )

        context.update(
            {
                "page_title": (
                    f"Delete Encounter {encounter.encounter_number}"
                ),
                "selected_patient": encounter.patient,
                "active_encounter": alternative_active_encounter,
                "active_patient_section": "encounters",
            }
        )

        return context

    def get_success_url(self):
        """
        Return to the deleted encounter's patient history.
        """

        return (
            reverse("encounters:list")
            + f"?patient={self.object.patient_id}"
        )

    def form_valid(self, form):
        """
        Permanently delete the encounter after confirmation.
        """

        encounter_number = self.object.encounter_number
        patient_id = self.object.patient_id

        with transaction.atomic():
            response = super().form_valid(form)

        messages.success(
            self.request,
            f"Encounter {encounter_number} was permanently deleted.",
        )

        self.success_url = (
            reverse("encounters:list")
            + f"?patient={patient_id}"
        )

        return response