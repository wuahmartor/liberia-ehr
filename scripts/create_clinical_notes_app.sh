

#!/usr/bin/env bash

# ============================================================
# LIBERIA EHR - CLINICAL NOTES APP CREATOR
#
# File:
# scripts/create_clinical_notes_app.sh
#
# Purpose:
# - Create the clinical_notes Django application.
# - Create models, forms, views, URLs, admin registration.
# - Create complete Tailwind/HTMX templates.
# - Preserve the existing Liberia EHR application structure.
#
# Usage:
#   chmod +x scripts/create_clinical_notes_app.sh
#   ./scripts/create_clinical_notes_app.sh
#
# Run from:
#   Project root containing manage.py
# ============================================================

set -e


# ============================================================
# PATHS
# ============================================================

APP_DIR="apps/clinical_notes"
TEMPLATE_DIR="$APP_DIR/templates/clinical_notes"
PARTIAL_DIR="$TEMPLATE_DIR/partials"
MIGRATION_DIR="$APP_DIR/migrations"


echo ""
echo "============================================================"
echo " Creating Liberia EHR Clinical Notes module"
echo "============================================================"
echo ""


# ============================================================
# CREATE DIRECTORIES
# ============================================================

mkdir -p "$APP_DIR"
mkdir -p "$MIGRATION_DIR"
mkdir -p "$TEMPLATE_DIR"
mkdir -p "$PARTIAL_DIR"


# ============================================================
# PYTHON PACKAGE FILES
# ============================================================

touch "$APP_DIR/__init__.py"
touch "$MIGRATION_DIR/__init__.py"


# ============================================================
# APPS.PY
# ============================================================

cat > "$APP_DIR/apps.py" <<'PYTHON'
"""
============================================================
CLINICAL NOTES APP CONFIGURATION

File:
apps/clinical_notes/apps.py

Purpose:
- Configure the Clinical Notes Django application.
============================================================
"""

from django.apps import AppConfig


class ClinicalNotesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.clinical_notes"
    verbose_name = "Clinical Notes"
PYTHON


# ============================================================
# MODELS.PY
# ============================================================

cat > "$APP_DIR/models.py" <<'PYTHON'
"""
============================================================
CLINICAL NOTES MODELS

File:
apps/clinical_notes/models.py

Purpose:
- Store patient clinical documentation.
- Associate clinical notes with patients and encounters.
- Support multidisciplinary documentation.
- Support draft, signed, amended, and voided documentation.
- Preserve author, signer, and timestamp information.
- Support SOAP documentation without requiring all notes to
  follow SOAP structure.

Design principles:
- Patient is required.
- Encounter is optional because some documentation may occur
  outside a traditional encounter.
- Signed clinical notes should be treated as finalized records.
- Changes after signing should generally be handled by addendum
  or amendment rather than silently replacing documentation.
============================================================
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ClinicalNote(models.Model):
    """
    Primary clinical documentation record.

    A ClinicalNote belongs to one patient and may optionally
    belong to an encounter.
    """

    # ========================================================
    # NOTE TYPE
    # ========================================================

    class NoteType(models.TextChoices):
        PROGRESS = "progress", "Progress Note"
        SOAP = "soap", "SOAP Note"
        PHYSICIAN = "physician", "Physician Note"
        NURSE_PRACTITIONER = "np", "Nurse Practitioner Note"
        NURSING = "nursing", "Nursing Note"
        ADMISSION = "admission", "Admission Note"
        CONSULTATION = "consultation", "Consultation Note"
        PROCEDURE = "procedure", "Procedure Note"
        DISCHARGE = "discharge", "Discharge Note"
        CASE_MANAGEMENT = "case_management", "Case Management Note"
        CARE_COORDINATION = "care_coordination", "Care Coordination Note"
        TELEPHONE = "telephone", "Telephone Note"
        FOLLOW_UP = "follow_up", "Follow-up Note"
        GENERAL = "general", "General Clinical Note"

    # ========================================================
    # NOTE STATUS
    # ========================================================

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SIGNED = "signed", "Signed"
        AMENDED = "amended", "Amended"
        VOIDED = "voided", "Voided"

    # ========================================================
    # PRIMARY IDENTIFIER
    # ========================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # ========================================================
    # PATIENT / ENCOUNTER RELATIONSHIPS
    # ========================================================

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="clinical_notes",
        db_index=True,
    )

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.PROTECT,
        related_name="clinical_notes",
        null=True,
        blank=True,
        db_index=True,
    )

    # ========================================================
    # CLASSIFICATION
    # ========================================================

    note_type = models.CharField(
        max_length=30,
        choices=NoteType.choices,
        default=NoteType.PROGRESS,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    title = models.CharField(
        max_length=200,
        blank=True,
        help_text="Optional descriptive note title.",
    )

    # ========================================================
    # SOAP / STRUCTURED CONTENT
    # ========================================================

    subjective = models.TextField(
        blank=True,
        help_text=(
            "Patient-reported symptoms, history, concerns, "
            "and other subjective information."
        ),
    )

    objective = models.TextField(
        blank=True,
        help_text=(
            "Physical examination findings, observations, "
            "measurements, and objective clinical information."
        ),
    )

    assessment = models.TextField(
        blank=True,
        help_text=(
            "Clinical impression, interpretation, differential "
            "considerations, and assessment."
        ),
    )

    plan = models.TextField(
        blank=True,
        help_text=(
            "Treatment plan, investigations, referrals, education, "
            "follow-up, and other planned interventions."
        ),
    )

    # ========================================================
    # GENERAL / ADDITIONAL CONTENT
    # ========================================================

    content = models.TextField(
        blank=True,
        help_text=(
            "Additional narrative documentation that does not fit "
            "within the structured SOAP sections."
        ),
    )

    # ========================================================
    # AUTHORSHIP
    # ========================================================

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_authored",
    )

    # ========================================================
    # ELECTRONIC SIGNATURE
    # ========================================================

    signed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_signed",
        null=True,
        blank=True,
    )

    signed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ========================================================
    # AMENDMENT / ADDENDUM TRACKING
    # ========================================================

    amended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    amendment_reason = models.TextField(
        blank=True,
    )

    amended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_amended",
        null=True,
        blank=True,
    )

    # ========================================================
    # VOID TRACKING
    # ========================================================

    voided_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_voided",
        null=True,
        blank=True,
    )

    void_reason = models.TextField(
        blank=True,
    )

    # ========================================================
    # AUDIT FIELDS
    # ========================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_created",
        null=True,
        blank=True,
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clinical_notes_updated",
        null=True,
        blank=True,
    )

    # ========================================================
    # MODEL META
    # ========================================================

    class Meta:
        ordering = [
            "-created_at",
        ]

        indexes = [
            models.Index(
                fields=["patient", "-created_at"],
                name="clin_note_patient_created_idx",
            ),
            models.Index(
                fields=["encounter", "-created_at"],
                name="clin_note_enc_created_idx",
            ),
            models.Index(
                fields=["patient", "status"],
                name="clin_note_patient_status_idx",
            ),
            models.Index(
                fields=["patient", "note_type"],
                name="clin_note_patient_type_idx",
            ),
        ]

        verbose_name = "Clinical Note"
        verbose_name_plural = "Clinical Notes"

    # ========================================================
    # DISPLAY
    # ========================================================

    def __str__(self):
        patient_name = str(self.patient)

        return (
            f"{self.get_note_type_display()} - "
            f"{patient_name} - "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):
        """
        Validate clinical note relationships and documentation.
        """

        super().clean()

        # ----------------------------------------------------
        # ENCOUNTER MUST BELONG TO PATIENT
        # ----------------------------------------------------

        if self.encounter_id and self.patient_id:
            encounter_patient_id = getattr(
                self.encounter,
                "patient_id",
                None,
            )

            if (
                encounter_patient_id is not None
                and encounter_patient_id != self.patient_id
            ):
                raise ValidationError(
                    {
                        "encounter": (
                            "The selected encounter does not belong "
                            "to this patient."
                        )
                    }
                )

        # ----------------------------------------------------
        # REQUIRE CLINICAL CONTENT
        # ----------------------------------------------------

        has_content = any(
            [
                bool((self.subjective or "").strip()),
                bool((self.objective or "").strip()),
                bool((self.assessment or "").strip()),
                bool((self.plan or "").strip()),
                bool((self.content or "").strip()),
            ]
        )

        if not has_content:
            raise ValidationError(
                "Clinical notes must contain documentation in at least "
                "one clinical section."
            )

        # ----------------------------------------------------
        # SIGNED STATUS REQUIRES SIGNATURE
        # ----------------------------------------------------

        if self.status == self.Status.SIGNED:
            if not self.signed_by:
                raise ValidationError(
                    {
                        "signed_by": (
                            "A signed clinical note must identify "
                            "the signing user."
                        )
                    }
                )

            if not self.signed_at:
                raise ValidationError(
                    {
                        "signed_at": (
                            "A signed clinical note must include "
                            "the signing date and time."
                        )
                    }
                )

        # ----------------------------------------------------
        # AMENDMENT REQUIRES REASON
        # ----------------------------------------------------

        if self.status == self.Status.AMENDED:
            if not (self.amendment_reason or "").strip():
                raise ValidationError(
                    {
                        "amendment_reason": (
                            "An amendment reason is required."
                        )
                    }
                )

    # ========================================================
    # HELPERS
    # ========================================================

    @property
    def is_draft(self):
        return self.status == self.Status.DRAFT

    @property
    def is_signed(self):
        return self.status == self.Status.SIGNED

    @property
    def is_amended(self):
        return self.status == self.Status.AMENDED

    @property
    def is_voided(self):
        return self.status == self.Status.VOIDED

    @property
    def can_edit(self):
        """
        Normal editing is permitted only while the note is a draft.
        """
        return self.status == self.Status.DRAFT

    def sign(self, user):
        """
        Electronically sign this clinical note.
        """

        if self.status != self.Status.DRAFT:
            raise ValidationError(
                "Only draft clinical notes can be signed."
            )

        self.status = self.Status.SIGNED
        self.signed_by = user
        self.signed_at = timezone.now()
        self.updated_by = user

        self.full_clean()

        self.save(
            update_fields=[
                "status",
                "signed_by",
                "signed_at",
                "updated_by",
                "updated_at",
            ]
        )

    def void(self, user, reason):
        """
        Void a clinical note while preserving the original record.
        """

        if not reason or not reason.strip():
            raise ValidationError(
                "A reason is required to void a clinical note."
            )

        self.status = self.Status.VOIDED
        self.voided_by = user
        self.voided_at = timezone.now()
        self.void_reason = reason.strip()
        self.updated_by = user

        self.save(
            update_fields=[
                "status",
                "voided_by",
                "voided_at",
                "void_reason",
                "updated_by",
                "updated_at",
            ]
        )
PYTHON


# ============================================================
# FORMS.PY
# ============================================================

cat > "$APP_DIR/forms.py" <<'PYTHON'
"""
============================================================
CLINICAL NOTES FORMS

File:
apps/clinical_notes/forms.py

Purpose:
- Provide compact Tailwind-styled clinical note forms.
- Restrict encounter choices to the selected patient.
- Keep system-generated authorship/signature fields outside
  normal clinician input.
============================================================
"""

from django import forms

from apps.encounters.models import Encounter

from .models import ClinicalNote


# ============================================================
# SHARED TAILWIND CLASSES
# ============================================================

INPUT_CLASS = """
block h-8 w-full rounded-md border border-slate-300 bg-white
px-2 text-xs text-slate-800 shadow-sm outline-none
placeholder:text-slate-400
focus:border-ehr-500 focus:ring-1 focus:ring-ehr-500
""".strip()


TEXTAREA_CLASS = """
block min-h-[110px] w-full resize-y rounded-md
border border-slate-300 bg-white
px-3 py-2 text-sm leading-5 text-slate-800 shadow-sm outline-none
placeholder:text-slate-400
focus:border-ehr-500 focus:ring-1 focus:ring-ehr-500
""".strip()


class ClinicalNoteForm(forms.ModelForm):
    """
    Clinical documentation form.

    System-managed fields such as author, created_by, signed_by,
    and timestamps are intentionally excluded.
    """

    class Meta:
        model = ClinicalNote

        fields = [
            "note_type",
            "encounter",
            "title",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "content",
        ]

        widgets = {
            "note_type": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "encounter": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),
            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Optional note title",
                    "autocomplete": "off",
                }
            ),
            "subjective": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Patient-reported symptoms, concerns, "
                        "history, and relevant subjective information..."
                    ),
                }
            ),
            "objective": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Examination findings, observations, "
                        "measurements, and objective information..."
                    ),
                }
            ),
            "assessment": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Clinical impression, interpretation, "
                        "assessment, and relevant problems..."
                    ),
                }
            ),
            "plan": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Treatment, investigations, referrals, "
                        "education, follow-up, and care plan..."
                    ),
                }
            ),
            "content": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 5,
                    "placeholder": (
                        "Additional clinical documentation..."
                    ),
                }
            ),
        }

    def __init__(
        self,
        *args,
        patient=None,
        active_encounter=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.patient = patient
        self.active_encounter = active_encounter

        # ----------------------------------------------------
        # ENCOUNTER CHOICES
        # ----------------------------------------------------

        if patient is not None:
            self.fields["encounter"].queryset = (
                Encounter.objects
                .filter(patient=patient)
                .order_by("-start_datetime")
            )
        else:
            self.fields["encounter"].queryset = Encounter.objects.none()

        # ----------------------------------------------------
        # DEFAULT ACTIVE ENCOUNTER
        # ----------------------------------------------------

        if (
            not self.is_bound
            and not self.instance.pk
            and active_encounter is not None
        ):
            self.initial["encounter"] = active_encounter

        # ----------------------------------------------------
        # LABELS
        # ----------------------------------------------------

        self.fields["note_type"].label = "Note Type"
        self.fields["encounter"].label = "Encounter"
        self.fields["title"].label = "Title"
        self.fields["subjective"].label = "Subjective"
        self.fields["objective"].label = "Objective"
        self.fields["assessment"].label = "Assessment"
        self.fields["plan"].label = "Plan"
        self.fields["content"].label = "Additional Documentation"

        self.fields["encounter"].required = False
        self.fields["title"].required = False

    def clean_encounter(self):
        encounter = self.cleaned_data.get("encounter")

        if encounter and self.patient:
            if encounter.patient_id != self.patient.pk:
                raise forms.ValidationError(
                    "The selected encounter does not belong to this patient."
                )

        return encounter

    def clean(self):
        cleaned_data = super().clean()

        clinical_fields = [
            "subjective",
            "objective",
            "assessment",
            "plan",
            "content",
        ]

        has_content = any(
            (
                cleaned_data.get(field_name)
                and cleaned_data.get(field_name).strip()
            )
            for field_name in clinical_fields
        )

        if not has_content:
            raise forms.ValidationError(
                "Enter documentation in at least one clinical section."
            )

        return cleaned_data
PYTHON


# ============================================================
# VIEWS.PY
# ============================================================

cat > "$APP_DIR/views.py" <<'PYTHON'
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
PYTHON


# ============================================================
# URLS.PY
# ============================================================

cat > "$APP_DIR/urls.py" <<'PYTHON'
"""
============================================================
CLINICAL NOTES URLS

File:
apps/clinical_notes/urls.py
============================================================
"""

from django.urls import path

from .views import (
    ClinicalNoteCreateView,
    ClinicalNoteDetailView,
    ClinicalNoteListView,
    ClinicalNoteSignView,
    ClinicalNoteUpdateView,
)


app_name = "clinical_notes"


urlpatterns = [

    # ========================================================
    # PATIENT NOTE HISTORY
    # ========================================================

    path(
        "patient/<int:patient_pk>/",
        ClinicalNoteListView.as_view(),
        name="list",
    ),

    # ========================================================
    # CREATE NOTE
    # ========================================================

    path(
        "patient/<int:patient_pk>/new/",
        ClinicalNoteCreateView.as_view(),
        name="create",
    ),

    # ========================================================
    # NOTE DETAIL
    # ========================================================

    path(
        "<uuid:pk>/",
        ClinicalNoteDetailView.as_view(),
        name="detail",
    ),

    # ========================================================
    # UPDATE DRAFT NOTE
    # ========================================================

    path(
        "<uuid:pk>/edit/",
        ClinicalNoteUpdateView.as_view(),
        name="update",
    ),

    # ========================================================
    # SIGN NOTE
    # ========================================================

    path(
        "<uuid:pk>/sign/",
        ClinicalNoteSignView.as_view(),
        name="sign",
    ),
]
PYTHON


# ============================================================
# ADMIN.PY
# ============================================================

cat > "$APP_DIR/admin.py" <<'PYTHON'
"""
============================================================
CLINICAL NOTES ADMIN

File:
apps/clinical_notes/admin.py
============================================================
"""

from django.contrib import admin

from .models import ClinicalNote


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):

    list_display = (
        "patient",
        "note_type",
        "status",
        "author",
        "encounter",
        "created_at",
        "signed_at",
    )

    list_filter = (
        "note_type",
        "status",
        "created_at",
        "signed_at",
    )

    search_fields = (
        "patient__first_name",
        "patient__middle_name",
        "patient__last_name",
        "title",
        "subjective",
        "objective",
        "assessment",
        "plan",
        "content",
    )

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "signed_at",
        "amended_at",
        "voided_at",
    )

    autocomplete_fields = (
        "patient",
        "encounter",
        "author",
        "signed_by",
        "created_by",
        "updated_by",
        "amended_by",
        "voided_by",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (

        (
            "Clinical Note",
            {
                "fields": (
                    "id",
                    "patient",
                    "encounter",
                    "note_type",
                    "status",
                    "title",
                )
            },
        ),

        (
            "Clinical Documentation",
            {
                "fields": (
                    "subjective",
                    "objective",
                    "assessment",
                    "plan",
                    "content",
                )
            },
        ),

        (
            "Authorship",
            {
                "fields": (
                    "author",
                    "signed_by",
                    "signed_at",
                )
            },
        ),

        (
            "Amendment",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "amended_by",
                    "amended_at",
                    "amendment_reason",
                ),
            },
        ),

        (
            "Void Information",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "voided_by",
                    "voided_at",
                    "void_reason",
                ),
            },
        ),

        (
            "Audit",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_by",
                    "updated_at",
                ),
            },
        ),
    )
PYTHON


# ============================================================
# TESTS.PY
# ============================================================

cat > "$APP_DIR/tests.py" <<'PYTHON'
"""
Clinical Notes tests.

Add model, form, permission, signing, and HTMX workflow tests here.
"""
PYTHON


# ============================================================
# FULL PAGE: NOTE LIST
# ============================================================

cat > "$TEMPLATE_DIR/note_list.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTES LIST PAGE

File:
apps/clinical_notes/templates/clinical_notes/note_list.html
============================================================
{% endcomment %}

{% extends "base.html" %}

{% block title %}
Clinical Notes | Liberia EHR
{% endblock %}

{% block content %}

<div
    id="clinical-notes-workspace"
    class="h-full min-h-0 w-full"
>
    {% include "clinical_notes/partials/note_list.html" %}
</div>

{% endblock %}
HTML


# ============================================================
# FULL PAGE: NOTE FORM
# ============================================================

cat > "$TEMPLATE_DIR/note_form.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE FORM PAGE

File:
apps/clinical_notes/templates/clinical_notes/note_form.html
============================================================
{% endcomment %}

{% extends "base.html" %}

{% block title %}
{{ page_title|default:"Clinical Note" }} | Liberia EHR
{% endblock %}

{% block content %}

<div
    id="clinical-notes-workspace"
    class="h-full min-h-0 w-full"
>
    {% include "clinical_notes/partials/note_form.html" %}
</div>

{% endblock %}
HTML


# ============================================================
# FULL PAGE: NOTE DETAIL
# ============================================================

cat > "$TEMPLATE_DIR/note_detail.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE DETAIL PAGE

File:
apps/clinical_notes/templates/clinical_notes/note_detail.html
============================================================
{% endcomment %}

{% extends "base.html" %}

{% block title %}
Clinical Note | Liberia EHR
{% endblock %}

{% block content %}

<div
    id="clinical-notes-workspace"
    class="h-full min-h-0 w-full"
>
    {% include "clinical_notes/partials/note_detail.html" %}
</div>

{% endblock %}
HTML


# ============================================================
# PARTIAL: NOTE LIST
# ============================================================

cat > "$PARTIAL_DIR/note_list.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTES LIST PARTIAL

File:
apps/clinical_notes/templates/clinical_notes/partials/note_list.html

Purpose:
- Display longitudinal clinical documentation.
- Provide note filters.
- Provide compact clinical note rows.
============================================================
{% endcomment %}

<section class="flex h-full min-h-0 flex-col bg-white">

    <!-- =====================================================
         HEADER
    ====================================================== -->

    <header
        class="
            flex shrink-0 flex-col gap-2
            border-b border-slate-200
            px-4 py-3
            sm:flex-row sm:items-center sm:justify-between
        "
    >

        <div class="min-w-0">

            <div class="flex items-center gap-2">

                <h1 class="text-base font-semibold text-slate-900">
                    Clinical Notes
                </h1>

                {% if page_obj %}
                    <span
                        class="
                            rounded-full bg-slate-100
                            px-2 py-0.5
                            text-[10px] font-semibold text-slate-600
                        "
                    >
                        {{ page_obj.paginator.count }}
                    </span>
                {% endif %}

            </div>

            <p class="mt-0.5 text-xs text-slate-500">
                Clinical documentation and encounter note history.
            </p>

        </div>


        {% if selected_patient %}

            <a
                href="{% url 'clinical_notes:create' selected_patient.pk %}"
                hx-get="{% url 'clinical_notes:create' selected_patient.pk %}"
                hx-target="#clinical-notes-workspace"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="
                    inline-flex h-8 items-center justify-center gap-1.5
                    rounded-md bg-ehr-700
                    px-3 text-xs font-semibold text-white
                    shadow-sm transition
                    hover:bg-ehr-800
                "
            >

                <svg
                    class="h-3.5 w-3.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path
                        stroke-linecap="round"
                        stroke-linejoin="round"
                        stroke-width="2"
                        d="M12 4v16m8-8H4"
                    />
                </svg>

                New Note

            </a>

        {% endif %}

    </header>


    <!-- =====================================================
         ENCOUNTER CONTEXT
    ====================================================== -->

    {% if active_encounter %}

        <div
            class="
                flex shrink-0 flex-wrap
                items-center gap-x-4 gap-y-1
                border-b border-slate-200
                bg-slate-50 px-4 py-2
                text-[11px]
            "
        >

            <div>
                <span class="text-slate-500">
                    Encounter
                </span>

                <span class="ml-1 font-medium text-slate-800">
                    {{ active_encounter }}
                </span>
            </div>


            {% if active_encounter.status %}

                <div>
                    <span class="text-slate-500">
                        Status
                    </span>

                    <span class="ml-1 font-medium text-slate-800">
                        {{ active_encounter.get_status_display }}
                    </span>
                </div>

            {% endif %}


            {% if active_encounter.start_datetime %}

                <div>
                    <span class="text-slate-500">
                        Started
                    </span>

                    <span class="ml-1 font-medium text-slate-800">
                        {{ active_encounter.start_datetime|date:"M j, Y H:i" }}
                    </span>
                </div>

            {% endif %}

        </div>

    {% endif %}


    <!-- =====================================================
         FILTER BAR
    ====================================================== -->

    <div
        class="
            shrink-0 border-b border-slate-200
            bg-white px-4 py-2
        "
    >

        <form
            method="get"
            action="{{ request.path }}"
            hx-get="{{ request.path }}"
            hx-target="#clinical-notes-workspace"
            hx-swap="innerHTML"
            hx-push-url="true"
            hx-trigger="change"
            class="flex flex-wrap items-center gap-2"
        >

            <select
                name="note_type"
                class="
                    h-8 min-w-[150px]
                    rounded-md border border-slate-300
                    bg-white px-2
                    text-xs text-slate-700
                    outline-none
                    focus:border-ehr-500
                    focus:ring-1 focus:ring-ehr-500
                "
            >

                <option value="">
                    All note types
                </option>

                {% for value, label in note_type_choices %}

                    <option
                        value="{{ value }}"
                        {% if request.GET.note_type == value %}
                            selected
                        {% endif %}
                    >
                        {{ label }}
                    </option>

                {% endfor %}

            </select>


            <select
                name="status"
                class="
                    h-8 min-w-[120px]
                    rounded-md border border-slate-300
                    bg-white px-2
                    text-xs text-slate-700
                    outline-none
                    focus:border-ehr-500
                    focus:ring-1 focus:ring-ehr-500
                "
            >

                <option value="">
                    All statuses
                </option>

                {% for value, label in status_choices %}

                    <option
                        value="{{ value }}"
                        {% if request.GET.status == value %}
                            selected
                        {% endif %}
                    >
                        {{ label }}
                    </option>

                {% endfor %}

            </select>

        </form>

    </div>


    <!-- =====================================================
         NOTE HISTORY
    ====================================================== -->

    <div class="min-h-0 flex-1 overflow-y-auto">

        {% if notes %}

            <div class="divide-y divide-slate-100">

                {% for note in notes %}

                    {% include "clinical_notes/partials/note_row.html" %}

                {% endfor %}

            </div>

        {% else %}

            <div
                class="
                    flex min-h-[300px]
                    items-center justify-center
                    p-6
                "
            >

                <div class="max-w-sm text-center">

                    <div
                        class="
                            mx-auto flex h-10 w-10
                            items-center justify-center
                            rounded-full bg-slate-100
                            text-slate-400
                        "
                    >

                        <svg
                            class="h-5 w-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path
                                stroke-linecap="round"
                                stroke-linejoin="round"
                                stroke-width="1.5"
                                d="M9 12h6m-6 4h6M7 4h7l3 3v13H7V4z"
                            />
                        </svg>

                    </div>

                    <h2 class="mt-3 text-sm font-semibold text-slate-800">
                        No clinical notes
                    </h2>

                    <p class="mt-1 text-xs leading-5 text-slate-500">
                        No clinical documentation has been entered
                        for this patient.
                    </p>

                </div>

            </div>

        {% endif %}

    </div>


    <!-- =====================================================
         PAGINATION
    ====================================================== -->

    {% if page_obj.has_other_pages %}

        <footer
            class="
                flex shrink-0 items-center justify-between
                border-t border-slate-200
                px-4 py-2
                text-xs text-slate-500
            "
        >

            <div>
                Page {{ page_obj.number }}
                of {{ page_obj.paginator.num_pages }}
            </div>


            <div class="flex items-center gap-1">

                {% if page_obj.has_previous %}

                    <a
                        href="?page={{ page_obj.previous_page_number }}"
                        hx-get="?page={{ page_obj.previous_page_number }}"
                        hx-target="#clinical-notes-workspace"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="
                            rounded border border-slate-300
                            px-2 py-1
                            hover:bg-slate-50
                        "
                    >
                        Previous
                    </a>

                {% endif %}


                {% if page_obj.has_next %}

                    <a
                        href="?page={{ page_obj.next_page_number }}"
                        hx-get="?page={{ page_obj.next_page_number }}"
                        hx-target="#clinical-notes-workspace"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="
                            rounded border border-slate-300
                            px-2 py-1
                            hover:bg-slate-50
                        "
                    >
                        Next
                    </a>

                {% endif %}

            </div>

        </footer>

    {% endif %}

</section>
HTML


# ============================================================
# PARTIAL: NOTE ROW
# ============================================================

cat > "$PARTIAL_DIR/note_row.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE ROW

File:
apps/clinical_notes/templates/clinical_notes/partials/note_row.html
============================================================
{% endcomment %}

<article
    class="
        group px-4 py-3
        transition hover:bg-slate-50
    "
>

    <div
        class="
            flex flex-col gap-2
            sm:flex-row
            sm:items-start
            sm:justify-between
        "
    >

        <div class="min-w-0 flex-1">

            <!-- =================================================
                 TITLE / STATUS
            ================================================== -->

            <div class="flex flex-wrap items-center gap-2">

                <a
                    href="{% url 'clinical_notes:detail' note.pk %}"
                    hx-get="{% url 'clinical_notes:detail' note.pk %}"
                    hx-target="#clinical-notes-workspace"
                    hx-swap="innerHTML"
                    hx-push-url="true"
                    class="
                        text-sm font-semibold text-slate-900
                        hover:text-ehr-700
                    "
                >
                    {% if note.title %}
                        {{ note.title }}
                    {% else %}
                        {{ note.get_note_type_display }}
                    {% endif %}
                </a>


                <span
                    class="
                        rounded px-1.5 py-0.5
                        text-[9px] font-semibold
                        uppercase tracking-wide

                        {% if note.status == 'draft' %}
                            bg-amber-50 text-amber-700
                        {% elif note.status == 'signed' %}
                            bg-emerald-50 text-emerald-700
                        {% elif note.status == 'amended' %}
                            bg-blue-50 text-blue-700
                        {% else %}
                            bg-slate-100 text-slate-600
                        {% endif %}
                    "
                >
                    {{ note.get_status_display }}
                </span>

            </div>


            <!-- =================================================
                 NOTE TYPE
            ================================================== -->

            {% if note.title %}

                <p class="mt-0.5 text-[11px] font-medium text-slate-500">
                    {{ note.get_note_type_display }}
                </p>

            {% endif %}


            <!-- =================================================
                 METADATA
            ================================================== -->

            <div
                class="
                    mt-1 flex flex-wrap
                    items-center gap-x-3 gap-y-1
                    text-[11px] text-slate-500
                "
            >

                <span>
                    {{ note.author.get_full_name|default:note.author.username }}
                </span>

                <span>
                    {{ note.created_at|date:"M j, Y H:i" }}
                </span>

                {% if note.encounter %}
                    <span>
                        {{ note.encounter }}
                    </span>
                {% endif %}

            </div>


            <!-- =================================================
                 SUMMARY
            ================================================== -->

            {% if note.assessment %}

                <p
                    class="
                        mt-2 max-w-4xl
                        text-xs leading-5 text-slate-600
                    "
                >
                    {{ note.assessment|truncatechars:220 }}
                </p>

            {% elif note.subjective %}

                <p
                    class="
                        mt-2 max-w-4xl
                        text-xs leading-5 text-slate-600
                    "
                >
                    {{ note.subjective|truncatechars:220 }}
                </p>

            {% elif note.content %}

                <p
                    class="
                        mt-2 max-w-4xl
                        text-xs leading-5 text-slate-600
                    "
                >
                    {{ note.content|truncatechars:220 }}
                </p>

            {% endif %}

        </div>


        <!-- =====================================================
             ACTIONS
        ====================================================== -->

        <div class="flex shrink-0 items-center gap-1">

            <a
                href="{% url 'clinical_notes:detail' note.pk %}"
                hx-get="{% url 'clinical_notes:detail' note.pk %}"
                hx-target="#clinical-notes-workspace"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="
                    inline-flex h-7 items-center
                    rounded-md border border-slate-300
                    bg-white px-2
                    text-[11px] font-medium text-slate-600
                    hover:bg-slate-50
                    hover:text-slate-900
                "
            >
                View
            </a>


            {% if note.can_edit %}

                <a
                    href="{% url 'clinical_notes:update' note.pk %}"
                    hx-get="{% url 'clinical_notes:update' note.pk %}"
                    hx-target="#clinical-notes-workspace"
                    hx-swap="innerHTML"
                    hx-push-url="true"
                    class="
                        inline-flex h-7 items-center
                        rounded-md border border-slate-300
                        bg-white px-2
                        text-[11px] font-medium text-slate-600
                        hover:bg-slate-50
                        hover:text-ehr-700
                    "
                >
                    Edit
                </a>

            {% endif %}

        </div>

    </div>

</article>
HTML


# ============================================================
# PARTIAL: NOTE FORM
# ============================================================

cat > "$PARTIAL_DIR/note_form.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE FORM PARTIAL

File:
apps/clinical_notes/templates/clinical_notes/partials/note_form.html

Purpose:
- Create or update clinical documentation.
- Keep patient and encounter context visible.
- Support HTMX submission.
============================================================
{% endcomment %}

<section class="flex h-full min-h-0 flex-col bg-white">

    <!-- =====================================================
         HEADER
    ====================================================== -->

    <header
        class="
            flex shrink-0 flex-col gap-2
            border-b border-slate-200
            px-4 py-3
            sm:flex-row
            sm:items-center
            sm:justify-between
        "
    >

        <div>

            <h1 class="text-base font-semibold text-slate-900">
                {{ page_title|default:"Clinical Note" }}
            </h1>

            <p class="mt-0.5 text-xs text-slate-500">
                {{ page_description }}
            </p>

        </div>


        {% if selected_patient %}

            <a
                href="{% url 'clinical_notes:list' selected_patient.pk %}"
                hx-get="{% url 'clinical_notes:list' selected_patient.pk %}"
                hx-target="#clinical-notes-workspace"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="
                    inline-flex h-8 items-center
                    rounded-md border border-slate-300
                    bg-white px-3
                    text-xs font-medium text-slate-600
                    hover:bg-slate-50
                "
            >
                Back to Notes
            </a>

        {% endif %}

    </header>


    <!-- =====================================================
         PATIENT / ENCOUNTER CONTEXT
    ====================================================== -->

    <div
        class="
            shrink-0
            border-b border-slate-200
            bg-slate-50 px-4 py-2
        "
    >

        <div
            class="
                flex flex-wrap items-center
                gap-x-5 gap-y-1
                text-[11px]
            "
        >

            {% if selected_patient %}

                <div>

                    <span class="text-slate-500">
                        Patient
                    </span>

                    <span class="ml-1 font-semibold text-slate-800">
                        {{ selected_patient.first_name }}
                        {{ selected_patient.middle_name }}
                        {{ selected_patient.last_name }}
                    </span>

                </div>

            {% endif %}


            {% if active_encounter %}

                <div>

                    <span class="text-slate-500">
                        Encounter
                    </span>

                    <span class="ml-1 font-medium text-slate-800">
                        {{ active_encounter }}
                    </span>

                </div>

            {% endif %}

        </div>

    </div>


    <!-- =====================================================
         FORM
    ====================================================== -->

    <form
        method="post"
        action="{{ request.get_full_path }}"
        hx-post="{{ request.get_full_path }}"
        hx-target="#clinical-notes-workspace"
        hx-swap="innerHTML"
        hx-indicator="#clinical-note-loading"
        hx-disabled-elt="#clinical-note-submit"
        class="flex min-h-0 flex-1 flex-col"
    >

        {% csrf_token %}


        <!-- =================================================
             ERRORS
        ================================================== -->

        {% if form.non_field_errors %}

            <div
                class="
                    mx-4 mt-3
                    rounded-md border border-red-200
                    bg-red-50 px-3 py-2
                    text-xs text-red-700
                "
            >

                {% for error in form.non_field_errors %}
                    <p>{{ error }}</p>
                {% endfor %}

            </div>

        {% endif %}


        <!-- =================================================
             FIELDS
        ================================================== -->

        <div
            class="
                min-h-0 flex-1
                overflow-y-auto
                px-4 py-4
            "
        >

            {% include "clinical_notes/partials/note_form_fields.html" %}

        </div>


        <!-- =================================================
             ACTIONS
        ================================================== -->

        <footer
            class="
                flex shrink-0
                items-center justify-between
                border-t border-slate-200
                bg-white px-4 py-2.5
            "
        >

            <div
                id="clinical-note-loading"
                class="
                    htmx-indicator
                    flex items-center gap-2
                    text-xs text-slate-500
                "
            >

                <svg
                    class="h-4 w-4 animate-spin"
                    viewBox="0 0 24 24"
                    fill="none"
                >
                    <circle
                        class="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        stroke-width="4"
                    />

                    <path
                        class="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
                    />
                </svg>

                Saving...

            </div>


            <div class="ml-auto flex items-center gap-2">

                {% if selected_patient %}

                    <a
                        href="{% url 'clinical_notes:list' selected_patient.pk %}"
                        hx-get="{% url 'clinical_notes:list' selected_patient.pk %}"
                        hx-target="#clinical-notes-workspace"
                        hx-swap="innerHTML"
                        hx-push-url="true"
                        class="
                            inline-flex h-8 items-center
                            justify-center rounded-md
                            border border-slate-300
                            bg-white px-3
                            text-xs font-medium text-slate-600
                            hover:bg-slate-50
                        "
                    >
                        Cancel
                    </a>

                {% endif %}


                <button
                    id="clinical-note-submit"
                    type="submit"
                    class="
                        inline-flex h-8 items-center
                        justify-center rounded-md
                        bg-ehr-700 px-4
                        text-xs font-semibold text-white
                        shadow-sm
                        hover:bg-ehr-800
                        disabled:cursor-not-allowed
                        disabled:opacity-60
                    "
                >
                    {{ submit_label|default:"Save Note" }}
                </button>

            </div>

        </footer>

    </form>

</section>
HTML


# ============================================================
# PARTIAL: NOTE FORM FIELDS
# ============================================================

cat > "$PARTIAL_DIR/note_form_fields.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE FORM FIELDS

File:
apps/clinical_notes/templates/clinical_notes/partials/note_form_fields.html

Purpose:
- Render structured note documentation.
- Keep general fields compact.
- Keep narrative clinical sections readable.
============================================================
{% endcomment %}

<div class="mx-auto max-w-6xl space-y-4">


    <!-- =====================================================
         NOTE INFORMATION
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200
            bg-white
        "
    >

        <div
            class="
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <h2
                class="
                    text-[11px] font-semibold
                    uppercase tracking-wide
                    text-slate-700
                "
            >
                Note Information
            </h2>

        </div>


        <div
            class="
                grid grid-cols-1 gap-3 p-3
                md:grid-cols-3
            "
        >

            <!-- NOTE TYPE -->

            <div>

                <label
                    for="{{ form.note_type.id_for_label }}"
                    class="
                        mb-1 block
                        text-[11px] font-medium text-slate-700
                    "
                >
                    {{ form.note_type.label }}
                </label>

                {{ form.note_type }}

                {% for error in form.note_type.errors %}

                    <p class="mt-1 text-[10px] text-red-600">
                        {{ error }}
                    </p>

                {% endfor %}

            </div>


            <!-- ENCOUNTER -->

            <div>

                <label
                    for="{{ form.encounter.id_for_label }}"
                    class="
                        mb-1 block
                        text-[11px] font-medium text-slate-700
                    "
                >
                    {{ form.encounter.label }}
                </label>

                {{ form.encounter }}

                {% for error in form.encounter.errors %}

                    <p class="mt-1 text-[10px] text-red-600">
                        {{ error }}
                    </p>

                {% endfor %}

            </div>


            <!-- TITLE -->

            <div>

                <label
                    for="{{ form.title.id_for_label }}"
                    class="
                        mb-1 block
                        text-[11px] font-medium text-slate-700
                    "
                >
                    {{ form.title.label }}
                </label>

                {{ form.title }}

                {% for error in form.title.errors %}

                    <p class="mt-1 text-[10px] text-red-600">
                        {{ error }}
                    </p>

                {% endfor %}

            </div>

        </div>

    </section>


    <!-- =====================================================
         SUBJECTIVE
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200 bg-white
        "
    >

        <header
            class="
                flex items-center justify-between
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <div>

                <h2
                    class="
                        text-[11px] font-semibold
                        uppercase tracking-wide
                        text-slate-700
                    "
                >
                    Subjective
                </h2>

                <p class="mt-0.5 text-[10px] text-slate-500">
                    Patient-reported symptoms, concerns, and history.
                </p>

            </div>

            <span
                class="
                    rounded bg-white
                    px-2 py-0.5
                    text-[10px] font-bold text-slate-500
                "
            >
                S
            </span>

        </header>


        <div class="p-3">

            {{ form.subjective }}

            {% for error in form.subjective.errors %}
                <p class="mt-1 text-[10px] text-red-600">
                    {{ error }}
                </p>
            {% endfor %}

        </div>

    </section>


    <!-- =====================================================
         OBJECTIVE
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200 bg-white
        "
    >

        <header
            class="
                flex items-center justify-between
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <div>

                <h2
                    class="
                        text-[11px] font-semibold
                        uppercase tracking-wide
                        text-slate-700
                    "
                >
                    Objective
                </h2>

                <p class="mt-0.5 text-[10px] text-slate-500">
                    Examination findings and objective observations.
                </p>

            </div>

            <span
                class="
                    rounded bg-white
                    px-2 py-0.5
                    text-[10px] font-bold text-slate-500
                "
            >
                O
            </span>

        </header>


        <div class="p-3">

            {{ form.objective }}

            {% for error in form.objective.errors %}
                <p class="mt-1 text-[10px] text-red-600">
                    {{ error }}
                </p>
            {% endfor %}

        </div>

    </section>


    <!-- =====================================================
         ASSESSMENT
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200 bg-white
        "
    >

        <header
            class="
                flex items-center justify-between
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <div>

                <h2
                    class="
                        text-[11px] font-semibold
                        uppercase tracking-wide
                        text-slate-700
                    "
                >
                    Assessment
                </h2>

                <p class="mt-0.5 text-[10px] text-slate-500">
                    Clinical impression, interpretation, and assessment.
                </p>

            </div>

            <span
                class="
                    rounded bg-white
                    px-2 py-0.5
                    text-[10px] font-bold text-slate-500
                "
            >
                A
            </span>

        </header>


        <div class="p-3">

            {{ form.assessment }}

            {% for error in form.assessment.errors %}
                <p class="mt-1 text-[10px] text-red-600">
                    {{ error }}
                </p>
            {% endfor %}

        </div>

    </section>


    <!-- =====================================================
         PLAN
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200 bg-white
        "
    >

        <header
            class="
                flex items-center justify-between
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <div>

                <h2
                    class="
                        text-[11px] font-semibold
                        uppercase tracking-wide
                        text-slate-700
                    "
                >
                    Plan
                </h2>

                <p class="mt-0.5 text-[10px] text-slate-500">
                    Treatment, referrals, education, and follow-up.
                </p>

            </div>

            <span
                class="
                    rounded bg-white
                    px-2 py-0.5
                    text-[10px] font-bold text-slate-500
                "
            >
                P
            </span>

        </header>


        <div class="p-3">

            {{ form.plan }}

            {% for error in form.plan.errors %}
                <p class="mt-1 text-[10px] text-red-600">
                    {{ error }}
                </p>
            {% endfor %}

        </div>

    </section>


    <!-- =====================================================
         ADDITIONAL DOCUMENTATION
    ====================================================== -->

    <section
        class="
            overflow-hidden rounded-lg
            border border-slate-200 bg-white
        "
    >

        <header
            class="
                border-b border-slate-200
                bg-slate-50 px-3 py-2
            "
        >

            <h2
                class="
                    text-[11px] font-semibold
                    uppercase tracking-wide
                    text-slate-700
                "
            >
                Additional Documentation
            </h2>

            <p class="mt-0.5 text-[10px] text-slate-500">
                Optional narrative information not captured above.
            </p>

        </header>


        <div class="p-3">

            {{ form.content }}

            {% for error in form.content.errors %}
                <p class="mt-1 text-[10px] text-red-600">
                    {{ error }}
                </p>
            {% endfor %}

        </div>

    </section>

</div>
HTML


# ============================================================
# PARTIAL: NOTE DETAIL
# ============================================================

cat > "$PARTIAL_DIR/note_detail.html" <<'HTML'
{% comment %}
============================================================
CLINICAL NOTE DETAIL PARTIAL

File:
apps/clinical_notes/templates/clinical_notes/partials/note_detail.html
============================================================
{% endcomment %}

<section class="flex h-full min-h-0 flex-col bg-white">

    <!-- =====================================================
         HEADER
    ====================================================== -->

    <header
        class="
            flex shrink-0 flex-col gap-2
            border-b border-slate-200
            px-4 py-3
            sm:flex-row
            sm:items-center
            sm:justify-between
        "
    >

        <div class="min-w-0">

            <div class="flex flex-wrap items-center gap-2">

                <h1 class="text-base font-semibold text-slate-900">

                    {% if note.title %}
                        {{ note.title }}
                    {% else %}
                        {{ note.get_note_type_display }}
                    {% endif %}

                </h1>


                <span
                    class="
                        rounded px-1.5 py-0.5
                        text-[9px] font-semibold
                        uppercase tracking-wide

                        {% if note.status == 'draft' %}
                            bg-amber-50 text-amber-700
                        {% elif note.status == 'signed' %}
                            bg-emerald-50 text-emerald-700
                        {% elif note.status == 'amended' %}
                            bg-blue-50 text-blue-700
                        {% else %}
                            bg-slate-100 text-slate-600
                        {% endif %}
                    "
                >
                    {{ note.get_status_display }}
                </span>

            </div>


            <div
                class="
                    mt-1 flex flex-wrap
                    gap-x-3 gap-y-1
                    text-[11px] text-slate-500
                "
            >

                <span>
                    {{ note.get_note_type_display }}
                </span>

                <span>
                    {{ note.author.get_full_name|default:note.author.username }}
                </span>

                <span>
                    {{ note.created_at|date:"M j, Y H:i" }}
                </span>

            </div>

        </div>


        <!-- =================================================
             ACTIONS
        ================================================== -->

        <div class="flex flex-wrap items-center gap-2">

            {% if note.can_edit %}

                <a
                    href="{% url 'clinical_notes:update' note.pk %}"
                    hx-get="{% url 'clinical_notes:update' note.pk %}"
                    hx-target="#clinical-notes-workspace"
                    hx-swap="innerHTML"
                    hx-push-url="true"
                    class="
                        inline-flex h-8 items-center
                        rounded-md border border-slate-300
                        bg-white px-3
                        text-xs font-medium text-slate-600
                        hover:bg-slate-50
                    "
                >
                    Edit
                </a>


                <form
                    method="post"
                    action="{% url 'clinical_notes:sign' note.pk %}"
                    hx-post="{% url 'clinical_notes:sign' note.pk %}"
                >

                    {% csrf_token %}

                    <button
                        type="submit"
                        class="
                            inline-flex h-8 items-center
                            rounded-md bg-ehr-700
                            px-3
                            text-xs font-semibold text-white
                            shadow-sm
                            hover:bg-ehr-800
                        "
                    >
                        Sign Note
                    </button>

                </form>

            {% endif %}


            <a
                href="{% url 'clinical_notes:list' note.patient.pk %}"
                hx-get="{% url 'clinical_notes:list' note.patient.pk %}"
                hx-target="#clinical-notes-workspace"
                hx-swap="innerHTML"
                hx-push-url="true"
                class="
                    inline-flex h-8 items-center
                    rounded-md border border-slate-300
                    bg-white px-3
                    text-xs font-medium text-slate-600
                    hover:bg-slate-50
                "
            >
                Back
            </a>

        </div>

    </header>


    <!-- =====================================================
         PATIENT / ENCOUNTER STRIP
    ====================================================== -->

    <div
        class="
            flex shrink-0 flex-wrap
            gap-x-5 gap-y-1
            border-b border-slate-200
            bg-slate-50 px-4 py-2
            text-[11px]
        "
    >

        <div>
            <span class="text-slate-500">
                Patient
            </span>

            <span class="ml-1 font-semibold text-slate-800">
                {{ note.patient }}
            </span>
        </div>


        {% if note.encounter %}

            <div>
                <span class="text-slate-500">
                    Encounter
                </span>

                <span class="ml-1 font-medium text-slate-800">
                    {{ note.encounter }}
                </span>
            </div>

        {% endif %}

    </div>


    <!-- =====================================================
         NOTE CONTENT
    ====================================================== -->

    <div class="min-h-0 flex-1 overflow-y-auto px-4 py-4">

        <article class="mx-auto max-w-6xl">


            {% if note.status == "voided" %}

                <div
                    class="
                        mb-4 rounded-md
                        border border-red-200
                        bg-red-50 px-3 py-2
                    "
                >

                    <p class="text-xs font-semibold text-red-700">
                        This clinical note has been voided.
                    </p>

                    {% if note.void_reason %}

                        <p class="mt-1 text-xs text-red-600">
                            {{ note.void_reason }}
                        </p>

                    {% endif %}

                </div>

            {% endif %}


            <div class="space-y-5">


                {% if note.subjective %}

                    <section>

                        <h2
                            class="
                                border-b border-slate-200
                                pb-1 text-[11px] font-semibold
                                uppercase tracking-wide text-slate-500
                            "
                        >
                            Subjective
                        </h2>

                        <div
                            class="
                                mt-2 whitespace-pre-line
                                text-sm leading-6 text-slate-800
                            "
                        >{{ note.subjective }}</div>

                    </section>

                {% endif %}


                {% if note.objective %}

                    <section>

                        <h2
                            class="
                                border-b border-slate-200
                                pb-1 text-[11px] font-semibold
                                uppercase tracking-wide text-slate-500
                            "
                        >
                            Objective
                        </h2>

                        <div
                            class="
                                mt-2 whitespace-pre-line
                                text-sm leading-6 text-slate-800
                            "
                        >{{ note.objective }}</div>

                    </section>

                {% endif %}


                {% if note.assessment %}

                    <section>

                        <h2
                            class="
                                border-b border-slate-200
                                pb-1 text-[11px] font-semibold
                                uppercase tracking-wide text-slate-500
                            "
                        >
                            Assessment
                        </h2>

                        <div
                            class="
                                mt-2 whitespace-pre-line
                                text-sm leading-6 text-slate-800
                            "
                        >{{ note.assessment }}</div>

                    </section>

                {% endif %}


                {% if note.plan %}

                    <section>

                        <h2
                            class="
                                border-b border-slate-200
                                pb-1 text-[11px] font-semibold
                                uppercase tracking-wide text-slate-500
                            "
                        >
                            Plan
                        </h2>

                        <div
                            class="
                                mt-2 whitespace-pre-line
                                text-sm leading-6 text-slate-800
                            "
                        >{{ note.plan }}</div>

                    </section>

                {% endif %}


                {% if note.content %}

                    <section>

                        <h2
                            class="
                                border-b border-slate-200
                                pb-1 text-[11px] font-semibold
                                uppercase tracking-wide text-slate-500
                            "
                        >
                            Additional Documentation
                        </h2>

                        <div
                            class="
                                mt-2 whitespace-pre-line
                                text-sm leading-6 text-slate-800
                            "
                        >{{ note.content }}</div>

                    </section>

                {% endif %}

            </div>


            <!-- =================================================
                 ELECTRONIC SIGNATURE
            ================================================== -->

            {% if note.signed_at %}

                <footer
                    class="
                        mt-8 border-t border-slate-300
                        pt-4
                    "
                >

                    <p class="text-xs font-semibold text-slate-800">
                        Electronically Signed
                    </p>

                    <p class="mt-1 text-xs text-slate-600">
                        {{ note.signed_by.get_full_name|default:note.signed_by.username }}
                    </p>

                    <p class="text-[11px] text-slate-500">
                        {{ note.signed_at|date:"M j, Y H:i" }}
                    </p>

                </footer>

            {% endif %}

        </article>

    </div>

</section>
HTML


# ============================================================
# COMPLETE
# ============================================================

echo ""
echo "============================================================"
echo " Clinical Notes module created successfully"
echo "============================================================"
echo ""
echo "Created:"
echo "  $APP_DIR/models.py"
echo "  $APP_DIR/forms.py"
echo "  $APP_DIR/views.py"
echo "  $APP_DIR/urls.py"
echo "  $APP_DIR/admin.py"
echo "  $APP_DIR/apps.py"
echo "  $TEMPLATE_DIR/note_list.html"
echo "  $TEMPLATE_DIR/note_form.html"
echo "  $TEMPLATE_DIR/note_detail.html"
echo "  $PARTIAL_DIR/note_list.html"
echo "  $PARTIAL_DIR/note_row.html"
echo "  $PARTIAL_DIR/note_form.html"
echo "  $PARTIAL_DIR/note_form_fields.html"
echo "  $PARTIAL_DIR/note_detail.html"
echo ""
echo "NEXT:"
echo "1. Add apps.clinical_notes to INSTALLED_APPS"
echo "2. Include apps.clinical_notes.urls in project urls.py"
echo "3. Run:"
echo "       python manage.py makemigrations clinical_notes"
echo "       python manage.py migrate"
echo "       python manage.py check"
echo ""