from __future__ import annotations

import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone


class LabTestDefinition(models.Model):
    class ValueType(models.TextChoices):
        NUMERIC = "numeric", "Numeric"
        TEXT = "text", "Text"
        CODED = "coded", "Coded"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=60, unique=True)
    loinc_code = models.CharField(max_length=20, blank=True, db_index=True)
    name = models.CharField(max_length=160)
    short_name = models.CharField(max_length=60)
    specimen_type = models.CharField(max_length=80, default="Serum or plasma")
    value_type = models.CharField(max_length=20, choices=ValueType.choices, default=ValueType.NUMERIC)
    default_unit = models.CharField(max_length=30, blank=True)
    result_choices = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    class Meta: ordering = ("name",)
    def __str__(self): return self.name


class LabPanel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.SlugField(max_length=60, unique=True)
    loinc_code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=160)
    description = models.CharField(max_length=500, blank=True)
    tests = models.ManyToManyField(LabTestDefinition, through="LabPanelTest", related_name="panels")
    is_active = models.BooleanField(default=True, db_index=True)
    class Meta: ordering = ("name",)
    def __str__(self): return self.name


class LabPanelTest(models.Model):
    panel = models.ForeignKey(LabPanel, on_delete=models.CASCADE, related_name="panel_tests")
    test = models.ForeignKey(LabTestDefinition, on_delete=models.PROTECT)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_required = models.BooleanField(default=True)
    class Meta:
        ordering = ("display_order", "test__name")
        constraints = [models.UniqueConstraint(fields=("panel", "test"), name="unique_lab_panel_test")]


class LabReferenceRange(models.Model):
    class Sex(models.TextChoices):
        ANY = "any", "Any"
        FEMALE = "female", "Female"
        MALE = "male", "Male"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    test = models.ForeignKey(LabTestDefinition, on_delete=models.CASCADE, related_name="reference_ranges")
    label = models.CharField(max_length=120, default="Adult reference interval")
    sex = models.CharField(max_length=10, choices=Sex.choices, default=Sex.ANY)
    age_min_years = models.PositiveSmallIntegerField(default=18)
    age_max_years = models.PositiveSmallIntegerField(null=True, blank=True)
    lower_bound = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    upper_bound = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    critical_low = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    critical_high = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=30)
    source_title = models.CharField(max_length=250)
    source_url = models.URLField(max_length=500)
    source_version = models.CharField(max_length=80, blank=True)
    effective_date = models.DateField()
    is_locally_validated = models.BooleanField(default=False)
    validated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    validated_at = models.DateTimeField(null=True, blank=True)
    class Meta: ordering = ("test", "sex", "age_min_years")
    def clean(self):
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValidationError("Lower bound cannot exceed upper bound.")
        if self.is_locally_validated and not self.validated_by_id:
            raise ValidationError({"validated_by": "Local validation requires an accountable user."})
    @property
    def display_interval(self):
        return f"{self.lower_bound if self.lower_bound is not None else '—'}–{self.upper_bound if self.upper_bound is not None else '—'} {self.unit}"


class LabOrder(models.Model):
    class Status(models.TextChoices):
        ORDERED = "ordered", "Ordered"
        COLLECTED = "collected", "Collected"
        IN_PROCESS = "in_process", "In process"
        PARTIAL = "partial", "Partially resulted"
        FINAL = "final", "Final"
        CANCELLED = "cancelled", "Cancelled"
    class Priority(models.TextChoices):
        ROUTINE = "routine", "Routine"
        URGENT = "urgent", "Urgent"
        STAT = "stat", "STAT"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    accession_number = models.CharField(max_length=30, unique=True, blank=True, db_index=True)
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="lab_orders")
    encounter = models.ForeignKey("encounters.Encounter", on_delete=models.PROTECT, related_name="lab_orders")
    panel = models.ForeignKey(LabPanel, null=True, blank=True, on_delete=models.PROTECT, related_name="orders")
    indication_diagnosis = models.ForeignKey("diagnoses.PatientDiagnosis", null=True, blank=True, on_delete=models.PROTECT, related_name="lab_orders")
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.ROUTINE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ORDERED, db_index=True)
    clinical_indication = models.CharField(max_length=500)
    ordered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lab_orders")
    ordered_at = models.DateTimeField(default=timezone.now, db_index=True)
    class Meta: ordering = ("-ordered_at",)
    def save(self, *args, **kwargs):
        if not self.accession_number: self.accession_number = f"LAB-{timezone.now():%y%m%d}-{uuid.uuid4().hex[:6].upper()}"
        self.full_clean()
        return super().save(*args, **kwargs)
    def clean(self):
        if self.encounter_id and self.patient_id and self.encounter.patient_id != self.patient_id:
            raise ValidationError({"encounter": "Encounter must belong to the patient."})
        if self.indication_diagnosis_id and self.patient_id and self.indication_diagnosis.patient_id != self.patient_id:
            raise ValidationError({"indication_diagnosis": "Diagnosis must belong to the patient."})
    def get_absolute_url(self): return reverse("laboratories:order-detail", args=[self.pk])


class LabOrderItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name="items")
    test = models.ForeignKey(LabTestDefinition, on_delete=models.PROTECT)
    class Meta: constraints = [models.UniqueConstraint(fields=("order", "test"), name="unique_lab_order_test")]


class LabSpecimen(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending collection"
        COLLECTED = "collected", "Collected"
        RECEIVED = "received", "Received"
        REJECTED = "rejected", "Rejected"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(LabOrder, on_delete=models.PROTECT, related_name="specimens")
    specimen_type = models.CharField(max_length=80)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="collected_lab_specimens")
    received_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=300, blank=True)


class LabResult(models.Model):
    class Status(models.TextChoices):
        PRELIMINARY = "preliminary", "Preliminary"
        FINAL = "final", "Final"
        CORRECTED = "corrected", "Corrected"
        ENTERED_IN_ERROR = "entered_in_error", "Entered in error"
    class Flag(models.TextChoices):
        NORMAL = "normal", "Normal"
        LOW = "low", "Low"
        HIGH = "high", "High"
        CRITICAL_LOW = "critical_low", "Critical low"
        CRITICAL_HIGH = "critical_high", "Critical high"
        ABNORMAL = "abnormal", "Abnormal"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_item = models.OneToOneField(LabOrderItem, on_delete=models.PROTECT, related_name="result")
    numeric_value = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    text_value = models.CharField(max_length=500, blank=True)
    unit = models.CharField(max_length=30, blank=True)
    reference_range = models.ForeignKey(LabReferenceRange, null=True, blank=True, on_delete=models.PROTECT)
    reference_range_snapshot = models.JSONField(default=dict)
    flag = models.CharField(max_length=20, choices=Flag.choices, default=Flag.NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.FINAL)
    resulted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="lab_results")
    resulted_at = models.DateTimeField(default=timezone.now, db_index=True)
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="verified_lab_results")
    verified_at = models.DateTimeField(null=True, blank=True)
    critical_acknowledged_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="acknowledged_critical_lab_results")
    critical_acknowledged_at = models.DateTimeField(null=True, blank=True)
    critical_acknowledgment_note = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    def clean(self):
        if self.numeric_value is None and not self.text_value.strip(): raise ValidationError("A numeric or text result is required.")
    @property
    def display_value(self):
        return f"{self.numeric_value.normalize()} {self.unit}".strip() if self.numeric_value is not None else self.text_value


class LabClinicalRecommendation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(LabResult, on_delete=models.PROTECT, related_name="recommendations")
    title = models.CharField(max_length=200)
    recommendation = models.TextField()
    evidence_reference = models.CharField(max_length=500)
    rule_version = models.CharField(max_length=40, default="1.0")
    generated_by = models.CharField(max_length=80, default="Deterministic lab rule")
    requires_clinician_review = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ("-created_at",)
