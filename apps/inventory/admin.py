from django.contrib import admin

from .models import (
    EquipmentAsset, InventoryItem, InventoryLocation, StockLot, StockTransaction, Supplier,
)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("sku", "name", "category", "tracking_mode", "reorder_level", "is_critical", "is_active")
    list_filter = ("category", "tracking_mode", "is_critical", "is_active")
    search_fields = ("sku", "name", "manufacturer")


@admin.register(StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ("item", "location", "lot_number", "expiration_date", "quantity_on_hand", "is_quarantined")
    list_filter = ("location", "is_quarantined", "expiration_date")
    search_fields = ("item__name", "item__sku", "lot_number")


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "item", "transaction_type", "quantity", "location", "recorded_by")
    list_filter = ("transaction_type", "location")
    search_fields = ("item__name", "item__sku", "reference", "reason")
    readonly_fields = ("balance_after",)


admin.site.register(InventoryLocation)
admin.site.register(Supplier)
admin.site.register(EquipmentAsset)
