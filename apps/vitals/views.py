from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, TemplateView
from django.views.generic.edit import FormView

from django.core.paginator import Paginator

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import (
    VitalEnteredInErrorForm,
    VitalObservationForm,
)
from .models import VitalObservation


VITAL_PAGE_SIZE = 25


def is_htmx(request):
    return request.headers.get("HX-Request") == "true"


class VitalNavigationMixin:
    active_primary_nav = "clinical"
    active_clinical_module = "vitals"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "active_primary_nav": self.active_primary_nav,
                "active_clinical_module": (
                    self.active_clinical_module
                ),
            }
        )

        return context


class VitalListView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    TemplateView,
):
    """
    General vital-sign observation list.

    Supports:
    - Global vital-sign review.
    - Patient filtering.
    - Encounter filtering.
    - Search.
    - Record status filtering.
    - Date-range filtering.
    - Pagination.
    - Patient/encounter sidebar context.
    - HTMX partial rendering.
    """

    template_name = "vitals/list.html"
    partial_template_name = "vitals/partials/list_content.html"

    # ============================================================
    # TEMPLATE SELECTION
    # ============================================================

    def get_template_names(self):
        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    # ============================================================
    # PATIENT CONTEXT
    # ============================================================

    def get_selected_patient(self):
        """
        Resolve the patient from the ?patient=<uuid> query parameter.

        If an encounter is supplied without a patient parameter,
        the encounter patient is used automatically.
        """

        patient_id = self.request.GET.get(
            "patient",
            "",
        ).strip()

        encounter = self.get_active_encounter()

        if encounter:
            return encounter.patient

        if not patient_id:
            return None

        return (
            Patient.objects
            .filter(pk=patient_id)
            .first()
        )

    # ============================================================
    # ENCOUNTER CONTEXT
    # ============================================================

    def get_active_encounter(self):
        """
        Resolve encounter from ?encounter=<uuid>.
        """

        if hasattr(self, "_resolved_active_encounter"):
            return self._resolved_active_encounter

        encounter_id = self.request.GET.get(
            "encounter",
            "",
        ).strip()

        if not encounter_id:
            self._resolved_active_encounter = None
            return None

        self._resolved_active_encounter = (
            Encounter.objects
            .select_related("patient")
            .filter(pk=encounter_id)
            .first()
        )

        return self._resolved_active_encounter

    # ============================================================
    # QUERYSET
    # ============================================================

    def get_queryset(self):
        queryset = (
            VitalObservation.objects
            .select_related(
                "patient",
                "encounter",
                "recorded_by",
            )
            .all()
        )

        query = self.request.GET.get(
            "q",
            "",
        ).strip()

        status = self.request.GET.get(
            "status",
            "",
        ).strip()

        patient_id = self.request.GET.get(
            "patient",
            "",
        ).strip()

        encounter_id = self.request.GET.get(
            "encounter",
            "",
        ).strip()

        start_date = self.request.GET.get(
            "start_date",
            "",
        ).strip()

        end_date = self.request.GET.get(
            "end_date",
            "",
        ).strip()

        # --------------------------------------------------------
        # SEARCH
        # --------------------------------------------------------

        if query:
            queryset = queryset.filter(
                Q(
                    patient__mrn__icontains=query,
                )
                | Q(
                    patient__first_name__icontains=query,
                )
                | Q(
                    patient__middle_name__icontains=query,
                )
                | Q(
                    patient__last_name__icontains=query,
                )
                | Q(
                    encounter__encounter_number__icontains=query,
                )
                | Q(
                    notes__icontains=query,
                )
            )

        # --------------------------------------------------------
        # RECORD STATUS
        # --------------------------------------------------------

        if status:
            queryset = queryset.filter(
                status=status,
            )

        # --------------------------------------------------------
        # PATIENT
        # --------------------------------------------------------

        if patient_id:
            queryset = queryset.filter(
                patient_id=patient_id,
            )

        # --------------------------------------------------------
        # ENCOUNTER
        # --------------------------------------------------------

        if encounter_id:
            queryset = queryset.filter(
                encounter_id=encounter_id,
            )

        # --------------------------------------------------------
        # DATE RANGE
        # --------------------------------------------------------

        if start_date:
            queryset = queryset.filter(
                recorded_at__date__gte=start_date,
            )

        if end_date:
            queryset = queryset.filter(
                recorded_at__date__lte=end_date,
            )

        return queryset.order_by(
            "-recorded_at",
            "-created_at",
        )

    # ============================================================
    # CONTEXT
    # ============================================================

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        selected_patient = self.get_selected_patient()
        active_encounter = self.get_active_encounter()

        paginator = Paginator(
            queryset,
            VITAL_PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            self.request.GET.get("page"),
        )

        # --------------------------------------------------------
        # PAGE TITLE
        # --------------------------------------------------------

        if active_encounter:
            page_title = "Encounter Vital Signs"

            page_description = (
                "Vital signs recorded during encounter "
                f"{active_encounter.encounter_number}."
            )

        elif selected_patient:
            page_title = "Patient Vital Signs"

            page_description = (
                "Review recorded vital signs for "
                f"{selected_patient.display_name}."
            )

        else:
            page_title = "Vital Signs"

            page_description = (
                "Review and manage recorded patient vital signs."
            )

        # --------------------------------------------------------
        # CONTEXT
        # --------------------------------------------------------

        context.update(
            {
                # Page
                "page_title": page_title,
                "page_description": page_description,

                # Navigation
                "active_primary_nav": "clinical",
                "active_clinical_module": "vitals",

                # Patient / encounter
                "selected_patient": selected_patient,
                "patient": selected_patient,
                "active_encounter": active_encounter,
                "encounter": active_encounter,

                # Keep encounter section highlighted
                "active_encounter_module": (
                    "vitals"
                    if active_encounter
                    else None
                ),

                # Keep historical Vitals highlighted
                "active_patient_section": (
                    "vitals"
                    if selected_patient
                    and not active_encounter
                    else None
                ),

                # Vital observations
                "vital_observations": page_obj.object_list,

                # Pagination
                "page_obj": page_obj,
                "paginator": paginator,

                # Filters
                "status_choices": (
                    VitalObservation.RecordStatus.choices
                ),

                "current_query": self.request.GET.get(
                    "q",
                    "",
                ),

                "current_status": self.request.GET.get(
                    "status",
                    "",
                ),

                "current_start_date": self.request.GET.get(
                    "start_date",
                    "",
                ),

                "current_end_date": self.request.GET.get(
                    "end_date",
                    "",
                ),

                "current_patient": self.request.GET.get(
                    "patient",
                    "",
                ),

                "current_encounter": self.request.GET.get(
                    "encounter",
                    "",
                ),
            }
        )

        return context


class VitalDetailView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    DetailView,
):
    model = VitalObservation
    context_object_name = "vital"
    template_name = "vitals/detail.html"
    partial_template_name = "vitals/partials/detail_content.html"

    def get_queryset(self):
        return (
            VitalObservation.objects
            .select_related(
                "patient",
                "encounter",
                "recorded_by",
                "entered_in_error_by",
            )
        )

    def get_template_names(self):
        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "page_title": "Vital Sign Details",
                "selected_patient": self.object.patient,
                "active_encounter": self.object.encounter,
            }
        )

        return context


class VitalFormMixin:
    model = VitalObservation
    form_class = VitalObservationForm
    template_name = "vitals/form.html"
    partial_template_name = "vitals/partials/vital_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    def get_patient(self):
        patient_id = (
            self.request.GET.get("patient")
            or self.request.POST.get("patient")
        )

        if not patient_id:
            return None

        return Patient.objects.filter(
            pk=patient_id,
        ).first()

    def get_encounter(self):
        encounter_id = (
            self.request.GET.get("encounter")
            or self.request.POST.get("encounter")
        )

        if not encounter_id:
            return None

        return (
            Encounter.objects
            .select_related("patient")
            .filter(pk=encounter_id)
            .first()
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update(
            {
                "current_user": self.request.user,
                "patient": self.get_patient(),
                "encounter": self.get_encounter(),
            }
        )

        return kwargs

    def render_invalid_form(self, form):
        context = self.get_context_data(form=form)

        return self.render_to_response(
            context,
            status=200,
        )


class VitalCreateView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    VitalFormMixin,
    FormView,
):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        patient = self.get_patient()
        encounter = self.get_encounter()

        context.update(
            {
                "page_title": "Record Vital Signs",
                "page_description": (
                    "Record current clinical measurements for the patient."
                ),
                "form_mode": "create",
                "submit_label": "Save Vital Signs",
                "selected_patient": (
                    encounter.patient
                    if encounter
                    else patient
                ),
                "active_encounter": encounter,
            }
        )

        return context

    @transaction.atomic
    def form_valid(self, form):
        vital = form.save(commit=False)
        vital.save(actor=self.request.user)

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "vitalCreated"
            response["HX-Redirect"] = vital.get_absolute_url()
            return response

        return redirect(vital.get_absolute_url())

    def form_invalid(self, form):
        return self.render_invalid_form(form)


class VitalUpdateView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    VitalFormMixin,
    FormView,
):
    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            VitalObservation.objects.select_related(
                "patient",
                "encounter",
            ),
            pk=kwargs["pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.object
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "page_title": "Update Vital Signs",
                "page_description": (
                    "Correct or update the recorded vital-sign values."
                ),
                "form_mode": "update",
                "submit_label": "Save Changes",
                "vital": self.object,
                "selected_patient": self.object.patient,
                "active_encounter": self.object.encounter,
            }
        )

        return context

    @transaction.atomic
    def form_valid(self, form):
        vital = form.save(commit=False)

        if vital.status != (
            VitalObservation.RecordStatus.ENTERED_IN_ERROR
        ):
            vital.status = (
                VitalObservation.RecordStatus.CORRECTED
            )

        vital.save(actor=self.request.user)

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "vitalUpdated"
            response["HX-Redirect"] = vital.get_absolute_url()
            return response

        return redirect(vital.get_absolute_url())

    def form_invalid(self, form):
        return self.render_invalid_form(form)


class VitalEnteredInErrorView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    FormView,
):
    form_class = VitalEnteredInErrorForm
    template_name = "vitals/confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        self.object = get_object_or_404(
            VitalObservation.objects.select_related(
                "patient",
                "encounter",
            ),
            pk=kwargs["pk"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "page_title": "Mark Vital Signs Entered in Error",
                "vital": self.object,
                "selected_patient": self.object.patient,
                "active_encounter": self.object.encounter,
            }
        )

        return context

    @transaction.atomic
    def form_valid(self, form):
        self.object.mark_entered_in_error(
            self.request.user,
            form.cleaned_data["reason"],
        )

        if is_htmx(self.request):
            response = HttpResponse(status=204)
            response["HX-Trigger"] = "vitalEnteredInError"
            response["HX-Redirect"] = self.object.get_absolute_url()
            return response

        return redirect(self.object.get_absolute_url())


class PatientVitalHistoryView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    TemplateView,
):
    """
    Longitudinal vital-sign history for one patient.
    """

    template_name = "vitals/list.html"
    partial_template_name = "vitals/partials/list_content.html"

    def dispatch(self, request, *args, **kwargs):
        self.patient = get_object_or_404(
            Patient,
            pk=kwargs["patient_id"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_template_names(self):
        if is_htmx(self.request):
            return [self.partial_template_name]

        return [self.template_name]

    def get_queryset(self):
        return (
            VitalObservation.objects
            .select_related(
                "patient",
                "encounter",
                "recorded_by",
            )
            .filter(
                patient=self.patient,
            )
            .order_by(
                "-recorded_at",
                "-created_at",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        paginator = Paginator(
            queryset,
            VITAL_PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            self.request.GET.get("page"),
        )

        context.update(
            {
                "page_title": "Vital Sign History",

                "page_description": (
                    "Longitudinal vital-sign history for "
                    f"{self.patient.display_name}."
                ),

                # Navigation
                "active_primary_nav": "clinical",
                "active_clinical_module": "vitals",
                "active_patient_section": "vitals",

                # Patient
                "selected_patient": self.patient,
                "patient": self.patient,

                # Do not pretend there is an active encounter
                "active_encounter": None,
                "encounter": None,

                # Table data
                "vital_observations": page_obj.object_list,

                # Pagination
                "page_obj": page_obj,
                "paginator": paginator,

                "status_choices": (
                    VitalObservation.RecordStatus.choices
                ),

                "current_query": self.request.GET.get(
                    "q",
                    "",
                ),

                "current_status": self.request.GET.get(
                    "status",
                    "",
                ),
            }
        )

        return context


class EncounterVitalListView(
    LoginRequiredMixin,
    VitalNavigationMixin,
    TemplateView,
):
    """
    Display vital-sign observations associated with one encounter.

    Provides:
    - Encounter context
    - Patient context
    - Clinical sidebar context
    - Pagination
    - HTMX list refresh
    """

    template_name = "vitals/list.html"
    partial_template_name = "vitals/partials/list_content.html"

    # ============================================================
    # ENCOUNTER RESOLUTION
    # ============================================================

    def dispatch(self, request, *args, **kwargs):
        self.encounter = get_object_or_404(
            Encounter.objects.select_related(
                "patient",
            ),
            pk=kwargs["encounter_id"],
        )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    # ============================================================
    # TEMPLATE SELECTION
    # ============================================================

    def get_template_names(self):
        if is_htmx(self.request):
            return [
                self.partial_template_name,
            ]

        return [
            self.template_name,
        ]

    # ============================================================
    # QUERYSET
    # ============================================================

    def get_queryset(self):
        return (
            VitalObservation.objects
            .select_related(
                "patient",
                "encounter",
                "recorded_by",
            )
            .filter(
                encounter_id=self.encounter.pk,
            )
            .order_by(
                "-recorded_at",
                "-created_at",
            )
        )

    # ============================================================
    # CONTEXT
    # ============================================================

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset = self.get_queryset()

        paginator = Paginator(
            queryset,
            VITAL_PAGE_SIZE,
        )

        page_obj = paginator.get_page(
            self.request.GET.get("page")
        )

        context.update(
            {
                # ------------------------------------------------
                # PAGE
                # ------------------------------------------------
                "page_title": "Encounter Vital Signs",

                "page_description": (
                    "Vital signs recorded during encounter "
                    f"{self.encounter.encounter_number}."
                ),

                # ------------------------------------------------
                # CLINICAL NAVIGATION
                # ------------------------------------------------
                "active_primary_nav": "clinical",
                "active_clinical_module": "vitals",
                "active_encounter_module": "vitals",
                "active_patient_section": None,

                # ------------------------------------------------
                # PATIENT
                # ------------------------------------------------
                "selected_patient": self.encounter.patient,
                "patient": self.encounter.patient,

                # ------------------------------------------------
                # ENCOUNTER
                # ------------------------------------------------
                "active_encounter": self.encounter,
                "encounter": self.encounter,

                # ------------------------------------------------
                # VITAL DATA
                # ------------------------------------------------
                "vital_observations": page_obj.object_list,

                # ------------------------------------------------
                # PAGINATION
                # ------------------------------------------------
                "page_obj": page_obj,
                "paginator": paginator,

                # ------------------------------------------------
                # FILTER SUPPORT
                # ------------------------------------------------
                "status_choices": (
                    VitalObservation.RecordStatus.choices
                ),

                "current_query": self.request.GET.get(
                    "q",
                    "",
                ),

                "current_status": self.request.GET.get(
                    "status",
                    "",
                ),

                "current_start_date": self.request.GET.get(
                    "start_date",
                    "",
                ),

                "current_end_date": self.request.GET.get(
                    "end_date",
                    "",
                ),
            }
        )

        return context