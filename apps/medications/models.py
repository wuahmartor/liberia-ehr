from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class MedicationAdministration(models.Model):
    class Status(models.TextChoices):
        ADMINISTERED = "administered", "Administered"
        HELD = "held", "Held"
        REFUSED = "refused", "Refused"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medication_administrations",
    )
    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.PROTECT,
        related_name="medication_administrations",
    )
    medication = models.ForeignKey(
        "pharmacy.Medication",
        on_delete=models.PROTECT,
        related_name="administrations",
    )
    dose_administered = models.CharField(max_length=100)
    route = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ADMINISTERED,
        db_index=True,
    )
    reason = models.TextField(blank=True)
    administered_at = models.DateTimeField()
    administered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medication_administrations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-administered_at",)
        indexes = [
            models.Index(
                fields=("encounter", "administered_at"),
                name="med_admin_enc_time_idx",
            ),
            models.Index(
                fields=("patient", "status"),
                name="med_admin_patient_status_idx",
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
