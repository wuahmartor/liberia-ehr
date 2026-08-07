"""
============================================================
ADMINISTRATION MODELS

File:
apps/administration/models.py

Purpose:
- Store Administration-owned configuration and workflow data.
- Provide appointment scheduling within the Administration app.
============================================================
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class AppointmentQuerySet(models.QuerySet):
    """
    Query helpers for scheduled appointments.
    """

    def active(self):
        return self.filter(is_active=True)

    def upcoming(self):
        return self.active().filter(
            start_datetime__gte=timezone.now(),
        )

    def for_period(
        self,
        start_datetime,
        end_datetime,
    ):
        return self.filter(
            start_datetime__lt=end_datetime,
            end_datetime__gt=start_datetime,
        )

    def search(self, query):
        query = (query or "").strip()

        if not query:
            return self

        return self.filter(
            Q(appointment_number__icontains=query)
            | Q(patient__first_name__icontains=query)
            | Q(patient__middle_name__icontains=query)
            | Q(patient__last_name__icontains=query)
            | Q(reason_for_visit__icontains=query)
        )


class Appointment(models.Model):
    """
    Administrative appointment scheduling record.

    Scheduling is separate from a clinical encounter. An encounter may
    later be created from an appointment when the patient arrives.
    """

    class AppointmentType(models.TextChoices):
        NEW_PATIENT = "new_patient", "New Patient"
        FOLLOW_UP = "follow_up", "Follow-up"
        PROCEDURE = "procedure", "Procedure"
        LABORATORY = "laboratory", "Laboratory"
        IMAGING = "imaging", "Imaging"
        THERAPY = "therapy", "Therapy"
        TELEHEALTH = "telehealth", "Telehealth"
        HOME_VISIT = "home_visit", "Home Visit"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        SCHEDULED = "scheduled", "Scheduled"
        CONFIRMED = "confirmed", "Confirmed"
        CHECKED_IN = "checked_in", "Checked In"
        IN_PROGRESS = "in_progress", "In Progress"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No Show"
        CANCELLED = "cancelled", "Cancelled"
        ENTERED_IN_ERROR = "entered_in_error", "Entered in Error"

    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        URGENT = "urgent", "Urgent"
        EMERGENCY = "emergency", "Emergency"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    appointment_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True,
        db_index=True,
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    appointment_type = models.CharField(
        max_length=30,
        choices=AppointmentType.choices,
        default=AppointmentType.FOLLOW_UP,
        db_index=True,
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.ROUTINE,
        db_index=True,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    department = models.ForeignKey(

    "facilities.Department",

    on_delete=models.PROTECT,

    related_name="appointments",

    null=True,

    blank=True,
    )

    clinical_unit = models.ForeignKey(

    "facilities.ClinicalUnit",

    on_delete=models.PROTECT,

    related_name="appointments",

    null=True,

    blank=True,
    )

    room = models.ForeignKey(
        "facilities.Room",
        on_delete=models.PROTECT,
        related_name="appointments",
        null=True,
        blank=True,
    )

    provider = models.ForeignKey(

    settings.AUTH_USER_MODEL,

    on_delete=models.PROTECT,

    related_name="scheduled_appointments",

    null=True,

    blank=True,

)

    start_datetime = models.DateTimeField(
        db_index=True,
    )

    end_datetime = models.DateTimeField(
        db_index=True,
    )

    reason_for_visit = models.TextField()

    patient_instructions = models.TextField(
        blank=True,
    )

    internal_notes = models.TextField(
        blank=True,
    )

    cancellation_reason = models.TextField(
        blank=True,
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments_created",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments_updated",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        ordering = [
            "start_datetime",
            "appointment_number",
        ]

        indexes = [
            models.Index(
                fields=[
                    "facility",
                    "start_datetime",
                ],
                name="adm_appt_facility_start",
            ),
            models.Index(
                fields=[
                    "provider",
                    "start_datetime",
                ],
                name="adm_appt_provider_start",
            ),
            models.Index(
                fields=[
                    "status",
                    "start_datetime",
                ],
                name="adm_appt_status_start",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=Q(
                    end_datetime__gt=models.F(
                        "start_datetime",
                    ),
                ),
                name="adm_appt_end_after_start",
            ),
        ]

    def __str__(self):
        return (
            f"{self.appointment_number} - "
            f"{self.patient} - "
            f"{self.start_datetime:%Y-%m-%d %H:%M}"
        )

    def get_absolute_url(self):
        return reverse(
            "administration:scheduling_detail",
            kwargs={
                "appointment_id": self.pk,
            },
        )

    def save(self, *args, **kwargs):
        if not self.appointment_number:
            self.appointment_number = (
                self.generate_appointment_number()
            )

        super().save(*args, **kwargs)

    def generate_appointment_number(self):
        """
        Generate a readable appointment number.

        Example:
        APT-20260806-0001
        """

        today = timezone.localdate()
        prefix = today.strftime("APT-%Y%m%d")

        last_appointment = (
            Appointment.objects
            .filter(
                appointment_number__startswith=prefix,
            )
            .order_by("-appointment_number")
            .first()
        )

        sequence = 1

        if last_appointment:
            try:
                sequence = (
                    int(
                        last_appointment
                        .appointment_number
                        .rsplit("-", 1)[-1]
                    )
                    + 1
                )
            except (TypeError, ValueError):
                sequence = 1

        return f"{prefix}-{sequence:04d}"

    def clean(self):
        super().clean()

        errors = {}

        if (
            self.start_datetime
            and self.end_datetime
            and self.end_datetime
            <= self.start_datetime
        ):
            errors["end_datetime"] = (
                "The appointment end time must be after "
                "the start time."
            )

        if (
            self.department_id
            and self.facility_id
            and self.department.facility_id
            != self.facility_id
        ):
            errors["department"] = (
                "The selected department does not belong "
                "to the selected facility."
            )

        if (
            self.clinical_unit_id
            and self.facility_id
            and self.clinical_unit.facility_id
            != self.facility_id
        ):
            errors["clinical_unit"] = (
                "The selected clinical unit does not belong "
                "to the selected facility."
            )

        if (
            self.clinical_unit_id
            and self.department_id
            and self.clinical_unit.department_id
            != self.department_id
        ):
            errors["clinical_unit"] = (
                "The selected clinical unit does not belong "
                "to the selected department."
            )

        if (
            self.room_id
            and self.facility_id
            and self.room.facility_id
            != self.facility_id
        ):
            errors["room"] = (
                "The selected room does not belong to the "
                "selected facility."
            )

        if (
            self.start_datetime
            and self.end_datetime
            and self.status
            not in {
                self.Status.CANCELLED,
                self.Status.ENTERED_IN_ERROR,
            }
            and self.is_active
        ):
            conflict_query = Appointment.objects.filter(
                is_active=True,
                start_datetime__lt=self.end_datetime,
                end_datetime__gt=self.start_datetime,
            ).exclude(
                status__in=[
                    self.Status.CANCELLED,
                    self.Status.ENTERED_IN_ERROR,
                ],
            )

            if self.pk:
                conflict_query = conflict_query.exclude(
                    pk=self.pk,
                )

            if (
                self.provider_id
                and conflict_query.filter(
                    provider_id=self.provider_id,
                ).exists()
            ):
                errors["provider"] = (
                    "This provider already has another "
                    "appointment during the selected time."
                )

            if (
                self.room_id
                and conflict_query.filter(
                    room_id=self.room_id,
                ).exists()
            ):
                errors["room"] = (
                    "This room is already assigned to another "
                    "appointment during the selected time."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def duration_minutes(self):
        if not self.start_datetime or not self.end_datetime:
            return 0

        duration = (
            self.end_datetime
            - self.start_datetime
        )

        return max(
            int(duration.total_seconds() / 60),
            0,
        )

    @property
    def is_cancelled(self):
        return self.status == self.Status.CANCELLED

    @property
    def is_completed(self):
        return self.status == self.Status.COMPLETED

    @property
    def can_be_cancelled(self):
        return self.status not in {
            self.Status.COMPLETED,
            self.Status.CANCELLED,
            self.Status.ENTERED_IN_ERROR,
        }

    @property
    def can_be_restored(self):
        return self.status == self.Status.CANCELLED