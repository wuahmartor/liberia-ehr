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

    chief_complaint = models.CharField(

    max_length=255,

    db_index=True,

    help_text=(

        "Primary reason, symptom, concern, or clinical issue "

        "being documented in this note."

    ),

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
