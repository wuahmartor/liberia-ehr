from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import EquipmentAssetForm, InventoryItemForm, StockLotForm, StockTransactionForm
from .models import EquipmentAsset, InventoryItem, StockLot, StockTransaction
from .services import record_stock_transaction


def _navigation(module):
    return {
        "active_primary_nav": "inventory",
        "active_inventory_module": module,
    }


def _item_queryset():
    return InventoryItem.objects.annotate(
        on_hand=Coalesce(
            Sum("lots__quantity_on_hand"),
            Value(0),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )


@login_required
def dashboard(request):
    today = timezone.localdate()
    horizon = today + timedelta(days=90)
    items = _item_queryset().filter(is_active=True)
    low_stock = items.filter(on_hand__lte=F("reorder_level"))
    expiring = StockLot.objects.filter(
        quantity_on_hand__gt=0,
        expiration_date__range=(today, horizon),
    ).select_related("item", "location")
    expired = StockLot.objects.filter(
        quantity_on_hand__gt=0, expiration_date__lt=today
    ).select_related("item", "location")
    assets_due = EquipmentAsset.objects.filter(
        next_maintenance_date__lte=today + timedelta(days=30)
    ).exclude(status=EquipmentAsset.Status.RETIRED)
    recent_usage = StockTransaction.objects.filter(
        transaction_type=StockTransaction.Type.USAGE
    ).select_related("item", "location", "patient", "recorded_by")[:8]
    context = {
        **_navigation("dashboard"),
        "item_count": items.count(),
        "low_stock": low_stock[:8],
        "low_stock_count": low_stock.count(),
        "expiring": expiring[:8],
        "expiring_count": expiring.count(),
        "expired_count": expired.count(),
        "asset_count": EquipmentAsset.objects.exclude(status=EquipmentAsset.Status.RETIRED).count(),
        "maintenance_due_count": assets_due.count(),
        "recent_usage": recent_usage,
    }
    return render(request, "inventory/dashboard.html", context)


@login_required
def item_list(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    stock = request.GET.get("stock", "")
    items = _item_queryset().search(query)
    if category:
        items = items.filter(category=category)
    if stock == "low":
        items = items.filter(on_hand__lte=F("reorder_level"), on_hand__gt=0)
    elif stock == "out":
        items = items.filter(on_hand__lte=0)
    context = {
        **_navigation("items"),
        "items": items,
        "query": query,
        "selected_category": category,
        "selected_stock": stock,
        "categories": InventoryItem.Category.choices,
        "headings": ("Item", "Category", "Tracking", "On hand", "Reorder", "Status"),
    }
    return render(request, "inventory/item_list.html", context)


@login_required
def item_detail(request, item_id):
    item = get_object_or_404(_item_queryset(), pk=item_id)
    context = {
        **_navigation("items"),
        "item": item,
        "lots": item.lots.select_related("location", "supplier"),
        "assets": item.assets.select_related("location"),
        "transactions": item.transactions.select_related("location", "recorded_by")[:25],
    }
    return render(request, "inventory/item_detail.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def item_create(request):
    form = InventoryItemForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.created_by = request.user
        item.save()
        messages.success(request, f"{item.name} was added to the inventory catalog.")
        return redirect("inventory:item-detail", item_id=item.pk)
    return render(request, "inventory/form.html", {**_navigation("items"), "form": form, "title": "Add inventory item", "submit_label": "Save item"})


@login_required
@require_http_methods(["GET", "POST"])
def lot_create(request):
    initial = {"item": request.GET.get("item")}
    form = StockLotForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        lot = form.save(commit=False)
        lot.quantity_on_hand = lot.quantity_received
        lot.full_clean()
        lot.save()
        StockTransaction.objects.create(
            item=lot.item,
            lot=lot,
            location=lot.location,
            transaction_type=StockTransaction.Type.RECEIPT,
            quantity=lot.quantity_received,
            balance_after=lot.quantity_on_hand,
            reference="Initial receipt",
            reason="Stock lot received",
            recorded_by=request.user,
        )
        messages.success(request, f"Received {lot.quantity_received} {lot.item.unit_of_measure} of {lot.item.name}.")
        return redirect("inventory:item-detail", item_id=lot.item_id)
    return render(request, "inventory/form.html", {**_navigation("receiving"), "form": form, "title": "Receive stock", "submit_label": "Post receipt"})


@login_required
@require_http_methods(["GET", "POST"])
def transaction_create(request):
    initial = {"item": request.GET.get("item"), "lot": request.GET.get("lot")}
    form = StockTransactionForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        try:
            movement = record_stock_transaction(actor=request.user, **form.cleaned_data)
        except ValidationError as exc:
            for field, errors in exc.message_dict.items():
                for error in errors:
                    form.add_error(field if field in form.fields else None, error)
        else:
            messages.success(request, f"{movement.get_transaction_type_display()} posted successfully.")
            return redirect("inventory:item-detail", item_id=movement.item_id)
    return render(request, "inventory/form.html", {**_navigation("transactions"), "form": form, "title": "Record inventory movement", "submit_label": "Post transaction"})


@login_required
def transaction_list(request):
    transactions = StockTransaction.objects.select_related(
        "item", "lot", "location", "patient", "recorded_by"
    )
    transaction_type = request.GET.get("type", "")
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    return render(request, "inventory/transaction_list.html", {
        **_navigation("transactions"), "transactions": transactions[:250],
        "types": StockTransaction.Type.choices, "selected_type": transaction_type,
    })


@login_required
@require_http_methods(["GET", "POST"])
def equipment(request):
    form = EquipmentAssetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        asset = form.save()
        messages.success(request, f"Equipment asset {asset.asset_tag} was registered.")
        return redirect("inventory:equipment")
    assets = EquipmentAsset.objects.select_related("item", "location")
    return render(request, "inventory/equipment.html", {
        **_navigation("equipment"), "assets": assets, "form": form,
    })


@login_required
def analytics(request):
    today = timezone.localdate()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    usage = StockTransaction.objects.filter(
        transaction_type=StockTransaction.Type.USAGE,
        occurred_at__gte=thirty_days_ago,
    )
    top_usage = usage.values("item__name", "item__unit_of_measure").annotate(
        total=Sum("quantity"), events=Count("id")
    ).order_by("-total")[:10]
    usage_by_location = usage.values("location__name").annotate(
        total=Sum("quantity"), events=Count("id")
    ).order_by("-total")[:10]
    expiry_bands = {
        "expired": StockLot.objects.filter(quantity_on_hand__gt=0, expiration_date__lt=today).count(),
        "within_30": StockLot.objects.filter(quantity_on_hand__gt=0, expiration_date__range=(today, today + timedelta(days=30))).count(),
        "within_90": StockLot.objects.filter(quantity_on_hand__gt=0, expiration_date__range=(today + timedelta(days=31), today + timedelta(days=90))).count(),
    }
    return render(request, "inventory/analytics.html", {
        **_navigation("analytics"), "top_usage": top_usage,
        "usage_by_location": usage_by_location, "expiry_bands": expiry_bands,
        "usage_events": usage.count(), "usage_quantity": usage.aggregate(total=Sum("quantity"))["total"] or 0,
    })
