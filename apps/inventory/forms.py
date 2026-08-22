from django import forms

from .models import EquipmentAsset, InventoryItem, InventoryLocation, StockLot, StockTransaction


INPUT_CLASS = (
    "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm "
    "text-slate-900 shadow-sm focus:border-emerald-600 focus:ring-emerald-600"
)


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", INPUT_CLASS)


class InventoryItemForm(StyledModelForm):
    class Meta:
        model = InventoryItem
        exclude = ("created_by", "created_at", "updated_at")
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class InventoryLocationForm(StyledModelForm):
    class Meta:
        model = InventoryLocation
        fields = "__all__"


class StockLotForm(StyledModelForm):
    class Meta:
        model = StockLot
        fields = (
            "item", "location", "supplier", "lot_number", "expiration_date",
            "received_date", "quantity_received", "unit_cost", "is_quarantined", "notes",
        )
        widgets = {
            "expiration_date": forms.DateInput(attrs={"type": "date"}),
            "received_date": forms.DateInput(attrs={"type": "date"}),
        }


class StockTransactionForm(StyledModelForm):
    class Meta:
        model = StockTransaction
        fields = (
            "item", "lot", "location", "transaction_type", "quantity",
            "patient", "encounter", "reference", "reason",
        )

    def clean(self):
        cleaned = super().clean()
        lot = cleaned.get("lot")
        item = cleaned.get("item")
        location = cleaned.get("location")
        if lot and (lot.item_id != getattr(item, "pk", None) or lot.location_id != getattr(location, "pk", None)):
            raise forms.ValidationError("The lot must belong to the selected item and location.")
        return cleaned


class EquipmentAssetForm(StyledModelForm):
    class Meta:
        model = EquipmentAsset
        fields = "__all__"
        widgets = {
            "acquired_date": forms.DateInput(attrs={"type": "date"}),
            "warranty_expires": forms.DateInput(attrs={"type": "date"}),
            "next_maintenance_date": forms.DateInput(attrs={"type": "date"}),
            "last_maintenance_date": forms.DateInput(attrs={"type": "date"}),
        }

