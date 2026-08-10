from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class MedicationOrder(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        DISCONTINUED = "discontinued", "Discontinued"
        COMPLETED = "completed", "Completed"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )
    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )
    medication = models.ForeignKey(
        "pharmacy.Medication",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )
    dose = models.CharField(max_length=100)
    route = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )
    instructions = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-ordered_at",)
        indexes = [
            models.Index(
                fields=("encounter", "status"),
                name="order_med_enc_status_idx",
            ),
            models.Index(
                fields=("patient", "status"),
                name="order_med_patient_status_idx",
            ),
        ]

    def clean(self):
        if self.encounter_id and self.patient_id:
            if self.encounter.patient_id != self.patient_id:
                raise ValidationError(
                    {"encounter": "The encounter must belong to this patient."}
                )

    def __str__(self) -> str:
        return f"{self.medication.display_name} for {self.patient}"
