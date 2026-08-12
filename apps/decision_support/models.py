import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class ClinicalRule(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", "Information"
        LOW = "low", "Low"
        MODERATE = "moderate", "Moderate"
        HIGH = "high", "High"
        CRITICAL = "critical", "Critical"

    code = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=180)
    version = models.PositiveIntegerField(default=1)
    description = models.TextField()
    trigger_definition = models.JSONField(default=dict, blank=True)
    recommendation = models.TextField()
    severity = models.CharField(max_length=20, choices=Severity.choices)
    evidence_reference = models.CharField(max_length=300, blank=True)
    owner = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True, db_index=True)
    effective_at = models.DateTimeField(default=timezone.now)
    review_due_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name", "-version")

    def __str__(self):
        return f"{self.name} v{self.version}"


class ClinicalAlert(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        OVERRIDDEN = "overridden", "Overridden"
        RESOLVED = "resolved", "Resolved"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(
        ClinicalRule, on_delete=models.PROTECT, related_name="alerts"
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="clinical_alerts"
    )
    encounter = models.ForeignKey(
        "encounters.Encounter",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="clinical_alerts",
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    supporting_data = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    triggered_at = models.DateTimeField(default=timezone.now, db_index=True)
    acted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="acted_clinical_alerts",
    )
    acted_at = models.DateTimeField(null=True, blank=True)
    action_note = models.TextField(blank=True)

    class Meta:
        ordering = ("status", "-triggered_at")

    def clean(self):
        super().clean()
        if self.encounter_id and self.encounter.patient_id != self.patient_id:
            raise ValidationError(
                {"encounter": "Encounter must belong to the patient."}
            )

    def __str__(self):
        return f"{self.title} — {self.patient}"


class RiskAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="risk_assessments"
    )
    encounter = models.ForeignKey(
        "encounters.Encounter", null=True, blank=True, on_delete=models.PROTECT
    )
    risk_type = models.CharField(max_length=100, db_index=True)
    score = models.DecimalField(max_digits=8, decimal_places=2)
    category = models.CharField(max_length=50)
    inputs = models.JSONField(default=dict)
    method = models.CharField(max_length=160, default="Deterministic clinical rule")
    method_version = models.CharField(max_length=40, default="1.0")
    calculated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )
    calculated_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-calculated_at",)
