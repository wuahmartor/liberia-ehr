from __future__ import annotations

from django.db import models
from django.db.models import Q


class MedicationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def search(self, query: str):
        query = (query or "").strip()
        if not query:
            return self

        return self.filter(
            Q(code__icontains=query)
            | Q(generic_name__icontains=query)
            | Q(brand_name__icontains=query)
            | Q(strength__icontains=query)
            | Q(dosage_form__icontains=query)
        )


class Medication(models.Model):
    """A formulary medication and its currently available pharmacy quantity."""

    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable pharmacy catalog code.",
    )
    rxnorm_rxcui = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        help_text="RxNorm concept identifier for US drug directory imports.",
    )
    generic_name = models.CharField(max_length=200)
    brand_name = models.CharField(max_length=200, blank=True)
    dosage_form = models.CharField(
        max_length=100,
        help_text="For example, tablet, capsule, injection, or suspension.",
    )
    strength = models.CharField(
        max_length=100,
        help_text="For example, 500 mg or 250 mg/5 mL.",
    )
    route = models.CharField(
        max_length=100,
        help_text="For example, oral, intravenous, or topical.",
    )
    unit_of_measure = models.CharField(
        max_length=50,
        help_text="Inventory unit, such as tablet, vial, or bottle.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    requires_prescription = models.BooleanField(default=True)
    is_controlled = models.BooleanField(default=False)
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    quantity_on_hand = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=0,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MedicationQuerySet.as_manager()

    class Meta:
        ordering = ("generic_name", "code", "pk")
        indexes = [
            models.Index(
                fields=("is_active", "generic_name", "code"),
                name="pharm_med_active_name_idx",
            ),
            models.Index(
                fields=("is_active", "quantity_on_hand"),
                name="pharm_med_inventory_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(reorder_level__gte=0),
                name="pharm_med_reorder_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0),
                name="pharm_med_quantity_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.code})"

    @property
    def display_name(self) -> str:
        name = self.generic_name
        if self.brand_name:
            name = f"{name} ({self.brand_name})"
        return f"{name} {self.strength} {self.dosage_form}"
