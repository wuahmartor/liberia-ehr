"""
Liberia EHR Encounter Models

File:
apps/encounters/models.py

Purpose:
- Represent patient visits and episodes of care.
- Distinguish patient registration from the clinical encounter.
- Track check-in, triage, clinical start, and completion timestamps.
- Connect diagnoses, medications, orders, nursing records, and results.
- Support outpatient, inpatient, emergency, telehealth, and community care.

Recommended workflow:
- New patient:
  Search -> Register -> Verify identity -> Create encounter ->
  Arrive/check in -> Triage -> Clinical care -> Complete.

- Existing patient:
  Search -> Verify identity/update demographics -> Create encounter ->
  Arrive/check in -> Triage -> Clinical care -> Complete.

- Emergency patient:
  Temporary registration -> Immediate encounter -> Stabilize/treat ->
  Complete registration and identity verification later.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Encounter(models.Model):
    """
    Represents a clinical interaction between a patient and the health system.

    The Patient model represents the person's longitudinal identity and
    demographics. This Encounter model represents one specific visit or
    episode of care.

    A single patient may therefore have many encounters over time.
    """

    # =================================================================
    # ENCOUNTER TYPE
    # =================================================================

    class EncounterType(models.TextChoices):
        OUTPATIENT = "OUTPATIENT", "Outpatient"
        INPATIENT = "INPATIENT", "Inpatient"
        EMERGENCY = "EMERGENCY", "Emergency"
        OBSERVATION = "OBSERVATION", "Observation"
        TELEHEALTH = "TELEHEALTH", "Telehealth"
        HOME_VISIT = "HOME_VISIT", "Home visit"
        COMMUNITY = "COMMUNITY", "Community care"
        MATERNITY = "MATERNITY", "Maternity"
        SURGICAL = "SURGICAL", "Surgical"
        PHARMACY = "PHARMACY", "Pharmacy consultation"
        LABORATORY = "LABORATORY", "Laboratory only"
        IMAGING = "IMAGING", "Imaging only"
        OTHER = "OTHER", "Other"

    # =================================================================
    # ENCOUNTER STATUS
    # =================================================================

    class EncounterStatus(models.TextChoices):
        PLANNED = "PLANNED", "Planned"
        SCHEDULED = "SCHEDULED", "Scheduled"
        ARRIVED = "ARRIVED", "Arrived"
        TRIAGED = "TRIAGED", "Triaged"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        ON_HOLD = "ON_HOLD", "On hold"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        ENTERED_IN_ERROR = "ENTERED_IN_ERROR", "Entered in error"

    # =================================================================
    # ENCOUNTER PRIORITY
    # =================================================================

    class Priority(models.TextChoices):
        ROUTINE = "ROUTINE", "Routine"
        URGENT = "URGENT", "Urgent"
        EMERGENCY = "EMERGENCY", "Emergency"

    # =================================================================
    # PRIMARY IDENTIFIERS
    # =================================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    encounter_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text="Automatically generated encounter identifier.",
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="encounters",
        help_text="The patient receiving care during this encounter.",
    )

    # =================================================================
    # ENCOUNTER CLASSIFICATION
    # =================================================================

    encounter_type = models.CharField(
        max_length=30,
        choices=EncounterType.choices,
        default=EncounterType.OUTPATIENT,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=EncounterStatus.choices,
        default=EncounterStatus.PLANNED,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.ROUTINE,
        db_index=True,
    )

    reason_for_visit = models.CharField(
        max_length=500,
        blank=True,
        db_index=True,
        help_text="Chief complaint or primary reason for the encounter.",
    )

    # =================================================================
    # REGISTRATION AND IDENTITY VERIFICATION
    # =================================================================

    registration_completed = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that the minimum required registration information "
            "has been completed for this visit."
        ),
    )

    identity_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that staff verified the patient using the required "
            "patient identifiers."
        ),
    )

    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Date and time registration requirements were completed "
            "for this encounter."
        ),
    )

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="registered_encounters",
        help_text="Staff member who completed encounter registration.",
    )

    # =================================================================
    # CHECK-IN AND ARRIVAL
    # =================================================================

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Date and time the patient arrived or checked in.",
    )

    check_in_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checked_in_encounters",
        help_text="Staff member who checked the patient in.",
    )

    # =================================================================
    # TRIAGE
    # =================================================================

    triaged_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Date and time triage was completed.",
    )

    triaged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triaged_encounters",
        help_text="Nurse or clinician who completed triage.",
    )

    # =================================================================
    # CLINICAL CARE TIMING
    # =================================================================

    start_datetime = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=(
            "Planned or administrative beginning of the encounter. "
            "Use clinical_start_at for the time direct clinical care began."
        ),
    )

    clinical_start_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Date and time direct clinical care began.",
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Date and time the encounter was clinically completed.",
    )

    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text=(
            "Administrative end of the encounter. This normally matches "
            "completed_at when the encounter is completed."
        ),
    )

    # =================================================================
    # CARE TEAM
    # =================================================================

    attending_provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attending_encounters",
        help_text="Primary provider responsible for this encounter.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_encounters",
        help_text="User who created the encounter record.",
    )

    # =================================================================
    # ADDITIONAL INFORMATION
    # =================================================================

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # =================================================================
    # MODEL META
    # =================================================================

    class Meta:
        ordering = [
            "-start_datetime",
            "-created_at",
        ]

        verbose_name = "encounter"
        verbose_name_plural = "encounters"

        indexes = [
            models.Index(
                fields=["patient", "status"],
                name="enc_patient_status_idx",
            ),
            models.Index(
                fields=["patient", "start_datetime"],
                name="enc_patient_start_idx",
            ),
            models.Index(
                fields=["encounter_type", "status"],
                name="enc_type_status_idx",
            ),
            models.Index(
                fields=["attending_provider", "status"],
                name="enc_provider_status_idx",
            ),
            models.Index(
                fields=["status", "arrived_at"],
                name="enc_status_arrived_idx",
            ),
            models.Index(
                fields=["status", "triaged_at"],
                name="enc_status_triaged_idx",
            ),
            models.Index(
                fields=["registration_completed", "identity_verified"],
                name="enc_registration_identity_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(end_datetime__isnull=True)
                    | Q(end_datetime__gte=models.F("start_datetime"))
                ),
                name="encounter_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(completed_at__isnull=True)
                    | Q(
                        completed_at__gte=models.F(
                            "start_datetime"
                        )
                    )
                ),
                name="enc_completed_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(clinical_start_at__isnull=True)
                    | Q(
                        clinical_start_at__gte=models.F(
                            "start_datetime"
                        )
                    )
                ),
                name="enc_clinical_start_after_start",
            ),
        ]

    # =================================================================
    # STRING REPRESENTATION
    # =================================================================

    def __str__(self):
        return (
            f"{self.encounter_number} — "
            f"{self.patient} — "
            f"{self.get_encounter_type_display()}"
        )

    # =================================================================
    # VALIDATION
    # =================================================================

    def clean(self):
        """
        Validate encounter timestamps and workflow requirements.

        Validation permits emergency encounters to begin before complete
        registration because urgent care must not be delayed.
        """

        super().clean()

        errors = {}

        # -------------------------------------------------------------
        # END DATE VALIDATION
        # -------------------------------------------------------------

        if (
            self.start_datetime
            and self.end_datetime
            and self.end_datetime < self.start_datetime
        ):
            errors["end_datetime"] = (
                "The encounter end time cannot be before its start time."
            )

        # -------------------------------------------------------------
        # REGISTRATION VALIDATION
        # -------------------------------------------------------------

        if self.registration_completed and not self.registered_at:
            errors["registered_at"] = (
                "Provide the registration completion time when "
                "registration is marked complete."
            )

        if self.registered_at and not self.registration_completed:
            errors["registration_completed"] = (
                "Mark registration as completed when a registration "
                "completion time has been recorded."
            )

        # -------------------------------------------------------------
        # ARRIVAL VALIDATION
        # -------------------------------------------------------------

        if self.status in {
            self.EncounterStatus.ARRIVED,
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        } and not self.arrived_at:
            errors["arrived_at"] = (
                "An arrived or active encounter must have an arrival time."
            )

        # -------------------------------------------------------------
        # TRIAGE VALIDATION
        # -------------------------------------------------------------

        if self.status == self.EncounterStatus.TRIAGED and not self.triaged_at:
            errors["triaged_at"] = (
                "A triaged encounter must have a triage completion time."
            )

        if (
            self.arrived_at
            and self.triaged_at
            and self.triaged_at < self.arrived_at
        ):
            errors["triaged_at"] = (
                "Triage cannot be completed before the patient arrives."
            )

        # -------------------------------------------------------------
        # CLINICAL START VALIDATION
        # -------------------------------------------------------------

        if (
            self.status == self.EncounterStatus.IN_PROGRESS
            and not self.clinical_start_at
        ):
            errors["clinical_start_at"] = (
                "An encounter in progress must have a clinical start time."
            )

        if (
            self.arrived_at
            and self.clinical_start_at
            and self.clinical_start_at < self.arrived_at
        ):
            errors["clinical_start_at"] = (
                "Clinical care cannot begin before the patient arrives."
            )

        # -------------------------------------------------------------
        # COMPLETION VALIDATION
        # -------------------------------------------------------------

        if self.status == self.EncounterStatus.COMPLETED:
            if not self.completed_at:
                errors["completed_at"] = (
                    "A completed encounter must have a completion time."
                )

            if not self.end_datetime:
                errors["end_datetime"] = (
                    "A completed encounter must have an end date and time."
                )

        if (
            self.clinical_start_at
            and self.completed_at
            and self.completed_at < self.clinical_start_at
        ):
            errors["completed_at"] = (
                "The completion time cannot precede the clinical start time."
            )

        if (
            self.completed_at
            and self.end_datetime
            and self.end_datetime < self.completed_at
        ):
            errors["end_datetime"] = (
                "The administrative end time cannot precede the clinical "
                "completion time."
            )

        # -------------------------------------------------------------
        # CANCELLED AND ERROR STATUS VALIDATION
        # -------------------------------------------------------------

        if self.status in {
            self.EncounterStatus.CANCELLED,
            self.EncounterStatus.ENTERED_IN_ERROR,
        } and self.completed_at:
            errors["completed_at"] = (
                "A cancelled or erroneous encounter cannot have a "
                "clinical completion time."
            )

        if errors:
            raise ValidationError(errors)

    # =================================================================
    # SAVE WORKFLOW AUTOMATION
    # =================================================================

    def save(self, *args, **kwargs):
        """
        Generate the encounter number and populate workflow timestamps.

        Timestamps are populated only when they are empty. Existing values
        are preserved so the historical workflow remains accurate.
        """

        current_time = timezone.now()

        # -------------------------------------------------------------
        # GENERATE ENCOUNTER NUMBER
        # -------------------------------------------------------------

        if not self.encounter_number:
            date_part = timezone.localdate().strftime("%Y%m%d")
            uuid_part = uuid.uuid4().hex[:8].upper()

            self.encounter_number = (
                f"ENC-{date_part}-{uuid_part}"
            )

        # -------------------------------------------------------------
        # REGISTRATION TIMESTAMP
        # -------------------------------------------------------------

        if self.registration_completed and not self.registered_at:
            self.registered_at = current_time

        # -------------------------------------------------------------
        # STATUS-BASED WORKFLOW TIMESTAMPS
        # -------------------------------------------------------------

        if self.status in {
            self.EncounterStatus.ARRIVED,
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        } and not self.arrived_at:
            self.arrived_at = current_time

        if self.status in {
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        } and not self.triaged_at:
            self.triaged_at = current_time

        if self.status in {
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        } and not self.clinical_start_at:
            self.clinical_start_at = current_time

        if self.status == self.EncounterStatus.COMPLETED:
            if not self.completed_at:
                self.completed_at = current_time

            if not self.end_datetime:
                self.end_datetime = self.completed_at

        # -------------------------------------------------------------
        # CANCELLED OR ERROR RECORDS ARE NOT ACTIVE
        # -------------------------------------------------------------

        if self.status in {
            self.EncounterStatus.CANCELLED,
            self.EncounterStatus.ENTERED_IN_ERROR,
        }:
            self.is_active = False

        super().save(*args, **kwargs)

    # =================================================================
    # WORKFLOW PROPERTIES
    # =================================================================

    @property
    def is_open(self):
        """
        Return True when the encounter remains operationally open.
        """

        return self.status in {
            self.EncounterStatus.PLANNED,
            self.EncounterStatus.SCHEDULED,
            self.EncounterStatus.ARRIVED,
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
        }

    @property
    def is_ready_for_triage(self):
        """
        Return True when the patient has arrived and can be triaged.
        """

        return (
            self.status == self.EncounterStatus.ARRIVED
            and self.arrived_at is not None
        )

    @property
    def is_ready_for_clinician(self):
        """
        Return True when triage is complete and clinical care may begin.
        """

        return (
            self.status == self.EncounterStatus.TRIAGED
            and self.triaged_at is not None
        )

    @property
    def registration_status(self):
        """
        Return a readable registration workflow status.
        """

        if self.registration_completed and self.identity_verified:
            return "Registration complete and identity verified"

        if self.registration_completed:
            return "Registration complete; identity verification pending"

        return "Registration incomplete"

    @property
    def duration(self):
        """
        Return total administrative encounter duration.
        """

        if not self.start_datetime:
            return None

        ending_time = self.end_datetime or timezone.now()

        return ending_time - self.start_datetime

    @property
    def clinical_duration(self):
        """
        Return the duration of direct clinical care.
        """

        if not self.clinical_start_at:
            return None

        ending_time = (
            self.completed_at
            or self.end_datetime
            or timezone.now()
        )

        return ending_time - self.clinical_start_at

    @property
    def waiting_time_to_triage(self):
        """
        Return the time between arrival and triage completion.
        """

        if not self.arrived_at or not self.triaged_at:
            return None

        return self.triaged_at - self.arrived_at

    @property
    def waiting_time_to_clinician(self):
        """
        Return the time between arrival and the beginning of clinical care.
        """

        if not self.arrived_at or not self.clinical_start_at:
            return None

        return self.clinical_start_at - self.arrived_at