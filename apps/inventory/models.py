from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q, Sum
from django.utils import timezone


class InventoryLocation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    facility = models.ForeignKey(
        "facilities.Facility", on_delete=models.PROTECT, related_name="inventory_locations"
    )
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=30)
    description = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("facility__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"), name="inventory_unique_location_code"
            )
        ]

    def __str__(self):
        return f"{self.name} · {self.facility}"


class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=180, unique=True)
    contact_name = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class InventoryItemQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def search(self, query):
        query = (query or "").strip()
        if not query:
            return self
        return self.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(manufacturer__icontains=query)
            | Q(description__icontains=query)
        )


class InventoryItem(models.Model):
    class Category(models.TextChoices):
        MEDICAL_SUPPLY = "medical_supply", "Medical supply"
        PPE = "ppe", "Personal protective equipment"
        SURGICAL = "surgical", "Surgical supply"
        LABORATORY = "laboratory", "Laboratory supply"
        MEDICATION_SUPPORT = "medication_support", "Medication support"
        MEDICAL_EQUIPMENT = "medical_equipment", "Medical equipment"
        OFFICE = "office", "Office and general supply"
        OTHER = "other", "Other"

    class TrackingMode(models.TextChoices):
        QUANTITY = "quantity", "Quantity"
        LOT_EXPIRY = "lot_expiry", "Lot and expiration"
        SERIALIZED = "serialized", "Serialized equipment"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=180, db_index=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, db_index=True)
    tracking_mode = models.CharField(
        max_length=20, choices=TrackingMode.choices, default=TrackingMode.LOT_EXPIRY
    )
    unit_of_measure = models.CharField(max_length=40, default="each")
    manufacturer = models.CharField(max_length=160, blank=True)
    manufacturer_part_number = models.CharField(max_length=80, blank=True)
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    target_stock_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    requires_expiration = models.BooleanField(default=False)
    is_critical = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="inventory_items_created",
    )

    objects = InventoryItemQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        indexes = [models.Index(fields=("category", "is_active"))]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def quantity_on_hand(self):
        return self.lots.aggregate(total=Sum("quantity_on_hand"))["total"] or 0

    @property
    def stock_status(self):
        quantity = self.quantity_on_hand
        if quantity <= 0:
            return "out"
        if quantity <= self.reorder_level:
            return "low"
        return "adequate"


class StockLot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="lots")
    location = models.ForeignKey(
        InventoryLocation, on_delete=models.PROTECT, related_name="stock_lots"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.SET_NULL, related_name="stock_lots", null=True, blank=True
    )
    lot_number = models.CharField(max_length=80, blank=True)
    expiration_date = models.DateField(null=True, blank=True, db_index=True)
    received_date = models.DateField(default=timezone.localdate)
    quantity_received = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_on_hand = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_quarantined = models.BooleanField(default=False, db_index=True)
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("expiration_date", "received_date")
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_received__gte=0), name="inventory_lot_received_nonnegative"
            ),
            models.CheckConstraint(
                condition=Q(quantity_on_hand__gte=0), name="inventory_lot_on_hand_nonnegative"
            ),
            models.UniqueConstraint(
                fields=("item", "location", "lot_number", "expiration_date"),
                name="inventory_unique_stock_lot",
            ),
        ]

    def clean(self):
        if self.item.requires_expiration and not self.expiration_date:
            raise ValidationError({"expiration_date": "This item requires an expiration date."})

    @property
    def expiry_status(self):
        if not self.expiration_date:
            return "not_applicable"
        days = (self.expiration_date - timezone.localdate()).days
        if days < 0:
            return "expired"
        if days <= 30:
            return "critical"
        if days <= 90:
            return "warning"
        return "current"

    def __str__(self):
        return f"{self.item.name} · {self.lot_number or 'No lot'}"


class EquipmentAsset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        IN_USE = "in_use", "In use"
        MAINTENANCE = "maintenance", "Under maintenance"
        OUT_OF_SERVICE = "out_of_service", "Out of service"
        RETIRED = "retired", "Retired"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="assets")
    location = models.ForeignKey(
        InventoryLocation, on_delete=models.PROTECT, related_name="equipment_assets"
    )
    asset_tag = models.CharField(max_length=60, unique=True, db_index=True)
    serial_number = models.CharField(max_length=100, blank=True, db_index=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.AVAILABLE)
    acquired_date = models.DateField(null=True, blank=True)
    warranty_expires = models.DateField(null=True, blank=True)
    next_maintenance_date = models.DateField(null=True, blank=True, db_index=True)
    last_maintenance_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("asset_tag",)

    def clean(self):
        if self.item.tracking_mode != InventoryItem.TrackingMode.SERIALIZED:
            raise ValidationError({"item": "Equipment assets require serialized tracking."})

    def __str__(self):
        return f"{self.asset_tag} · {self.item.name}"


class StockTransaction(models.Model):
    class Type(models.TextChoices):
        RECEIPT = "receipt", "Receipt"
        USAGE = "usage", "Clinical usage"
        TRANSFER_IN = "transfer_in", "Transfer in"
        TRANSFER_OUT = "transfer_out", "Transfer out"
        ADJUSTMENT_IN = "adjustment_in", "Positive adjustment"
        ADJUSTMENT_OUT = "adjustment_out", "Negative adjustment"
        EXPIRED = "expired", "Expired disposal"
        DAMAGED = "damaged", "Damaged disposal"
        RETURN = "return", "Return"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name="transactions"
    )
    lot = models.ForeignKey(
        StockLot, on_delete=models.PROTECT, related_name="transactions", null=True, blank=True
    )
    location = models.ForeignKey(
        InventoryLocation, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=25, choices=Type.choices, db_index=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, null=True, blank=True,
        related_name="inventory_usage_transactions"
    )
    encounter = models.ForeignKey(
        "encounters.Encounter", on_delete=models.PROTECT, null=True, blank=True,
        related_name="inventory_usage_transactions"
    )
    reference = models.CharField(max_length=100, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventory_transactions"
    )

    class Meta:
        ordering = ("-occurred_at",)
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="inventory_tx_quantity_positive")
        ]
        indexes = [models.Index(fields=("item", "transaction_type", "occurred_at"))]

    def clean(self):
        if self.transaction_type == self.Type.USAGE and not self.reason:
            raise ValidationError({"reason": "Document the clinical use or destination."})
        if self.lot_id and self.item_id != self.lot.item_id:
            raise ValidationError({"lot": "The selected lot does not belong to this item."})

    def __str__(self):
        return f"{self.get_transaction_type_display()} · {self.item} · {self.quantity}"
