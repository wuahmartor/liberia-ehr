from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from .models import StockLot, StockTransaction


INBOUND_TYPES = {
    StockTransaction.Type.RECEIPT,
    StockTransaction.Type.TRANSFER_IN,
    StockTransaction.Type.ADJUSTMENT_IN,
    StockTransaction.Type.RETURN,
}


@transaction.atomic
def record_stock_transaction(*, actor, **data):
    """Record an immutable movement and update its lot under a row lock."""
    quantity = Decimal(data["quantity"])
    transaction_type = data["transaction_type"]
    lot = data.get("lot")

    if not lot:
        raise ValidationError({"lot": "Select a stock lot for this movement."})

    locked_lot = StockLot.objects.select_for_update().get(pk=lot.pk)
    delta = quantity if transaction_type in INBOUND_TYPES else -quantity
    new_balance = locked_lot.quantity_on_hand + delta
    if new_balance < 0:
        raise ValidationError(
            {"quantity": f"Only {locked_lot.quantity_on_hand} units are available in this lot."}
        )

    movement = StockTransaction(recorded_by=actor, balance_after=new_balance, **data)
    movement.full_clean()
    movement.save()
    StockLot.objects.filter(pk=locked_lot.pk).update(quantity_on_hand=F("quantity_on_hand") + delta)
    return movement

