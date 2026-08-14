import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Conversation(models.Model):
    """A participant-restricted direct or broadcast staff conversation."""

    class Audience(models.TextChoices):
        SPECIFIC = "specific", "Specific staff"
        CARE_TEAM = "care_team", "Selected patients' care teams"
        ALL_STAFF = "all_staff", "All authorized staff"

    class ContextType(models.TextChoices):
        GENERAL = "general", "General / not patient-related"
        PATIENT = "patient", "Patient-related"

    class SubjectCategory(models.TextChoices):
        CHANGE_OF_CONDITION = "change_condition", "Change of condition"
        DIAGNOSTIC_RESULTS = "diagnostic_results", "Diagnostic results"
        NEW_ORDER = "new_order", "New order"
        MEDICATION_UPDATE = "medication_update", "Medication update"
        CARE_PLAN = "care_plan", "Care plan update"
        DISCHARGE_TRANSFER = "discharge_transfer", "Discharge or transfer"
        APPOINTMENT = "appointment", "Appointment or scheduling"
        SAFETY_CONCERN = "safety_concern", "Safety concern"
        OTHER = "other", "Other patient-related subject"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="staff_conversations",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_staff_conversations",
    )
    subject = models.CharField(max_length=200, default="Secure conversation")
    context_type = models.CharField(
        max_length=20,
        choices=ContextType.choices,
        default=ContextType.GENERAL,
        db_index=True,
    )
    subject_category = models.CharField(
        max_length=30,
        choices=SubjectCategory.choices,
        blank=True,
    )
    audience = models.CharField(
        max_length=20,
        choices=Audience.choices,
        default=Audience.SPECIFIC,
        db_index=True,
    )
    patients = models.ManyToManyField(
        "patients.Patient",
        related_name="staff_message_conversations",
        blank=True,
    )
    direct_key = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self):
        return f"Staff conversation {self.pk}"

    def other_participant(self, user):
        return self.participants.exclude(pk=user.pk).first()

    @property
    def is_broadcast(self):
        return self.audience != self.Audience.SPECIFIC or self.participants.count() > 2


class PatientCareTeamMember(models.Model):
    """Explicit patient-to-staff assignment used for care-team broadcasts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="messaging_care_team_memberships",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="messaging_care_team_assignments",
    )
    role_label = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_messaging_care_team_members",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("patient__last_name", "user__last_name")
        constraints = [
            models.UniqueConstraint(
                fields=("patient", "user"),
                name="unique_messaging_patient_care_team_member",
            )
        ]

    def __str__(self):
        return f"{self.user} — {self.patient}"


class Message(models.Model):
    """A participant-restricted staff message with per-user read receipts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_staff_messages",
    )
    body = models.TextField(max_length=4000)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="read_staff_messages",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("conversation", "created_at"))]

    def clean(self):
        super().clean()
        if self.conversation_id and self.sender_id:
            if not self.conversation.participants.filter(pk=self.sender_id).exists():
                raise ValidationError("The sender is not a conversation participant.")

    def __str__(self):
        return f"Message from {self.sender} at {self.created_at:%Y-%m-%d %H:%M}"
