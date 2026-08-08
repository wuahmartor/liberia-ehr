"""
============================================================
CLINICAL NOTES VIEWS

File:
apps/clinical_notes/views.py

Purpose:
- Display patient clinical note history.
- Create and update draft notes.
- Display signed documentation.
- Electronically sign draft notes.
- Maintain selected patient and encounter context.
- Support HTMX partial rendering.
============================================================
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import ClinicalNoteForm
from .models import ClinicalNote


# ============================================================
# HTMX HELPERS
# ============================================================

def is_htmx(request):
    """
    Return True when the request was initiated by HTMX.
    """

    return request.headers.get("HX-Request") == "true"


# ============================================================
# NAVIGATION / CONTEXT MIXIN
# ============================================================

class ClinicalNoteNavigationMixin:
    """
    Shared navigation context for Clinical Notes.
    """

    active_primary_nav = "clinical"
    active_clinical_module = "clinical_notes"

    def get_navigation_context(self):
        return {
            "active_primary_nav": self.active_primary_nav,
            "active_clinical_module": self.active_clinical_module,
        }


# ============================================================
# PATIENT CONTEXT MIXIN
# ============================================================

class PatientClinicalNoteMixin:
    """
    Resolve patient and active encounter context.
    """

    patient = None
    active_encounter = None

    def get_patient(self):
        if self.patient is not None:
            return self.patient

        patient_pk = self.kwargs.get("patient_pk")

        if patient_pk is not None:
            self.patient = get_object_or_404(
                Patient,
                pk=patient_pk,
            )

            return self.patient

        note = getattr(self, "object", None)

        if note is not None:
            self.patient = note.patient
            return self.patient

        return None

    def get_active_encounter(self):
        if self.active_encounter is not None:
            return self.active_encounter

        patient = self.get_patient()

        if patient is None:
            return None

        # ----------------------------------------------------
        # EXPLICIT ENCOUNTER QUERY PARAMETER
        # ----------------------------------------------------

        encounter_id = self.request.GET.get("encounter")

        if encounter_id:
            self.active_encounter = (
                Encounter.objects
                .filter(
                    pk=encounter_id,
                    patient=patient,
                )
                .first()
            )

            if self.active_encounter:
                return self.active_encounter

        # ----------------------------------------------------
        # NOTE ENCOUNTER
        # ----------------------------------------------------

        note = getattr(self, "object", None)

        if note is not None and note.encounter_id:
            self.active_encounter = note.encounter
            return self.active_encounter

        # ----------------------------------------------------
        # CURRENT OPEN ENCOUNTER
        #
        # Avoid depending on a specific enumeration name.
        # Prefer active encounters without an end date.
        # ----------------------------------------------------

        self.active_encounter = (
            Encounter.objects
            .filter(
                patient=patient,
                is_active=True,
            )
            .order_by("-start_datetime")
            .first()
        )

        return self.active_encounter

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            self.get_navigation_context()
        )

        context["selected_patient"] = self.get_patient()
        context["active_encounter"] = self.get_active_encounter()

        return context


# ============================================================
# NOTE LIST
# ============================================================

class ClinicalNoteListView(
    LoginRequiredMixin,
    ClinicalNoteNavigationMixin,
    PatientClinicalNoteMixin,
    ListView,
):
    """
    Display clinical documentation for one patient.
    """

    model = ClinicalNote
    context_object_name = "notes"
    template_name = "clinical_notes/note_list.html"
    paginate_by = 50

    def get_queryset(self):
        patient = self.get_patient()

        queryset = (
            ClinicalNote.objects
            .filter(patient=patient)
            .select_related(
                "patient",
                "encounter",
                "author",
                "signed_by",
            )
            .order_by("-created_at")
        )

        note_type = self.request.GET.get("note_type")
        status = self.request.GET.get("status")

        if note_type:
            queryset = queryset.filter(
                note_type=note_type,
            )

        if status:
            queryset = queryset.filter(
                status=status,
            )

        return queryset

    def get_template_names(self):
        if is_htmx(self.request):
            return [
                "clinical_notes/partials/note_list.html",
            ]

        return [
            "clinical_notes/note_list.html",
        ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["note_type_choices"] = ClinicalNote.NoteType.choices
        context["status_choices"] = ClinicalNote.Status.choices

        return context


# ============================================================
# NOTE DETAIL
# ============================================================

class ClinicalNoteDetailView(
    LoginRequiredMixin,
    ClinicalNoteNavigationMixin,
    PatientClinicalNoteMixin,
    DetailView,
):
    """
    Display one clinical note.
    """

    model = ClinicalNote
    context_object_name = "note"
    template_name = "clinical_notes/note_detail.html"

    queryset = (
        ClinicalNote.objects
        .select_related(
            "patient",
            "encounter",
            "author",
            "signed_by",
            "amended_by",
            "voided_by",
        )
    )

    def get_template_names(self):
        if is_htmx(self.request):
            return [
                "clinical_notes/partials/note_detail.html",
            ]

        return [
            "clinical_notes/note_detail.html",
        ]


# ============================================================
# NOTE CREATE
# ============================================================

class ClinicalNoteCreateView(
    LoginRequiredMixin,
    ClinicalNoteNavigationMixin,
    PatientClinicalNoteMixin,
    CreateView,
):
    """
    Create a new draft clinical note.
    """

    model = ClinicalNote
    form_class = ClinicalNoteForm
    template_name = "clinical_notes/note_form.html"

    def get_template_names(self):
        if is_htmx(self.request):
            return [
                "clinical_notes/partials/note_form.html",
            ]

        return [
            "clinical_notes/note_form.html",
        ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["patient"] = self.get_patient()
        kwargs["active_encounter"] = self.get_active_encounter()

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "New Clinical Note"
        context["page_description"] = (
            "Document patient assessment, findings, and care plan."
        )
        context["submit_label"] = "Save Draft"

        return context

    @transaction.atomic
    def form_valid(self, form):
        patient = self.get_patient()

        form.instance.patient = patient
        form.instance.author = self.request.user
        form.instance.created_by = self.request.user
        form.instance.updated_by = self.request.user
        form.instance.status = ClinicalNote.Status.DRAFT

        response = super().form_valid(form)

        if is_htmx(self.request):
            detail_url = reverse(
                "clinical_notes:detail",
                kwargs={
                    "pk": self.object.pk,
                },
            )

            response["HX-Redirect"] = detail_url

        return response

    def get_success_url(self):
        return reverse(
            "clinical_notes:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )


# ============================================================
# NOTE UPDATE
# ============================================================

class ClinicalNoteUpdateView(
    LoginRequiredMixin,
    ClinicalNoteNavigationMixin,
    PatientClinicalNoteMixin,
    UpdateView,
):
    """
    Update a draft clinical note.

    Signed, amended, or voided notes cannot be edited directly.
    """

    model = ClinicalNote
    form_class = ClinicalNoteForm
    template_name = "clinical_notes/note_form.html"

    queryset = (
        ClinicalNote.objects
        .select_related(
            "patient",
            "encounter",
            "author",
        )
    )

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not self.object.can_edit:
            raise PermissionDenied(
                "Signed or finalized clinical notes cannot be edited."
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_template_names(self):
        if is_htmx(self.request):
            return [
                "clinical_notes/partials/note_form.html",
            ]

        return [
            "clinical_notes/note_form.html",
        ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs["patient"] = self.object.patient
        kwargs["active_encounter"] = (
            self.object.encounter
            or self.get_active_encounter()
        )

        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["page_title"] = "Edit Clinical Note"
        context["page_description"] = (
            "Update this draft clinical note before signing."
        )
        context["submit_label"] = "Save Changes"

        return context

    @transaction.atomic
    def form_valid(self, form):
        form.instance.updated_by = self.request.user

        response = super().form_valid(form)

        if is_htmx(self.request):
            response["HX-Redirect"] = self.get_success_url()

        return response

    def get_success_url(self):
        return reverse(
            "clinical_notes:detail",
            kwargs={
                "pk": self.object.pk,
            },
        )


# ============================================================
# SIGN CLINICAL NOTE
# ============================================================

class ClinicalNoteSignView(
    LoginRequiredMixin,
    View,
):
    """
    Electronically sign a draft clinical note.
    """

    @transaction.atomic
    def post(self, request, pk):
        note = get_object_or_404(
            ClinicalNote,
            pk=pk,
        )

        if not note.can_edit:
            raise PermissionDenied(
                "This note is already finalized."
            )

        note.sign(request.user)

        detail_url = reverse(
            "clinical_notes:detail",
            kwargs={
                "pk": note.pk,
            },
        )

        if is_htmx(request):
            response = HttpResponse(status=204)
            response["HX-Redirect"] = detail_url
            return response

        return redirect(detail_url)


# ============================================================
# PATIENT NOTE SHORTCUT
# ============================================================

@login_required
def patient_notes_redirect(request, patient_pk):
    """
    Convenience endpoint for patient clinical note navigation.
    """

    return redirect(
        "clinical_notes:list",
        patient_pk=patient_pk,
    )
