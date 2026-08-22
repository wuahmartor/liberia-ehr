from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.facilities.models import Facility

from ..models import InventoryItem, InventoryLocation, StockLot, StockTransaction
from ..services import record_stock_transaction


class InventoryWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("inventory-user", password="test-password")
        self.facility = Facility.objects.create(name="Test Hospital", code="TEST-HOSP")
        self.location = InventoryLocation.objects.create(
            facility=self.facility, name="Central Store", code="CENTRAL"
        )
        self.item = InventoryItem.objects.create(
            sku="PPE-001",
            name="Examination Gloves",
            category=InventoryItem.Category.PPE,
            tracking_mode=InventoryItem.TrackingMode.LOT_EXPIRY,
            unit_of_measure="box",
            reorder_level=Decimal("10"),
            target_stock_level=Decimal("50"),
            requires_expiration=True,
            created_by=self.user,
        )
        self.lot = StockLot.objects.create(
            item=self.item,
            location=self.location,
            lot_number="LOT-001",
            expiration_date=timezone.localdate() + timedelta(days=20),
            quantity_received=Decimal("20"),
            quantity_on_hand=Decimal("20"),
        )

    def test_usage_reduces_lot_balance_and_records_balance_after(self):
        movement = record_stock_transaction(
            actor=self.user,
            item=self.item,
            lot=self.lot,
            location=self.location,
            transaction_type=StockTransaction.Type.USAGE,
            quantity=Decimal("3"),
            patient=None,
            encounter=None,
            reference="",
            reason="Emergency department use",
        )
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantity_on_hand, Decimal("17"))
        self.assertEqual(movement.balance_after, Decimal("17"))

    def test_usage_cannot_make_stock_negative(self):
        with self.assertRaises(ValidationError):
            record_stock_transaction(
                actor=self.user,
                item=self.item,
                lot=self.lot,
                location=self.location,
                transaction_type=StockTransaction.Type.USAGE,
                quantity=Decimal("21"),
                patient=None,
                encounter=None,
                reference="",
                reason="Clinical use",
            )

    def test_expiry_status_flags_lot_within_thirty_days(self):
        self.assertEqual(self.lot.expiry_status, "critical")

    def test_inventory_dashboard_and_analytics_are_available(self):
        self.client.force_login(self.user)
        for route in ("inventory:dashboard", "inventory:item-list", "inventory:analytics"):
            response = self.client.get(reverse(route))
            self.assertEqual(response.status_code, 200)

