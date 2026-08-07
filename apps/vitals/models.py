"""
Liberia EHR Vital Observation Models

File:
apps/vitals/models.py

Purpose:
- Store one set of patient vital-sign observations.
- Associate observations with a patient and optional encounter.
- Automatically record the staff member entering the observation.
- Calculate BMI, mean arterial pressure, and pulse pressure.
- Detect abnormal and critical vital-sign values.
- Preserve erroneous records for audit instead of deleting them.
"""

from __future__ import annotations

import uuid
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class VitalObservationQuerySet(models.QuerySet):
    def active(self):
        return self.exclude(
            status=VitalObservation.RecordStatus.ENTERED_IN_ERROR,
        )

    def entered_in_error(self):
        return self.filter(
            status=VitalObservation.RecordStatus.ENTERED_IN_ERROR,
        )

    def for_patient(self, patient):
        return self.filter(patient=patient)

    def for_encounter(self, encounter):
        return self.filter(encounter=encounter)

    def recent(self):
        return self.order_by("-recorded_at")


class VitalObservation(models.Model):
    """
    Represents one group of vital-sign measurements recorded at a
    particular date and time.

    Recorder information should be supplied by calling:

        observation.save(actor=request.user)
    """

    class RecordStatus(models.TextChoices):
        FINAL = "final", "Final"
        CORRECTED = "corrected", "Corrected"
        ENTERED_IN_ERROR = "entered_in_error", "Entered in error"

    class PatientPosition(models.TextChoices):
        SITTING = "sitting", "Sitting"
        STANDING = "standing", "Standing"
        SUPINE = "supine", "Supine"
        PRONE = "prone", "Prone"
        LATERAL = "lateral", "Lateral"
        OTHER = "other", "Other"
        NOT_RECORDED = "not_recorded", "Not recorded"

    class TemperatureSite(models.TextChoices):
        ORAL = "oral", "Oral"
        AXILLARY = "axillary", "Axillary"
        TYMPANIC = "tympanic", "Tympanic"
        TEMPORAL = "temporal", "Temporal"
        RECTAL = "rectal", "Rectal"
        SKIN = "skin", "Skin"
        OTHER = "other", "Other"
        NOT_RECORDED = "not_recorded", "Not recorded"

    class OxygenDeliveryMethod(models.TextChoices):
        ROOM_AIR = "room_air", "Room air"
        NASAL_CANNULA = "nasal_cannula", "Nasal cannula"
        SIMPLE_MASK = "simple_mask", "Simple face mask"
        VENTURI_MASK = "venturi_mask", "Venturi mask"
        NON_REBREATHER = "non_rebreather", "Non-rebreather mask"
        HIGH_FLOW = "high_flow", "High-flow nasal cannula"
        CPAP = "cpap", "CPAP"
        BIPAP = "bipap", "BiPAP"
        MECHANICAL_VENTILATION = (
            "mechanical_ventilation",
            "Mechanical ventilation",
        )
        OTHER = "other", "Other"
        NOT_RECORDED = "not_recorded", "Not recorded"

    class ClinicalStatus(models.TextChoices):
        NORMAL = "normal", "Normal"
        ABNORMAL = "abnormal", "Abnormal"
        CRITICAL = "critical", "Critical"
        NOT_ASSESSED = "not_assessed", "Not assessed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="vital_observations",
    )

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.PROTECT,
        related_name="vital_observations",
        null=True,
        blank=True,
    )

    recorded_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_vital_observations",
        editable=False,
    )

    position = models.CharField(
        max_length=20,
        choices=PatientPosition.choices,
        default=PatientPosition.NOT_RECORDED,
        blank=True,
    )

    temperature_celsius = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("25.0")),
            MaxValueValidator(Decimal("45.0")),
        ],
    )

    temperature_site = models.CharField(
        max_length=20,
        choices=TemperatureSite.choices,
        default=TemperatureSite.NOT_RECORDED,
        blank=True,
    )

    heart_rate = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(10),
            MaxValueValidator(300),
        ],
        help_text="Heart rate in beats per minute.",
    )

    respiratory_rate = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(100),
        ],
        help_text="Respiratory rate in breaths per minute.",
    )

    systolic_blood_pressure = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(30),
            MaxValueValidator(300),
        ],
    )

    diastolic_blood_pressure = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(10),
            MaxValueValidator(200),
        ],
    )

    oxygen_saturation = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("100.0")),
        ],
        help_text="Peripheral oxygen saturation percentage.",
    )

    oxygen_delivery_method = models.CharField(
        max_length=30,
        choices=OxygenDeliveryMethod.choices,
        default=OxygenDeliveryMethod.ROOM_AIR,
        blank=True,
    )

    oxygen_flow_lpm = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("100.0")),
        ],
        help_text="Supplemental oxygen flow in liters per minute.",
    )

    pain_score = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(10),
        ],
    )

    height_cm = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("20.0")),
            MaxValueValidator(Decimal("300.0")),
        ],
    )

    weight_kg = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.20")),
            MaxValueValidator(Decimal("1000.00")),
        ],
    )

    blood_glucose_mg_dl = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("1.0")),
            MaxValueValidator(Decimal("2000.0")),
        ],
    )

    notes = models.TextField(
        blank=True,
    )

    status = models.CharField(
        max_length=30,
        choices=RecordStatus.choices,
        default=RecordStatus.FINAL,
        db_index=True,
    )

    correction_reason = models.TextField(
        blank=True,
    )

    entered_in_error_reason = models.TextField(
        blank=True,
    )

    entered_in_error_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    entered_in_error_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="vitals_entered_in_error",
        null=True,
        blank=True,
        editable=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = VitalObservationQuerySet.as_manager()

    class Meta:
        ordering = (
            "-recorded_at",
            "-created_at",
        )
        verbose_name = "vital observation"
        verbose_name_plural = "vital observations"

        indexes = [
            models.Index(
                fields=("patient", "recorded_at"),
                name="vital_patient_date_idx",
            ),
            models.Index(
                fields=("encounter", "recorded_at"),
                name="vital_encounter_date_idx",
            ),
            models.Index(
                fields=("status", "recorded_at"),
                name="vital_status_date_idx",
            ),
            models.Index(
                fields=("recorded_by", "recorded_at"),
                name="vital_recorder_date_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(systolic_blood_pressure__isnull=True)
                    | Q(diastolic_blood_pressure__isnull=True)
                    | Q(
                        systolic_blood_pressure__gt=models.F(
                            "diastolic_blood_pressure"
                        )
                    )
                ),
                name="vital_systolic_gt_diastolic",
            ),
        ]

    def __str__(self):
        return (
            f"{self.patient} — "
            f"{timezone.localtime(self.recorded_at):%b %d, %Y %I:%M %p}"
        )

    def get_absolute_url(self):
        return reverse(
            "vitals:detail",
            kwargs={"pk": self.pk},
        )

    @property
    def bmi(self):
        if self.height_cm is None or self.weight_kg is None:
            return None

        height_m = self.height_cm / Decimal("100")

        if height_m <= 0:
            return None

        value = self.weight_kg / (height_m * height_m)

        return value.quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )

    @property
    def bmi_category(self):
        value = self.bmi

        if value is None:
            return ""

        if value < Decimal("18.5"):
            return "Underweight"

        if value < Decimal("25.0"):
            return "Healthy weight"

        if value < Decimal("30.0"):
            return "Overweight"

        return "Obesity"

    @property
    def mean_arterial_pressure(self):
        if (
            self.systolic_blood_pressure is None
            or self.diastolic_blood_pressure is None
        ):
            return None

        value = (
            Decimal(self.systolic_blood_pressure)
            + Decimal(2 * self.diastolic_blood_pressure)
        ) / Decimal("3")

        return value.quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        )

    @property
    def pulse_pressure(self):
        if (
            self.systolic_blood_pressure is None
            or self.diastolic_blood_pressure is None
        ):
            return None

        return (
            self.systolic_blood_pressure
            - self.diastolic_blood_pressure
        )

    @property
    def has_measurements(self):
        fields = (
            self.temperature_celsius,
            self.heart_rate,
            self.respiratory_rate,
            self.systolic_blood_pressure,
            self.diastolic_blood_pressure,
            self.oxygen_saturation,
            self.pain_score,
            self.height_cm,
            self.weight_kg,
            self.blood_glucose_mg_dl,
        )

        return any(value is not None for value in fields)

    @property
    def abnormal_findings(self):
        findings = []

        if self.temperature_celsius is not None:
            if self.temperature_celsius < Decimal("35.0"):
                findings.append(
                    {
                        "field": "temperature",
                        "label": "Low temperature",
                        "value": f"{self.temperature_celsius} °C",
                        "severity": "critical",
                    }
                )
            elif self.temperature_celsius >= Decimal("39.0"):
                findings.append(
                    {
                        "field": "temperature",
                        "label": "High temperature",
                        "value": f"{self.temperature_celsius} °C",
                        "severity": "critical",
                    }
                )
            elif self.temperature_celsius >= Decimal("37.5"):
                findings.append(
                    {
                        "field": "temperature",
                        "label": "Elevated temperature",
                        "value": f"{self.temperature_celsius} °C",
                        "severity": "abnormal",
                    }
                )

        if self.heart_rate is not None:
            if self.heart_rate < 40 or self.heart_rate > 140:
                findings.append(
                    {
                        "field": "heart_rate",
                        "label": "Critical heart rate",
                        "value": f"{self.heart_rate} bpm",
                        "severity": "critical",
                    }
                )
            elif self.heart_rate < 60 or self.heart_rate > 100:
                findings.append(
                    {
                        "field": "heart_rate",
                        "label": "Abnormal heart rate",
                        "value": f"{self.heart_rate} bpm",
                        "severity": "abnormal",
                    }
                )

        if self.respiratory_rate is not None:
            if self.respiratory_rate < 8 or self.respiratory_rate > 30:
                findings.append(
                    {
                        "field": "respiratory_rate",
                        "label": "Critical respiratory rate",
                        "value": f"{self.respiratory_rate}/min",
                        "severity": "critical",
                    }
                )
            elif (
                self.respiratory_rate < 12
                or self.respiratory_rate > 20
            ):
                findings.append(
                    {
                        "field": "respiratory_rate",
                        "label": "Abnormal respiratory rate",
                        "value": f"{self.respiratory_rate}/min",
                        "severity": "abnormal",
                    }
                )

        if (
            self.systolic_blood_pressure is not None
            and self.diastolic_blood_pressure is not None
        ):
            systolic = self.systolic_blood_pressure
            diastolic = self.diastolic_blood_pressure

            if systolic >= 180 or diastolic >= 120:
                findings.append(
                    {
                        "field": "blood_pressure",
                        "label": "Critical blood pressure",
                        "value": f"{systolic}/{diastolic} mmHg",
                        "severity": "critical",
                    }
                )
            elif systolic < 80 or diastolic < 50:
                findings.append(
                    {
                        "field": "blood_pressure",
                        "label": "Low blood pressure",
                        "value": f"{systolic}/{diastolic} mmHg",
                        "severity": "critical",
                    }
                )
            elif systolic >= 140 or diastolic >= 90:
                findings.append(
                    {
                        "field": "blood_pressure",
                        "label": "High blood pressure",
                        "value": f"{systolic}/{diastolic} mmHg",
                        "severity": "abnormal",
                    }
                )

        if self.oxygen_saturation is not None:
            if self.oxygen_saturation < Decimal("90.0"):
                findings.append(
                    {
                        "field": "oxygen_saturation",
                        "label": "Critical oxygen saturation",
                        "value": f"{self.oxygen_saturation}%",
                        "severity": "critical",
                    }
                )
            elif self.oxygen_saturation < Decimal("94.0"):
                findings.append(
                    {
                        "field": "oxygen_saturation",
                        "label": "Low oxygen saturation",
                        "value": f"{self.oxygen_saturation}%",
                        "severity": "abnormal",
                    }
                )

        if self.pain_score is not None:
            if self.pain_score >= 8:
                findings.append(
                    {
                        "field": "pain_score",
                        "label": "Severe pain",
                        "value": f"{self.pain_score}/10",
                        "severity": "critical",
                    }
                )
            elif self.pain_score >= 4:
                findings.append(
                    {
                        "field": "pain_score",
                        "label": "Moderate pain",
                        "value": f"{self.pain_score}/10",
                        "severity": "abnormal",
                    }
                )

        if self.blood_glucose_mg_dl is not None:
            if (
                self.blood_glucose_mg_dl < Decimal("54.0")
                or self.blood_glucose_mg_dl >= Decimal("400.0")
            ):
                findings.append(
                    {
                        "field": "blood_glucose",
                        "label": "Critical blood glucose",
                        "value": f"{self.blood_glucose_mg_dl} mg/dL",
                        "severity": "critical",
                    }
                )
            elif (
                self.blood_glucose_mg_dl < Decimal("70.0")
                or self.blood_glucose_mg_dl >= Decimal("200.0")
            ):
                findings.append(
                    {
                        "field": "blood_glucose",
                        "label": "Abnormal blood glucose",
                        "value": f"{self.blood_glucose_mg_dl} mg/dL",
                        "severity": "abnormal",
                    }
                )

        return findings

    @property
    def clinical_status(self):
        findings = self.abnormal_findings

        if not self.has_measurements:
            return self.ClinicalStatus.NOT_ASSESSED

        if any(item["severity"] == "critical" for item in findings):
            return self.ClinicalStatus.CRITICAL

        if findings:
            return self.ClinicalStatus.ABNORMAL

        return self.ClinicalStatus.NORMAL

    @property
    def clinical_status_display(self):
        return dict(self.ClinicalStatus.choices).get(
            self.clinical_status,
            "Not assessed",
        )

    @property
    def blood_pressure_display(self):
        if (
            self.systolic_blood_pressure is None
            or self.diastolic_blood_pressure is None
        ):
            return "Not recorded"

        return (
            f"{self.systolic_blood_pressure}/"
            f"{self.diastolic_blood_pressure} mmHg"
        )

    def clean(self):
        super().clean()

        errors = {}

        if self.encounter_id and self.patient_id:
            if self.encounter.patient_id != self.patient_id:
                errors["encounter"] = (
                    "The selected encounter does not belong to the "
                    "selected patient."
                )

        if (
            self.systolic_blood_pressure is None
            and self.diastolic_blood_pressure is not None
        ):
            errors["systolic_blood_pressure"] = (
                "Enter the systolic pressure when recording "
                "diastolic pressure."
            )

        if (
            self.systolic_blood_pressure is not None
            and self.diastolic_blood_pressure is None
        ):
            errors["diastolic_blood_pressure"] = (
                "Enter the diastolic pressure when recording "
                "systolic pressure."
            )

        if (
            self.systolic_blood_pressure is not None
            and self.diastolic_blood_pressure is not None
            and self.systolic_blood_pressure
            <= self.diastolic_blood_pressure
        ):
            errors["systolic_blood_pressure"] = (
                "Systolic pressure must be greater than "
                "diastolic pressure."
            )

        if (
            self.oxygen_delivery_method
            == self.OxygenDeliveryMethod.ROOM_AIR
            and self.oxygen_flow_lpm not in {
                None,
                Decimal("0"),
                Decimal("0.0"),
            }
        ):
            errors["oxygen_flow_lpm"] = (
                "Oxygen flow must be empty or zero when the patient "
                "is breathing room air."
            )

        if (
            self.recorded_at
            and self.recorded_at
            > timezone.now() + timezone.timedelta(minutes=5)
        ):
            errors["recorded_at"] = (
                "The vital-sign recording time cannot be in the future."
            )

        if (
            self.status == self.RecordStatus.CORRECTED
            and not self.correction_reason.strip()
        ):
            errors["correction_reason"] = (
                "Provide a reason for correcting this observation."
            )

        if (
            self.status == self.RecordStatus.ENTERED_IN_ERROR
            and not self.entered_in_error_reason.strip()
        ):
            errors["entered_in_error_reason"] = (
                "Provide a reason for marking this observation "
                "as entered in error."
            )

        if not self.has_measurements:
            errors["notes"] = (
                "Record at least one vital sign or clinical measurement."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, actor=None, validate=True, **kwargs):
        if self.encounter_id and not self.patient_id:
            self.patient_id = self.encounter.patient_id

        if self._state.adding and not self.recorded_by_id:
            if actor is None:
                raise ValidationError(
                    {
                        "recorded_by": (
                            "The authenticated user is required when "
                            "recording vital signs."
                        )
                    }
                )

            self.recorded_by = actor

        self.notes = (self.notes or "").strip()
        self.correction_reason = (
            self.correction_reason or ""
        ).strip()
        self.entered_in_error_reason = (
            self.entered_in_error_reason or ""
        ).strip()

        if validate:
            self.full_clean()

        return super().save(*args, **kwargs)

    def mark_entered_in_error(self, user, reason):
        reason = (reason or "").strip()

        if not reason:
            raise ValidationError(
                {
                    "entered_in_error_reason": (
                        "A reason is required when marking vital signs "
                        "as entered in error."
                    )
                }
            )

        self.status = self.RecordStatus.ENTERED_IN_ERROR
        self.entered_in_error_reason = reason
        self.entered_in_error_at = timezone.now()
        self.entered_in_error_by = user

        self.save(
            actor=user,
            update_fields={
                "status",
                "entered_in_error_reason",
                "entered_in_error_at",
                "entered_in_error_by",
                "updated_at",
            },
        )