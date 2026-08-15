from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


class CareShift(models.Model):
    """A bounded staffing period used to group patient assignments."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="care_shifts",
        null=True,
        blank=True,
    )
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(db_index=True)
    notes = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_care_shifts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-starts_at", "name"]
        permissions = [("manage_staffing", "Can manage care staffing assignments")]
        indexes = [models.Index(fields=["starts_at", "ends_at"])]

    def __str__(self):
        return f"{self.name} ({self.starts_at:%b %d %H:%M}–{self.ends_at:%H:%M})"

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "Shift end must be after shift start."})

    @property
    def phase(self):
        now = timezone.now()
        if now < self.starts_at:
            return "upcoming"
        if now >= self.ends_at:
            return "ended"
        return "active"


class CareTeam(models.Model):
    """A shift-based team that can care for many patients."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(CareShift, on_delete=models.PROTECT, related_name="care_teams")
    name = models.CharField(max_length=120)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_care_teams"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["shift", "name"], name="unique_shift_care_team_name")]

    def __str__(self):
        return f"{self.name} — {self.shift.name}"


class CareTeamMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    care_team = models.ForeignKey(CareTeam, on_delete=models.CASCADE, related_name="memberships")
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="care_team_memberships")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="added_care_team_memberships")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["care_team", "staff"], name="unique_care_team_staff")]

    def clean(self):
        super().clean()
        from apps.accounts.models import UserProfile
        if not UserProfile.objects.filter(user_id=self.staff_id, is_active_staff=True, is_clinical_staff=True).exists():
            raise ValidationError({"staff": "Only active clinical staff can join a care team."})


class PatientCareTeamAssignment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RELEASED = "released", "Released"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    care_team = models.ForeignKey(CareTeam, on_delete=models.PROTECT, related_name="patient_assignments")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="care_team_assignments")
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="made_care_team_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["patient__last_name", "patient__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["patient"], condition=Q(status="active"), name="one_active_care_team_per_patient")
        ]


class PatientStaffAssignmentQuerySet(models.QuerySet):
    def assigned(self):
        return self.filter(status=PatientStaffAssignment.Status.ASSIGNED)

    def effective(self, at=None):
        """Remain effective until shift expiry and staff logout have both occurred."""
        at = at or timezone.now()
        return self.assigned().filter(
            Q(shift__ends_at__gt=at) | Q(staff_logged_out_at__isnull=True)
        )


class PatientStaffAssignment(models.Model):
    class AssignmentRole(models.TextChoices):
        NURSE = "nurse", "Nurse"
        PATIENT_CARE_AIDE = "patient_care_aide", "Patient Care Aide"

    class Status(models.TextChoices):
        ASSIGNED = "assigned", "Assigned"
        COMPLETED = "completed", "Completed"
        RELEASED = "released", "Released early"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    shift = models.ForeignKey(
        CareShift, on_delete=models.PROTECT, related_name="patient_assignments"
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="staff_assignments",
    )
    staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_shift_assignments",
    )
    assignment_role = models.CharField(max_length=30, choices=AssignmentRole.choices)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="made_patient_staff_assignments",
    )
    assigned_at = models.DateTimeField(auto_now_add=True, db_index=True)
    staff_logged_out_at = models.DateTimeField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ASSIGNED,
        db_index=True,
    )
    released_at = models.DateTimeField(null=True, blank=True)
    released_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="released_patient_staff_assignments",
        null=True,
        blank=True,
    )
    release_reason = models.CharField(max_length=300, blank=True)

    objects = PatientStaffAssignmentQuerySet.as_manager()

    class Meta:
        ordering = ["staff__last_name", "staff__first_name", "patient__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["shift", "patient", "staff"],
                condition=Q(status="assigned"),
                name="unique_active_shift_patient_staff",
            )
        ]
        indexes = [
            models.Index(fields=["shift", "status"]),
            models.Index(fields=["staff", "status"]),
            models.Index(fields=["patient", "status"]),
        ]

    def __str__(self):
        return f"{self.patient} → {self.staff} ({self.get_assignment_role_display()})"

    def clean(self):
        super().clean()
        from apps.accounts.models import UserProfile

        profile = UserProfile.objects.filter(user_id=self.staff_id).first()
        if (
            profile is None
            or not profile.is_active_staff
            or not profile.is_clinical_staff
            or profile.role not in {"nurse", "patient_care_aide"}
        ):
            raise ValidationError({"staff": "Select a nurse or patient care aide."})
        expected_role = (
            self.AssignmentRole.NURSE
            if profile.role == "nurse"
            else self.AssignmentRole.PATIENT_CARE_AIDE
        )
        if self.assignment_role != expected_role:
            raise ValidationError(
                {
                    "assignment_role": "Assignment role must match the staff profile role."
                }
            )

    @property
    def is_effective(self):
        return self.status == self.Status.ASSIGNED and not (
            self.shift.ends_at <= timezone.now()
            and self.staff_logged_out_at is not None
        )
