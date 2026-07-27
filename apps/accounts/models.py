from django.conf import settings
from django.db import models


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SYSTEM_ADMIN = "system_admin", "System Administrator"
        FACILITY_ADMIN = "facility_admin", "Facility Administrator"
        PHYSICIAN = "physician", "Physician"
        NURSE = "nurse", "Nurse"
        NURSE_PRACTITIONER = "nurse_practitioner", "Nurse Practitioner"
        PHARMACIST = "pharmacist", "Pharmacist"
        LAB_TECHNICIAN = "lab_technician", "Laboratory Technician"
        RADIOLOGY_TECHNICIAN = (
            "radiology_technician",
            "Radiology Technician",
        )
        DATA_ANALYST = "data_analyst", "Healthcare Data Analyst"
        INFORMATICIST = "informaticist", "Nursing Informaticist"
        BILLING_OFFICER = "billing_officer", "Billing Officer"
        RECEPTIONIST = "receptionist", "Receptionist"
        COMMUNITY_HEALTH_WORKER = (
            "community_health_worker",
            "Community Health Worker",
        )
        AUDITOR = "auditor", "Auditor"
        PATIENT = "patient", "Patient"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    role = models.CharField(
        max_length=40,
        choices=Role.choices,
        default=Role.NURSE,
        db_index=True,
    )

    employee_id = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
    )

    professional_license_number = models.CharField(
        max_length=100,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=30,
        blank=True,
    )

    job_title = models.CharField(
        max_length=150,
        blank=True,
    )

    department = models.CharField(
        max_length=150,
        blank=True,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff_profiles",
    )

    must_change_password = models.BooleanField(
        default=False,
        help_text="Require the user to change their password after login.",
    )

    is_clinical_staff = models.BooleanField(
        default=False,
        help_text="Identifies users who provide direct clinical care.",
    )

    is_active_staff = models.BooleanField(
        default=True,
        help_text="Controls whether the staff profile is active.",
    )

    last_activity = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["user__last_name", "user__first_name"]
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        indexes = [
            models.Index(fields=["role", "is_active_staff"]),
            models.Index(fields=["facility", "role"]),
        ]

    def __str__(self):
        full_name = self.user.get_full_name().strip()

        return (
            f"{full_name or self.user.username} "
            f"({self.get_role_display()})"
        )

    @property
    def display_name(self):
        return self.user.get_full_name().strip() or self.user.username

    @property
    def is_clinician(self):
        clinical_roles = {
            self.Role.PHYSICIAN,
            self.Role.NURSE,
            self.Role.NURSE_PRACTITIONER,
            self.Role.PHARMACIST,
            self.Role.LAB_TECHNICIAN,
            self.Role.RADIOLOGY_TECHNICIAN,
            self.Role.COMMUNITY_HEALTH_WORKER,
        }

        return self.role in clinical_roles

    @property
    def can_access_analytics(self):
        analytics_roles = {
            self.Role.SYSTEM_ADMIN,
            self.Role.FACILITY_ADMIN,
            self.Role.DATA_ANALYST,
            self.Role.INFORMATICIST,
            self.Role.PHYSICIAN,
            self.Role.NURSE_PRACTITIONER,
        }

        return self.role in analytics_roles