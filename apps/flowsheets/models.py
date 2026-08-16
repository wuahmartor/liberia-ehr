from __future__ import annotations

import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class FlowSheetDefinition(models.Model):
    class Category(models.TextChoices):
        NURSING = "nursing", "Nursing assessment"
        INTAKE_OUTPUT = "intake_output", "Intake and output"
        NEUROLOGICAL = "neurological", "Neurological"
        RESPIRATORY = "respiratory", "Respiratory"
        CARDIOVASCULAR = "cardiovascular", "Cardiovascular"
        SAFETY = "safety", "Safety and mobility"
        CUSTOM = "custom", "Custom"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140, unique=True)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    is_system = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_flowsheet_definitions", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class FlowSheetFieldDefinition(models.Model):
    class DataType(models.TextChoices):
        NUMBER = "number", "Number"
        TEXT = "text", "Text"
        BOOLEAN = "boolean", "Yes / No"
        CHOICE = "choice", "Choice"
        MULTI_CHOICE = "multi_choice", "Multiple choice"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flowsheet = models.ForeignKey(FlowSheetDefinition, on_delete=models.CASCADE, related_name="fields")
    key = models.SlugField(max_length=80)
    label = models.CharField(max_length=120)
    data_type = models.CharField(max_length=20, choices=DataType.choices)
    unit = models.CharField(max_length=30, blank=True)
    choices = models.JSONField(default=list, blank=True)
    section = models.CharField(max_length=100, blank=True, default="General")
    subsection = models.CharField(max_length=100, blank=True)
    show_when_field_key = models.SlugField(max_length=80, blank=True)
    show_when_value = models.CharField(max_length=100, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_required = models.BooleanField(default=False)
    normal_min = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    normal_max = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    critical_min = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    critical_max = models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)
    help_text = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["display_order", "label"]
        constraints = [models.UniqueConstraint(fields=["flowsheet", "key"], name="unique_flowsheet_field_key")]

    def __str__(self):
        return f"{self.flowsheet.name}: {self.label}"

    def clean(self):
        super().clean()
        if self.data_type in (self.DataType.CHOICE, self.DataType.MULTI_CHOICE) and not self.choices:
            raise ValidationError({"choices": "Choice fields require at least one option."})
        if self.data_type not in (self.DataType.CHOICE, self.DataType.MULTI_CHOICE) and self.choices:
            raise ValidationError({"choices": "Only choice fields may define options."})
        if self.normal_min is not None and self.normal_max is not None and self.normal_min > self.normal_max:
            raise ValidationError("Normal minimum cannot exceed normal maximum.")
        if self.critical_min is not None and self.critical_max is not None and self.critical_min > self.critical_max:
            raise ValidationError("Critical minimum cannot exceed critical maximum.")
        if bool(self.show_when_field_key) != bool(self.show_when_value):
            raise ValidationError("Conditional fields require both a controlling field and value.")

    def classify_number(self, value: Decimal):
        if (self.critical_min is not None and value < self.critical_min) or (self.critical_max is not None and value > self.critical_max):
            return FlowSheetValue.Flag.CRITICAL
        if (self.normal_min is not None and value < self.normal_min) or (self.normal_max is not None and value > self.normal_max):
            return FlowSheetValue.Flag.WARNING
        return FlowSheetValue.Flag.NORMAL


class FlowSheetEntryQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(status=FlowSheetEntry.Status.ENTERED_IN_ERROR)


class FlowSheetEntry(models.Model):
    class AssessmentType(models.TextChoices):
        SHIFT = "shift", "Shift assessment"
        ADMISSION = "admission", "Admission assessment"
        FOCUSED = "focused", "Focused assessment"
        REASSESSMENT = "reassessment", "Reassessment"
        TRANSFER = "transfer", "Transfer assessment"
        DISCHARGE = "discharge", "Discharge assessment"

    class Status(models.TextChoices):
        FINAL = "final", "Final"
        CORRECTED = "corrected", "Corrected"
        ENTERED_IN_ERROR = "entered_in_error", "Entered in error"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="flowsheet_entries")
    encounter = models.ForeignKey("encounters.Encounter", on_delete=models.PROTECT, related_name="flowsheet_entries", null=True, blank=True)
    flowsheet = models.ForeignKey(FlowSheetDefinition, on_delete=models.PROTECT, related_name="entries")
    assessment_type = models.CharField(max_length=20, choices=AssessmentType.choices, default=AssessmentType.SHIFT, db_index=True)
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="recorded_flowsheet_entries")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FINAL, db_index=True)
    notes = models.TextField(blank=True)
    correction_reason = models.CharField(max_length=500, blank=True)
    corrected_from = models.ForeignKey("self", on_delete=models.PROTECT, related_name="corrections", null=True, blank=True)
    entered_in_error_at = models.DateTimeField(null=True, blank=True)
    entered_in_error_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="errored_flowsheet_entries", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = FlowSheetEntryQuerySet.as_manager()

    class Meta:
        ordering = ["-recorded_at", "-created_at"]
        indexes = [models.Index(fields=["patient", "recorded_at"]), models.Index(fields=["encounter", "recorded_at"])]

    def __str__(self):
        return f"{self.flowsheet.name} — {self.patient} — {self.recorded_at:%Y-%m-%d %H:%M}"

    def clean(self):
        super().clean()
        if self.encounter_id and self.patient_id and self.encounter.patient_id != self.patient_id:
            raise ValidationError({"encounter": "Encounter must belong to the selected patient."})
        if self.corrected_from_id and not self.correction_reason.strip():
            raise ValidationError({"correction_reason": "A correction reason is required."})

    def get_absolute_url(self):
        return reverse("flowsheets:detail", kwargs={"entry_id": self.pk})


class FlowSheetValue(models.Model):
    class Flag(models.TextChoices):
        NORMAL = "normal", "Normal"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"
        NOT_ASSESSED = "not_assessed", "Not assessed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entry = models.ForeignKey(FlowSheetEntry, on_delete=models.CASCADE, related_name="values")
    field = models.ForeignKey(FlowSheetFieldDefinition, on_delete=models.PROTECT, related_name="values")
    value_text = models.TextField(blank=True)
    value_number = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    value_boolean = models.BooleanField(null=True, blank=True)
    flag = models.CharField(max_length=20, choices=Flag.choices, default=Flag.NORMAL, db_index=True)

    class Meta:
        ordering = ["field__display_order", "field__label"]
        constraints = [
            models.UniqueConstraint(fields=["entry", "field"], name="unique_entry_field_value"),
            models.CheckConstraint(condition=Q(value_number__isnull=False) | ~Q(value_text="") | Q(value_boolean__isnull=False), name="flowsheet_value_not_empty"),
        ]

    @property
    def display_value(self):
        if self.value_number is not None:
            return f"{format(self.value_number.normalize(), 'f')} {self.field.unit}".strip()
        if self.value_boolean is not None:
            return "Yes" if self.value_boolean else "No"
        if self.field.data_type == FlowSheetFieldDefinition.DataType.MULTI_CHOICE:
            import json
            try:
                return ", ".join(json.loads(self.value_text))
            except (TypeError, ValueError):
                return self.value_text
        return self.value_text

    def __str__(self):
        return f"{self.field.label}: {self.display_value}"
