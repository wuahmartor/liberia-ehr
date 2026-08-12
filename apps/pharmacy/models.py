from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

# ============================================================
# MEDICATION QUERYSET
# ============================================================


class MedicationQuerySet(models.QuerySet):
    """
    Query helpers for the local medication formulary.
    """

    def active(self):
        """
        Medications currently available for routine clinical selection.

        Restricted formulary items remain active because they may still
        legitimately appear in CPOE, medication reconciliation, and MAR.
        """
        return self.filter(
            is_active=True,
        ).exclude(
            formulary_status=Medication.FormularyStatus.RETIRED,
        )

    def retired(self):
        return self.filter(
            formulary_status=Medication.FormularyStatus.RETIRED,
        )

    def restricted(self):
        return self.filter(
            formulary_status=Medication.FormularyStatus.RESTRICTED,
            is_active=True,
        )

    def high_alert(self):
        return self.filter(
            is_high_alert=True,
            is_active=True,
        )

    def low_stock(self):
        return self.filter(
            quantity_on_hand__lte=models.F("reorder_level"),
            is_active=True,
        )

    def out_of_stock(self):
        return self.filter(
            quantity_on_hand__lte=0,
            is_active=True,
        )

    def search(self, query: str):
        """
        Search the local formulary.

        Includes common clinician-facing medication identifiers and
        descriptions.
        """
        query = " ".join((query or "").split()).strip()

        if not query:
            return self

        return self.filter(
            Q(code__icontains=query)
            | Q(rxnorm_rxcui__icontains=query)
            | Q(generic_name__icontains=query)
            | Q(brand_name__icontains=query)
            | Q(strength__icontains=query)
            | Q(dosage_form__icontains=query)
            | Q(route__icontains=query)
            | Q(therapeutic_class__icontains=query)
        )


# ============================================================
# MEDICATION
# ============================================================


class Medication(models.Model):
    """
    Local medication formulary record.

    This model represents a medication concept/product approved or
    recognized by the local EHR formulary.

    IMPORTANT:
    Inventory fields remain here temporarily for compatibility with the
    current Liberia EHR pharmacy implementation.

    Long term, stock quantities, batches, expiration dates, locations,
    receipts, transfers, and dispensing should be moved into dedicated
    inventory models.
    """

    # ========================================================
    # FORMULARY STATUS
    # ========================================================

    class FormularyStatus(models.TextChoices):
        FORMULARY = (
            "FORMULARY",
            "Formulary",
        )
        RESTRICTED = (
            "RESTRICTED",
            "Restricted",
        )
        NON_FORMULARY = (
            "NON_FORMULARY",
            "Non-formulary",
        )
        RETIRED = (
            "RETIRED",
            "Retired",
        )

    # ========================================================
    # TERMINOLOGY SOURCE
    # ========================================================

    class TerminologySource(models.TextChoices):
        LOCAL = (
            "LOCAL",
            "Local formulary",
        )
        RXNORM = (
            "RXNORM",
            "RxNorm",
        )
        OTHER = (
            "OTHER",
            "Other",
        )

    # ========================================================
    # IDENTIFICATION
    # ========================================================

    code = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=(
            "Stable local pharmacy/formulary identifier. "
            "This should not change when the display name changes."
        ),
    )

    terminology_source = models.CharField(
        max_length=20,
        choices=TerminologySource.choices,
        default=TerminologySource.LOCAL,
        db_index=True,
    )

    rxnorm_rxcui = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="RxNorm RxCUI",
        help_text=(
            "Optional RxNorm Concept Unique Identifier. "
            "RxNorm terminology does not imply local formulary approval."
        ),
    )

    # ========================================================
    # MEDICATION NAME
    # ========================================================

    generic_name = models.CharField(
        max_length=200,
        db_index=True,
    )

    brand_name = models.CharField(
        max_length=200,
        blank=True,
    )

    # ========================================================
    # PRODUCT DESCRIPTION
    # ========================================================

    strength = models.CharField(
        max_length=100,
        help_text=(
            "Medication strength, for example: 500 mg, 40 mg/mL, or 250 mg/5 mL."
        ),
    )

    dosage_form = models.CharField(
        max_length=100,
        help_text=(
            "Dosage form, for example: tablet, capsule, injection, "
            "oral solution, cream, or suppository."
        ),
    )

    route = models.CharField(
        max_length=100,
        help_text=(
            "Usual administration route, for example: oral, IV, IM, "
            "subcutaneous, topical, ophthalmic, or inhalation."
        ),
    )

    therapeutic_class = models.CharField(
        max_length=150,
        blank=True,
        help_text=("Optional therapeutic/pharmacologic classification."),
    )

    # ========================================================
    # FORMULARY GOVERNANCE
    # ========================================================

    formulary_status = models.CharField(
        max_length=20,
        choices=FormularyStatus.choices,
        default=FormularyStatus.FORMULARY,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Inactive medications remain available historically but should "
            "not normally appear in new medication-order selections."
        ),
    )

    requires_prescription = models.BooleanField(
        default=True,
    )

    # ========================================================
    # MEDICATION SAFETY
    # ========================================================

    is_controlled = models.BooleanField(
        default=False,
        help_text=(
            "Indicates that the medication is regulated as a controlled "
            "medicine under the applicable jurisdiction."
        ),
    )

    controlled_substance_class = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Optional jurisdiction-specific controlled medicine schedule "
            "or classification."
        ),
    )

    is_high_alert = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Flag medications requiring heightened safeguards because "
            "errors could cause serious harm."
        ),
    )

    is_lasa = models.BooleanField(
        default=False,
        verbose_name="Look-alike / sound-alike",
        help_text=(
            "Marks medications identified locally as look-alike or sound-alike."
        ),
    )

    safety_notes = models.TextField(
        blank=True,
        help_text=("Local formulary safety notes or medication handling warnings."),
    )

    # ========================================================
    # INVENTORY
    # ========================================================

    unit_of_measure = models.CharField(
        max_length=50,
        help_text=(
            "Current inventory unit, for example: tablet, capsule, vial, "
            "ampule, bottle, mL, or unit."
        ),
    )

    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
    )

    quantity_on_hand = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        help_text=(
            "Temporary aggregate inventory quantity. "
            "This will eventually move to pharmacy inventory records."
        ),
    )

    # ========================================================
    # RETIREMENT
    # ========================================================

    retired_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    retired_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="retired_pharmacy_medications",
    )

    retirement_reason = models.TextField(
        blank=True,
    )

    # ========================================================
    # AUDIT
    # ========================================================

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_pharmacy_medications",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_pharmacy_medications",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    objects = MedicationQuerySet.as_manager()

    # ========================================================
    # META
    # ========================================================

    class Meta:
        ordering = (
            "generic_name",
            "strength",
            "dosage_form",
            "code",
            "pk",
        )

        verbose_name = "Medication"
        verbose_name_plural = "Medications"

        indexes = [
            models.Index(
                fields=(
                    "is_active",
                    "formulary_status",
                    "generic_name",
                ),
                name="pharm_med_formulary_idx",
            ),
            models.Index(
                fields=(
                    "is_active",
                    "generic_name",
                    "code",
                ),
                name="pharm_med_active_name_idx",
            ),
            models.Index(
                fields=(
                    "is_active",
                    "quantity_on_hand",
                ),
                name="pharm_med_inventory_idx",
            ),
            models.Index(
                fields=(
                    "is_high_alert",
                    "is_active",
                ),
                name="pharm_med_highalert_idx",
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

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):
        super().clean()

        errors = {}

        self.code = (self.code or "").strip().upper()
        self.generic_name = " ".join((self.generic_name or "").split()).strip()

        self.brand_name = " ".join((self.brand_name or "").split()).strip()

        self.strength = " ".join((self.strength or "").split()).strip()

        self.dosage_form = " ".join((self.dosage_form or "").split()).strip()

        self.route = " ".join((self.route or "").split()).strip()

        self.rxnorm_rxcui = (self.rxnorm_rxcui or "").strip() or None

        # ----------------------------------------------------
        # RxNorm validation
        # ----------------------------------------------------

        if self.rxnorm_rxcui and not self.rxnorm_rxcui.isdigit():
            errors["rxnorm_rxcui"] = (
                "RxNorm RxCUI must contain only numeric characters."
            )

        if (
            self.terminology_source == self.TerminologySource.RXNORM
            and not self.rxnorm_rxcui
        ):
            errors["rxnorm_rxcui"] = (
                "An RxNorm RxCUI is required when RxNorm is selected "
                "as the terminology source."
            )

        # ----------------------------------------------------
        # Controlled medication validation
        # ----------------------------------------------------

        if not self.is_controlled:
            self.controlled_substance_class = ""

        # ----------------------------------------------------
        # Retirement validation
        # ----------------------------------------------------

        if self.formulary_status == self.FormularyStatus.RETIRED:
            self.is_active = False

        if self.is_active and self.formulary_status == self.FormularyStatus.RETIRED:
            errors["is_active"] = "A retired medication cannot remain active."

        if errors:
            raise ValidationError(errors)

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, *args, **kwargs):
        """
        Normalize stable text fields before persistence.

        full_clean() is intentionally not called automatically here because
        Django ModelForms already perform validation and bulk/internal
        processes may have their own validation workflow.
        """

        self.code = (self.code or "").strip().upper()

        self.generic_name = " ".join((self.generic_name or "").split()).strip()

        self.brand_name = " ".join((self.brand_name or "").split()).strip()

        self.strength = " ".join((self.strength or "").split()).strip()

        self.dosage_form = " ".join((self.dosage_form or "").split()).strip()

        self.route = " ".join((self.route or "").split()).strip()

        self.rxnorm_rxcui = (self.rxnorm_rxcui or "").strip() or None

        super().save(*args, **kwargs)

    # ========================================================
    # CLINICAL / FORMULARY HELPERS
    # ========================================================

    @property
    def display_name(self) -> str:
        """
        Human-readable medication description.
        """

        components = [self.generic_name]

        if self.brand_name:
            components.append(f"({self.brand_name})")

        if self.strength:
            components.append(self.strength)

        if self.dosage_form:
            components.append(self.dosage_form)

        return " ".join(component for component in components if component)

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_on_hand <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        return self.quantity_on_hand <= 0

    @property
    def is_retired(self) -> bool:
        return self.formulary_status == self.FormularyStatus.RETIRED

    def retire(
        self,
        *,
        user=None,
        reason: str = "",
    ) -> None:
        """
        Retire a formulary entry without destroying historical data.
        """

        self.formulary_status = self.FormularyStatus.RETIRED
        self.is_active = False
        self.retired_at = timezone.now()
        self.retired_by = user
        self.retirement_reason = (reason or "").strip()

        if user:
            self.updated_by = user

        self.save(
            update_fields=[
                "formulary_status",
                "is_active",
                "retired_at",
                "retired_by",
                "retirement_reason",
                "updated_by",
                "updated_at",
            ]
        )

    def reactivate(
        self,
        *,
        user=None,
    ) -> None:
        """
        Reactivate a previously retired medication.

        A pharmacist/formulary administrator should determine whether
        reactivation is clinically appropriate.
        """

        self.formulary_status = self.FormularyStatus.FORMULARY
        self.is_active = True

        self.retired_at = None
        self.retired_by = None
        self.retirement_reason = ""

        if user:
            self.updated_by = user

        self.save(
            update_fields=[
                "formulary_status",
                "is_active",
                "retired_at",
                "retired_by",
                "retirement_reason",
                "updated_by",
                "updated_at",
            ]
        )

    def __str__(self) -> str:
        return f"{self.display_name} [{self.code}]"


class PharmacyReview(models.Model):
    """Auditable pharmacist review of a medication order."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        VERIFIED = "verified", "Verified"
        CLARIFICATION = "clarification", "Clarification required"
        REJECTED = "rejected", "Rejected"

    order = models.OneToOneField(
        "orders.MedicationOrder",
        on_delete=models.PROTECT,
        related_name="pharmacy_review",
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    allergy_checked = models.BooleanField(default=False)
    dose_checked = models.BooleanField(default=False)
    route_frequency_checked = models.BooleanField(default=False)
    interactions_checked = models.BooleanField(default=False)
    formulary_checked = models.BooleanField(default=False)
    clinical_notes = models.TextField(blank=True)
    clarification_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="pharmacy_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    @property
    def is_verified(self):
        return self.status == self.Status.VERIFIED

    def __str__(self):
        return f"{self.order} — {self.get_status_display()}"


class DispenseRecord(models.Model):
    """Medication quantity supplied against a pharmacist-verified order."""

    order = models.ForeignKey(
        "orders.MedicationOrder",
        on_delete=models.PROTECT,
        related_name="dispense_records",
    )
    medication = models.ForeignKey(
        Medication, on_delete=models.PROTECT, related_name="dispense_records"
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = models.CharField(max_length=50)
    lot_number = models.CharField(max_length=100, blank=True)
    expiration_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    dispensed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pharmacy_dispenses",
    )
    dispensed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-dispensed_at",)

    def clean(self):
        super().clean()
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError(
                {"quantity": "Dispensed quantity must be greater than zero."}
            )
        if self.order_id and self.medication_id != self.order.medication_id:
            raise ValidationError({"medication": "Medication must match the order."})

    def __str__(self):
        return f"{self.medication.display_name} × {self.quantity}"


class InventoryTransaction(models.Model):
    """Immutable stock movement ledger for the aggregate formulary inventory."""

    class MovementType(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        ADJUSTMENT = "adjustment", "Adjustment"
        DISPENSE = "dispense", "Dispense"
        RETURN = "return", "Return"
        WASTE = "waste", "Waste"

    medication = models.ForeignKey(
        Medication, on_delete=models.PROTECT, related_name="inventory_transactions"
    )
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.DecimalField(max_digits=12, decimal_places=3)
    balance_after = models.DecimalField(max_digits=12, decimal_places=3)
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    dispense_record = models.OneToOneField(
        DispenseRecord,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="inventory_transaction",
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pharmacy_inventory_transactions",
    )
    recorded_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ("-recorded_at",)

    def __str__(self):
        return f"{self.medication.code}: {self.quantity_change:+}"
