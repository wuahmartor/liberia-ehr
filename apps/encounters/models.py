"""
Liberia EHR Encounter Models

File:
apps/encounters/models.py

Purpose:
- Represent patient visits and episodes of care.
- Distinguish patient registration from the clinical encounter.
- Track registration, identity verification, arrival, triage,
  clinical start, and completion timestamps.
- Automatically record the staff member responsible for workflow actions.
- Connect diagnoses, medications, orders, nursing records, and results.
- Support outpatient, inpatient, emergency, telehealth, community,
  laboratory, imaging, pharmacy, maternity, and surgical care.

Important implementation rule:
- Dates, times, identifiers, and workflow timestamps are generated
  automatically by the model.
- Staff recorder fields are populated from the authenticated user by
  calling:

      encounter.save(actor=request.user)

  A Django model cannot independently determine request.user because
  models do not have direct access to the HTTP request.

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
from django.db.models import F, Q
from django.utils import timezone


class Encounter(models.Model):
    """
    Represents one clinical interaction between a patient and the
    healthcare system.

    The Patient model represents the person's longitudinal identity.
    The Encounter model represents one specific visit or episode of care.

    One patient may have many encounters over time.
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
    # REGISTRATION
    # =================================================================

    registration_completed = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that the minimum required registration information "
            "has been completed for this visit."
        ),
    )

    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when registration is marked complete."
        ),
    )

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="registered_encounters",
        help_text=(
            "Automatically populated with the staff member who completed "
            "encounter registration."
        ),
    )

    # =================================================================
    # IDENTITY VERIFICATION
    # =================================================================

    identity_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that staff verified the patient using the required "
            "patient identifiers."
        ),
    )

    identity_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when patient identity is verified."
        ),
    )

    identity_verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="identity_verified_encounters",
        help_text=(
            "Automatically populated with the staff member who verified "
            "the patient's identity."
        ),
    )

    # =================================================================
    # CHECK-IN AND ARRIVAL
    # =================================================================

    arrived_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when the encounter status becomes "
            "arrived or advances beyond arrival."
        ),
    )

    check_in_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="checked_in_encounters",
        help_text=(
            "Automatically populated with the staff member who checked "
            "the patient in."
        ),
    )

    # =================================================================
    # TRIAGE
    # =================================================================

    triaged_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when triage is completed."
        ),
    )

    triaged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="triaged_encounters",
        help_text=(
            "Automatically populated with the nurse or clinician who "
            "completed triage."
        ),
    )

    # =================================================================
    # CLINICAL CARE TIMING
    # =================================================================

    start_datetime = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=(
            "Administrative beginning of the encounter. Automatically "
            "defaults to the time the encounter is created."
        ),
    )

    clinical_start_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when direct clinical care begins."
        ),
    )

    clinical_started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="clinically_started_encounters",
        help_text=(
            "Automatically populated with the clinician who began "
            "direct clinical care."
        ),
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Automatically recorded when the encounter is completed."
        ),
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="completed_encounters",
        help_text=(
            "Automatically populated with the staff member who completed "
            "the encounter."
        ),
    )

    end_datetime = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
        help_text=(
            "Administrative end of the encounter. Automatically populated "
            "when the encounter is completed."
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
        editable=False,
        help_text=(
            "Automatically populated with the authenticated user who "
            "created the encounter."
        ),
    )

    # =================================================================
    # CANCELLATION AND ERROR AUDIT
    # =================================================================

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="cancelled_encounters",
    )

    entered_in_error_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    entered_in_error_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="erroneous_encounters",
    )

    status_reason = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Reason for cancellation, hold status, or entry-in-error."
        ),
    )

    # =================================================================
    # ADDITIONAL INFORMATION
    # =================================================================

    notes = models.TextField(
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        editable=False,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        editable=False,
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
                fields=[
                    "registration_completed",
                    "identity_verified",
                ],
                name="enc_registration_identity_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(end_datetime__isnull=True)
                    | Q(end_datetime__gte=F("start_datetime"))
                ),
                name="encounter_end_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(completed_at__isnull=True)
                    | Q(completed_at__gte=F("start_datetime"))
                ),
                name="enc_completed_after_start",
            ),
            models.CheckConstraint(
                condition=(
                    Q(clinical_start_at__isnull=True)
                    | Q(clinical_start_at__gte=F("start_datetime"))
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
    # INTERNAL WORKFLOW HELPERS
    # =================================================================

    @property
    def requires_triage(self):
        """
        Return whether this encounter type normally requires triage.

        Laboratory-only, imaging-only, and pharmacy-only encounters do
        not automatically require a formal triage stage.
        """

        return self.encounter_type not in {
            self.EncounterType.LABORATORY,
            self.EncounterType.IMAGING,
            self.EncounterType.PHARMACY,
        }

    def _previous_database_values(self):
        """
        Return selected previous values for transition detection.

        This prevents a normal edit from being treated as a new workflow
        action after a timestamp has already been recorded.
        """

        if self._state.adding or not self.pk:
            return {}

        return (
            type(self)
            .objects
            .filter(pk=self.pk)
            .values(
                "status",
                "registration_completed",
                "identity_verified",
            )
            .first()
            or {}
        )

    @staticmethod
    def _add_update_fields(kwargs, field_names):
        """
        Add automatically changed fields to update_fields.

        Without this helper, calling:

            encounter.save(update_fields={"status"}, actor=request.user)

        could change status without saving its automatic timestamp and
        recorder fields.
        """

        update_fields = kwargs.get("update_fields")

        if update_fields is None:
            return

        kwargs["update_fields"] = set(update_fields).union(field_names)

    # =================================================================
    # VALIDATION
    # =================================================================

    def clean(self):
        """
        Validate encounter workflow consistency and timestamp ordering.

        Automatically generated timestamps are not required here because
        ModelForm validation calls clean() before save() has populated them.

        The save() method populates automatic timestamps first and then calls
        full_clean(), so timestamp requirements are enforced after automatic
        values are available.
        """

        super().clean()

        errors = {}

        # =================================================================
        # GENERAL START AND END VALIDATION
        # =================================================================

        if (
            self.start_datetime
            and self.end_datetime
            and self.end_datetime < self.start_datetime
        ):
            errors["end_datetime"] = (
                "The encounter end time cannot be before its start time."
            )

        # =================================================================
        # REGISTRATION CONSISTENCY
        # =================================================================

        # registered_at is automatically generated during save().
        # Only reject a recorded timestamp when registration is not marked
        # complete.
        if self.registered_at and not self.registration_completed:
            errors["registration_completed"] = (
                "Registration must be marked complete when a registration "
                "completion time has been recorded."
            )

        # =================================================================
        # IDENTITY VERIFICATION CONSISTENCY
        # =================================================================

        # identity_verified_at is automatically generated during save().
        if self.identity_verified_at and not self.identity_verified:
            errors["identity_verified"] = (
                "Identity must be marked verified when an identity "
                "verification time has been recorded."
            )

        # Non-emergency encounters should normally complete registration
        # before identity verification.
        if (
            self.identity_verified
            and not self.registration_completed
            and self.encounter_type != self.EncounterType.EMERGENCY
        ):
            errors["identity_verified"] = (
                "Complete registration before confirming identity "
                "verification."
            )

        # =================================================================
        # ARRIVAL ORDER VALIDATION
        # =================================================================

        if (
            self.start_datetime
            and self.arrived_at
            and self.arrived_at < self.start_datetime
        ):
            errors["arrived_at"] = (
                "The arrival time cannot be before the encounter start time."
            )

        # Do not require arrived_at here. It is automatically populated
        # during save() based on encounter status.

        # =================================================================
        # TRIAGE ORDER VALIDATION
        # =================================================================

        if (
            self.arrived_at
            and self.triaged_at
            and self.triaged_at < self.arrived_at
        ):
            errors["triaged_at"] = (
                "Triage cannot be completed before the patient arrives."
            )

        # Do not require triaged_at here. It is automatically populated
        # during save() when appropriate.

        # =================================================================
        # CLINICAL START ORDER VALIDATION
        # =================================================================

        if (
            self.start_datetime
            and self.clinical_start_at
            and self.clinical_start_at < self.start_datetime
        ):
            errors["clinical_start_at"] = (
                "Clinical care cannot begin before the encounter starts."
            )

        if (
            self.arrived_at
            and self.clinical_start_at
            and self.clinical_start_at < self.arrived_at
        ):
            errors["clinical_start_at"] = (
                "Clinical care cannot begin before the patient arrives."
            )

        # Do not require clinical_start_at here. It is automatically
        # populated during save().

        # =================================================================
        # COMPLETION ORDER VALIDATION
        # =================================================================

        if (
            self.start_datetime
            and self.completed_at
            and self.completed_at < self.start_datetime
        ):
            errors["completed_at"] = (
                "The completion time cannot precede the encounter start time."
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

        # completed_at and end_datetime are generated during save() when
        # status becomes COMPLETED. Do not require them during ModelForm
        # validation.

        # =================================================================
        # CANCELLED AND ENTERED-IN-ERROR VALIDATION
        # =================================================================

        if self.status in {
            self.EncounterStatus.CANCELLED,
            self.EncounterStatus.ENTERED_IN_ERROR,
        }:
            if self.completed_at:
                errors["completed_at"] = (
                    "A cancelled encounter or an encounter entered in error "
                    "cannot have a clinical completion time."
                )

            if not self.status_reason.strip():
                errors["status_reason"] = (
                    "Provide a reason when cancelling an encounter or marking "
                    "it as entered in error."
                )

        # =================================================================
        # COMPLETED ENCOUNTER CONSISTENCY
        # =================================================================

        if (
            self.status != self.EncounterStatus.COMPLETED
            and self.completed_at
            and self.status not in {
                self.EncounterStatus.CANCELLED,
                self.EncounterStatus.ENTERED_IN_ERROR,
            }
        ):
            errors["status"] = (
                "An encounter with a clinical completion time must have "
                "Completed status."
            )

        if errors:
            raise ValidationError(errors)

    # =================================================================
    # SAVE WORKFLOW AUTOMATION
    # =================================================================

    def save(self, *args, actor=None, validate=True, **kwargs):
        """
        Save the encounter and populate automatic workflow information.

        Parameters:
            actor:
                The authenticated user performing the action. Views,
                forms, services, and admin classes should call:

                    encounter.save(actor=request.user)

            validate:
                Run model validation before saving. Defaults to True.

        Existing timestamps and recorder fields are preserved to maintain
        an accurate historical audit trail.
        """

        current_time = timezone.now()
        previous = self._previous_database_values()
        automatic_fields = set()

        previous_status = previous.get("status")
        previous_registration_completed = previous.get(
            "registration_completed",
            False,
        )
        previous_identity_verified = previous.get(
            "identity_verified",
            False,
        )

        # -------------------------------------------------------------
        # GENERATE ENCOUNTER NUMBER
        # -------------------------------------------------------------

        if not self.encounter_number:
            date_part = timezone.localdate().strftime("%Y%m%d")
            uuid_part = uuid.uuid4().hex[:8].upper()

            self.encounter_number = f"ENC-{date_part}-{uuid_part}"
            automatic_fields.add("encounter_number")

        # -------------------------------------------------------------
        # ASSIGN ENCOUNTER CREATOR
        # -------------------------------------------------------------

        if self._state.adding and not self.created_by_id:
            if actor is None:
                raise ValidationError(
                    {
                        "created_by": (
                            "The authenticated user is required when "
                            "creating an encounter. Call "
                            "encounter.save(actor=request.user)."
                        )
                    }
                )

            self.created_by = actor
            automatic_fields.add("created_by")

        # -------------------------------------------------------------
        # REGISTRATION AUTOMATION
        # -------------------------------------------------------------

        registration_just_completed = (
            self.registration_completed
            and not previous_registration_completed
        )

        if self.registration_completed and not self.registered_at:
            self.registered_at = current_time
            automatic_fields.add("registered_at")

        if (
            registration_just_completed
            and actor is not None
            and not self.registered_by_id
        ):
            self.registered_by = actor
            automatic_fields.add("registered_by")

        # -------------------------------------------------------------
        # IDENTITY VERIFICATION AUTOMATION
        # -------------------------------------------------------------

        identity_just_verified = (
            self.identity_verified
            and not previous_identity_verified
        )

        if self.identity_verified and not self.identity_verified_at:
            self.identity_verified_at = current_time
            automatic_fields.add("identity_verified_at")

        if (
            identity_just_verified
            and actor is not None
            and not self.identity_verified_by_id
        ):
            self.identity_verified_by = actor
            automatic_fields.add("identity_verified_by")

        # -------------------------------------------------------------
        # STATUS TRANSITION DETECTION
        # -------------------------------------------------------------

        status_changed = (
            self._state.adding
            or previous_status != self.status
        )

        arrival_or_later_statuses = {
            self.EncounterStatus.ARRIVED,
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        }

        triage_or_later_statuses = {
            self.EncounterStatus.TRIAGED,
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        }

        clinical_or_later_statuses = {
            self.EncounterStatus.IN_PROGRESS,
            self.EncounterStatus.ON_HOLD,
            self.EncounterStatus.COMPLETED,
        }

        # -------------------------------------------------------------
        # ARRIVAL AUTOMATION
        # -------------------------------------------------------------

        if (
            self.status in arrival_or_later_statuses
            and not self.arrived_at
        ):
            self.arrived_at = current_time
            automatic_fields.add("arrived_at")

            if actor is not None and not self.check_in_user_id:
                self.check_in_user = actor
                automatic_fields.add("check_in_user")

        # -------------------------------------------------------------
        # TRIAGE AUTOMATION
        # -------------------------------------------------------------

        if (
            self.requires_triage
            and self.status in triage_or_later_statuses
            and not self.triaged_at
        ):
            self.triaged_at = current_time
            automatic_fields.add("triaged_at")

            if actor is not None and not self.triaged_by_id:
                self.triaged_by = actor
                automatic_fields.add("triaged_by")

        # -------------------------------------------------------------
        # CLINICAL START AUTOMATION
        # -------------------------------------------------------------

        if (
            self.status in clinical_or_later_statuses
            and not self.clinical_start_at
        ):
            self.clinical_start_at = current_time
            automatic_fields.add("clinical_start_at")

            if actor is not None and not self.clinical_started_by_id:
                self.clinical_started_by = actor
                automatic_fields.add("clinical_started_by")

        # -------------------------------------------------------------
        # COMPLETION AUTOMATION
        # -------------------------------------------------------------

        if self.status == self.EncounterStatus.COMPLETED:
            if not self.completed_at:
                self.completed_at = current_time
                automatic_fields.add("completed_at")

            if not self.end_datetime:
                self.end_datetime = self.completed_at
                automatic_fields.add("end_datetime")

            if (
                status_changed
                and actor is not None
                and not self.completed_by_id
            ):
                self.completed_by = actor
                automatic_fields.add("completed_by")

            self.is_active = False
            automatic_fields.add("is_active")

        # -------------------------------------------------------------
        # CANCELLATION AUTOMATION
        # -------------------------------------------------------------

        elif self.status == self.EncounterStatus.CANCELLED:
            if not self.cancelled_at:
                self.cancelled_at = current_time
                automatic_fields.add("cancelled_at")

            if (
                status_changed
                and actor is not None
                and not self.cancelled_by_id
            ):
                self.cancelled_by = actor
                automatic_fields.add("cancelled_by")

            self.is_active = False
            automatic_fields.add("is_active")

        # -------------------------------------------------------------
        # ENTERED-IN-ERROR AUTOMATION
        # -------------------------------------------------------------

        elif self.status == self.EncounterStatus.ENTERED_IN_ERROR:
            if not self.entered_in_error_at:
                self.entered_in_error_at = current_time
                automatic_fields.add("entered_in_error_at")

            if (
                status_changed
                and actor is not None
                and not self.entered_in_error_by_id
            ):
                self.entered_in_error_by = actor
                automatic_fields.add("entered_in_error_by")

            self.is_active = False
            automatic_fields.add("is_active")

        # -------------------------------------------------------------
        # OPEN ENCOUNTERS REMAIN ACTIVE
        # -------------------------------------------------------------

        else:
            if not self.is_active:
                self.is_active = True
                automatic_fields.add("is_active")

        # -------------------------------------------------------------
        # SUPPORT save(update_fields=...)
        # -------------------------------------------------------------

        self._add_update_fields(kwargs, automatic_fields)

        # -------------------------------------------------------------
        # VALIDATE AFTER AUTOMATIC FIELDS ARE POPULATED
        # -------------------------------------------------------------

        if validate:
            exclude = None

            if kwargs.get("update_fields"):
                update_fields = set(kwargs["update_fields"])
                all_fields = {
                    field.name
                    for field in self._meta.fields
                }
                exclude = list(all_fields - update_fields)

            self.full_clean(exclude=exclude)

        super().save(*args, **kwargs)

    # =================================================================
    # EXPLICIT WORKFLOW TRANSITION METHODS
    # =================================================================

    def complete_registration(self, user):
        """
        Mark registration as complete and automatically record the
        responsible user and timestamp.
        """

        self.registration_completed = True
        self.save(
            actor=user,
            update_fields={
                "registration_completed",
            },
        )

    def verify_identity(self, user):
        """
        Mark the patient's identity as verified.
        """

        self.identity_verified = True
        self.save(
            actor=user,
            update_fields={
                "identity_verified",
            },
        )

    def mark_arrived(self, user):
        """
        Mark the patient as arrived and checked in.
        """

        self.status = self.EncounterStatus.ARRIVED
        self.save(
            actor=user,
            update_fields={
                "status",
            },
        )

    def mark_triaged(self, user):
        """
        Mark triage as complete.

        Laboratory-only, imaging-only, and pharmacy-only encounters do
        not normally require this method.
        """

        if not self.requires_triage:
            raise ValidationError(
                {
                    "status": (
                        "This encounter type does not require formal triage."
                    )
                }
            )

        self.status = self.EncounterStatus.TRIAGED
        self.save(
            actor=user,
            update_fields={
                "status",
            },
        )

    def begin_clinical_care(self, user):
        """
        Begin direct clinical care.
        """

        self.status = self.EncounterStatus.IN_PROGRESS
        self.save(
            actor=user,
            update_fields={
                "status",
            },
        )

    def place_on_hold(self, user, reason=""):
        """
        Place an active encounter on hold.
        """

        self.status = self.EncounterStatus.ON_HOLD

        if reason:
            self.status_reason = reason

        self.save(
            actor=user,
            update_fields={
                "status",
                "status_reason",
            },
        )

    def resume_clinical_care(self, user):
        """
        Resume an encounter that was placed on hold.
        """

        self.status = self.EncounterStatus.IN_PROGRESS
        self.status_reason = ""

        self.save(
            actor=user,
            update_fields={
                "status",
                "status_reason",
            },
        )

    def complete(self, user):
        """
        Complete and close the encounter.
        """

        self.status = self.EncounterStatus.COMPLETED
        self.save(
            actor=user,
            update_fields={
                "status",
            },
        )

    def cancel(self, user, reason):
        """
        Cancel the encounter and record the reason.
        """

        if not reason or not reason.strip():
            raise ValidationError(
                {
                    "status_reason": (
                        "A cancellation reason is required."
                    )
                }
            )

        self.status = self.EncounterStatus.CANCELLED
        self.status_reason = reason.strip()

        self.save(
            actor=user,
            update_fields={
                "status",
                "status_reason",
            },
        )

    def mark_entered_in_error(self, user, reason):
        """
        Mark the encounter as entered in error.
        """

        if not reason or not reason.strip():
            raise ValidationError(
                {
                    "status_reason": (
                        "A reason is required when marking an encounter "
                        "as entered in error."
                    )
                }
            )

        self.status = self.EncounterStatus.ENTERED_IN_ERROR
        self.status_reason = reason.strip()

        self.save(
            actor=user,
            update_fields={
                "status",
                "status_reason",
            },
        )

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
        Return True when the patient has arrived and triage is required.
        """

        return (
            self.requires_triage
            and self.status == self.EncounterStatus.ARRIVED
            and self.arrived_at is not None
        )

    @property
    def is_ready_for_clinician(self):
        """
        Return True when the encounter may begin clinical care.
        """

        if not self.requires_triage:
            return (
                self.status == self.EncounterStatus.ARRIVED
                and self.arrived_at is not None
            )

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

        if self.identity_verified:
            return "Identity verified; registration incomplete"

        return "Registration incomplete"

    @property
    def duration(self):
        """
        Return the total administrative encounter duration.
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
        Return the time between arrival and direct clinical care.
        """

        if not self.arrived_at or not self.clinical_start_at:
            return None

        return self.clinical_start_at - self.arrived_at