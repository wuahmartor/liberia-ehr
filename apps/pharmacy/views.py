from __future__ import annotations

import logging
from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import F, Q, QuerySet
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import (
    require_GET,
    require_POST,
)
from django.views.generic import (
    CreateView,
    DeleteView,
    ListView,
    UpdateView,
)

from apps.orders.models import MedicationOrder

from .forms import (
    DispenseForm,
    InventoryAdjustmentForm,
    MedicationForm,
    PharmacyReviewForm,
)
from .models import (
    DispenseRecord,
    InventoryTransaction,
    Medication,
    PharmacyReview,
)
from .rxnorm import (
    RxNormClient,
    RxNormUnavailable,
)

logger = logging.getLogger(__name__)

# ============================================================
# CONSTANTS
# ============================================================

MEDICATION_SEARCH_LIMIT = 50
RXNORM_SEARCH_MIN_LENGTH = 2
CATALOG_PAGE_SIZE = 25


# ============================================================
# SHARED CONTEXT
# ============================================================


def pharmacy_context(section: str) -> dict[str, Any]:
    """
    Shared navigation context for all pharmacy workspaces.
    """

    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "pharmacy",
        "active_clinical_section": section,
    }


# ============================================================
# PERMISSIONS
# ============================================================


def can_manage_medication_catalog(user) -> bool:
    """
    Temporary formulary-management permission.

    Replace later with the Liberia EHR role/permission system.

    Current policy:
    - superusers may manage the formulary
    - staff users may manage the formulary
    """

    return bool(user.is_authenticated and (user.is_superuser or user.is_staff))


class MedicationCatalogManagementMixin:
    """
    Restrict formulary create/update/delete operations to
    authorized staff.
    """

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_medication_catalog(request.user):
            raise PermissionDenied(
                "You do not have permission to modify the medication formulary."
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )


# ============================================================
# HTMX
# ============================================================


class HTMXTemplateMixin:
    """
    Return the medication-catalog workspace partial for HTMX
    requests and the full page for normal browser requests.
    """

    partial_template_name = "pharmacy/partials/medication_catalog_workspace.html"

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]

        return super().get_template_names()


# ============================================================
# QUERY HELPERS
# ============================================================


def medication_catalog_queryset() -> QuerySet[Medication]:
    """
    Base medication catalog queryset.

    This includes active, inactive, restricted, non-formulary,
    and retired records because the catalog is a management
    workspace rather than a prescribing search.
    """

    return Medication.objects.all().order_by(
        "generic_name",
        "strength",
        "dosage_form",
        "code",
        "pk",
    )


def low_stock_queryset() -> QuerySet[Medication]:
    """
    Return active medications at or below their configured
    reorder point.

    Inventory status does not determine whether a medication
    remains clinically valid for prescribing.
    """

    return (
        Medication.objects.active()
        .filter(quantity_on_hand__lte=F("reorder_level"))
        .order_by(
            "quantity_on_hand",
            "generic_name",
            "strength",
            "pk",
        )
    )


def pharmacy_order_queryset() -> QuerySet[MedicationOrder]:
    return MedicationOrder.objects.select_related(
        "patient", "encounter", "medication", "ordered_by", "pharmacy_review"
    ).prefetch_related("dispense_records")


def workflow_response(request, template_name, context):
    if request.headers.get("HX-Request") == "true":
        return render(request, "pharmacy/partials/workflow_table.html", context)
    return render(request, template_name, context)


# ============================================================
# PHARMACY DASHBOARD
# ============================================================


@login_required
def dashboard(
    request: HttpRequest,
) -> HttpResponse:
    """
    Pharmacy operational dashboard.

    Current implementation summarizes:
    - active formulary medications
    - low-stock medications

    Pharmacy verification and dispensing metrics should later
    come from dedicated pharmacy workflow models.
    """

    low_stock = low_stock_queryset()

    context = pharmacy_context("dashboard") | {
        "catalog_count": (Medication.objects.active().count()),
        "low_stock_count": (low_stock.count()),
        "low_stock_medications": (low_stock[:10]),
        "queue_count": pharmacy_order_queryset()
        .filter(
            status=MedicationOrder.Status.ACTIVE,
            pharmacy_review__isnull=True,
        )
        .count(),
        "review_count": pharmacy_order_queryset()
        .filter(
            status=MedicationOrder.Status.ACTIVE,
            pharmacy_review__status=PharmacyReview.Status.PENDING,
        )
        .count(),
        "verified_count": pharmacy_order_queryset()
        .filter(
            status=MedicationOrder.Status.ACTIVE,
            pharmacy_review__status=PharmacyReview.Status.VERIFIED,
        )
        .count(),
        "recent_dispenses": DispenseRecord.objects.select_related(
            "order__patient", "medication", "dispensed_by"
        )[:8],
    }

    return render(
        request,
        "pharmacy/dashboard.html",
        context,
    )


# ============================================================
# CLINICAL PHARMACY WORKSPACES
# ============================================================


@login_required
def queue(
    request: HttpRequest,
) -> HttpResponse:
    """
    Pharmacy work queue.

    Future implementation should display medication orders
    awaiting pharmacy processing.
    """

    query = request.GET.get("q", "").strip()
    orders = pharmacy_order_queryset().filter(status=MedicationOrder.Status.ACTIVE)
    if query:
        orders = orders.filter(
            Q(patient__first_name__icontains=query)
            | Q(patient__last_name__icontains=query)
            | Q(patient__mrn__icontains=query)
            | Q(medication__generic_name__icontains=query)
            | Q(clinical_indication__icontains=query)
        )
    context = pharmacy_context("queue") | {
        "orders": orders[:100],
        "workflow_kind": "queue",
        "query": query,
    }
    return workflow_response(request, "pharmacy/queue.html", context)


@login_required
def pending_review(
    request: HttpRequest,
) -> HttpResponse:
    """
    Medication orders requiring pharmacist clinical review.

    Future review should support:
    - allergies
    - duplicate therapy
    - dose appropriateness
    - route
    - frequency
    - indication
    - interactions
    - renal/hepatic considerations
    - required monitoring
    """

    orders = pharmacy_order_queryset().filter(
        Q(pharmacy_review__isnull=True)
        | Q(pharmacy_review__status=PharmacyReview.Status.PENDING),
        status=MedicationOrder.Status.ACTIVE,
    )
    context = pharmacy_context("pending-review") | {
        "orders": orders,
        "workflow_kind": "review",
    }
    return workflow_response(request, "pharmacy/pending_review.html", context)


@login_required
def verified(
    request: HttpRequest,
) -> HttpResponse:
    """
    Medication orders that have completed pharmacy review.
    """

    orders = pharmacy_order_queryset().filter(
        status=MedicationOrder.Status.ACTIVE,
        pharmacy_review__status=PharmacyReview.Status.VERIFIED,
    )
    context = pharmacy_context("verified") | {
        "orders": orders,
        "workflow_kind": "verified",
    }
    return workflow_response(request, "pharmacy/verified.html", context)


@login_required
def dispensing(
    request: HttpRequest,
) -> HttpResponse:
    """
    Medication dispensing workspace.

    Future implementation should operate on verified
    medication orders and produce auditable dispensing
    transactions.
    """

    orders = pharmacy_order_queryset().filter(
        status=MedicationOrder.Status.ACTIVE,
        pharmacy_review__status=PharmacyReview.Status.VERIFIED,
    )
    context = pharmacy_context("dispensing") | {
        "orders": orders,
        "workflow_kind": "dispensing",
        "recent_dispenses": DispenseRecord.objects.select_related(
            "order__patient", "medication", "dispensed_by"
        )[:25],
    }
    return workflow_response(request, "pharmacy/dispensing.html", context)


@login_required
def interactions(
    request: HttpRequest,
) -> HttpResponse:
    """
    Medication interaction review workspace.

    Interaction results should remain decision support,
    not autonomous prescribing decisions.
    """

    flagged_orders = (
        pharmacy_order_queryset()
        .filter(
            status=MedicationOrder.Status.ACTIVE,
        )
        .filter(
            Q(medication__is_high_alert=True)
            | Q(medication__is_lasa=True)
            | Q(medication__is_controlled=True)
        )
    )
    return render(
        request,
        "pharmacy/interactions.html",
        pharmacy_context("interactions") | {"orders": flagged_orders},
    )


@login_required
def rejected(
    request: HttpRequest,
) -> HttpResponse:
    """
    Pharmacy rejected / clarification-required orders.

    Future workflow should preserve:
    - rejection reason
    - pharmacist
    - timestamp
    - prescriber communication
    - resolution status
    """

    orders = pharmacy_order_queryset().filter(
        pharmacy_review__status__in=(
            PharmacyReview.Status.CLARIFICATION,
            PharmacyReview.Status.REJECTED,
        )
    )
    context = pharmacy_context("rejected") | {
        "orders": orders,
        "workflow_kind": "rejected",
    }
    return workflow_response(request, "pharmacy/rejected.html", context)


@login_required
def review_order(request: HttpRequest, order_id) -> HttpResponse:
    order = get_object_or_404(pharmacy_order_queryset(), pk=order_id)
    review, _ = PharmacyReview.objects.get_or_create(order=order)
    form = PharmacyReviewForm(request.POST or None, instance=review)
    if request.method == "POST" and form.is_valid():
        review = form.save(commit=False)
        review.reviewed_by = request.user
        review.reviewed_at = timezone.now()
        review.save()
        messages.success(
            request, f"Pharmacy review saved for {order.medication.display_name}."
        )
        if request.headers.get("HX-Request") == "true":
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse_lazy("pharmacy:pending-review")
            return response
        return redirect("pharmacy:pending-review")
    return render(
        request,
        "pharmacy/review_order.html",
        pharmacy_context("pending-review") | {"order": order, "form": form},
    )


@login_required
def dispense_order(request: HttpRequest, order_id) -> HttpResponse:
    order = get_object_or_404(pharmacy_order_queryset(), pk=order_id)
    review = getattr(order, "pharmacy_review", None)
    if not review or not review.is_verified:
        messages.error(
            request, "The medication order must be verified before dispensing."
        )
        return redirect("pharmacy:pending-review")

    form = DispenseForm(request.POST or None, initial={"quantity": order.quantity})
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            medication = Medication.objects.select_for_update().get(
                pk=order.medication_id
            )
            quantity = form.cleaned_data["quantity"]
            if quantity > medication.quantity_on_hand:
                form.add_error(
                    "quantity",
                    (
                        f"Only {medication.quantity_on_hand} "
                        f"{medication.unit_of_measure} available."
                    ),
                )
            else:
                dispense = form.save(commit=False)
                dispense.order = order
                dispense.medication = medication
                dispense.unit_of_measure = medication.unit_of_measure
                dispense.dispensed_by = request.user
                dispense.save()
                medication.quantity_on_hand -= quantity
                medication.updated_by = request.user
                medication.save(
                    update_fields=["quantity_on_hand", "updated_by", "updated_at"]
                )
                InventoryTransaction.objects.create(
                    medication=medication,
                    movement_type=InventoryTransaction.MovementType.DISPENSE,
                    quantity_change=-quantity,
                    balance_after=medication.quantity_on_hand,
                    reference=str(order.pk),
                    dispense_record=dispense,
                    recorded_by=request.user,
                )
                messages.success(request, "Medication dispensed and inventory updated.")
                return redirect("pharmacy:dispensing")

    return render(
        request,
        "pharmacy/dispense_order.html",
        pharmacy_context("dispensing") | {"order": order, "form": form},
    )


# ============================================================
# INVENTORY
# ============================================================


@login_required
def inventory(
    request: HttpRequest,
) -> HttpResponse:
    """
    Pharmacy inventory exception workspace.

    Inventory availability is operational information and
    should not determine whether a valid formulary medication
    can appear in clinical ordering searches.
    """

    adjustment_form = InventoryAdjustmentForm(request.POST or None)
    if request.method == "POST" and adjustment_form.is_valid():
        with transaction.atomic():
            medication = Medication.objects.select_for_update().get(
                pk=adjustment_form.cleaned_data["medication"].pk
            )
            change = adjustment_form.cleaned_data["quantity_change"]
            new_balance = medication.quantity_on_hand + change
            if new_balance < 0:
                adjustment_form.add_error(
                    "quantity_change", "This adjustment would make stock negative."
                )
            else:
                medication.quantity_on_hand = new_balance
                medication.updated_by = request.user
                medication.save(
                    update_fields=["quantity_on_hand", "updated_by", "updated_at"]
                )
                InventoryTransaction.objects.create(
                    medication=medication,
                    movement_type=(
                        InventoryTransaction.MovementType.RECEIPT
                        if change > 0
                        else InventoryTransaction.MovementType.ADJUSTMENT
                    ),
                    quantity_change=change,
                    balance_after=new_balance,
                    reference=adjustment_form.cleaned_data["reference"],
                    notes=adjustment_form.cleaned_data["notes"],
                    recorded_by=request.user,
                )
                messages.success(request, "Inventory balance updated.")
                return redirect("pharmacy:inventory")

    medications = low_stock_queryset()

    context = pharmacy_context("inventory") | {
        "medications": medications,
        "low_stock_count": (medications.count()),
        "adjustment_form": adjustment_form,
        "recent_transactions": InventoryTransaction.objects.select_related(
            "medication", "recorded_by"
        )[:30],
    }

    return render(
        request,
        "pharmacy/inventory.html",
        context,
    )


# ============================================================
# MEDICATION CATALOG
# ============================================================


class MedicationCatalogListView(
    LoginRequiredMixin,
    HTMXTemplateMixin,
    ListView,
):
    """
    Searchable medication formulary/catalog.

    This is pharmacy terminology/formulary management.
    It is not the patient medication-order workflow.
    """

    model = Medication
    context_object_name = "medications"
    template_name = "pharmacy/medication_catalog.html"
    paginate_by = CATALOG_PAGE_SIZE

    def get_queryset(
        self,
    ) -> QuerySet[Medication]:
        queryset = medication_catalog_queryset()

        query = self.request.GET.get("q", "").strip()

        status = self.request.GET.get("status", "all").strip().lower()

        if query:
            queryset = Medication.objects.search(query)

        if status == "active":
            queryset = queryset.filter(is_active=True)

        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        elif status == "formulary":
            queryset = queryset.filter(
                formulary_status=(Medication.FormularyStatus.FORMULARY)
            )

        elif status == "restricted":
            queryset = queryset.filter(
                formulary_status=(Medication.FormularyStatus.RESTRICTED)
            )

        elif status == "non-formulary":
            queryset = queryset.filter(
                formulary_status=(Medication.FormularyStatus.NON_FORMULARY)
            )

        elif status == "retired":
            queryset = queryset.filter(
                formulary_status=(Medication.FormularyStatus.RETIRED)
            )

        return queryset.order_by(
            "generic_name",
            "strength",
            "dosage_form",
            "code",
            "pk",
        )

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(
            {
                "form_mode": None,
                "search_query": (self.request.GET.get("q", "").strip()),
                "status_filter": (
                    self.request.GET.get(
                        "status",
                        "all",
                    )
                ),
                "can_manage_catalog": (
                    can_manage_medication_catalog(self.request.user)
                ),
            }
        )

        return context


class MedicationCatalogCreateView(
    LoginRequiredMixin,
    MedicationCatalogManagementMixin,
    HTMXTemplateMixin,
    CreateView,
):
    """
    Add a medication to the local formulary/catalog.
    """

    model = Medication
    form_class = MedicationForm

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(
            {
                "form_mode": "create",
                "medications": (medication_catalog_queryset()),
                "can_manage_catalog": True,
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        try:
            with transaction.atomic():
                response = super().form_valid(form)

        except IntegrityError:
            form.add_error(
                None,
                (
                    "This medication could not be created "
                    "because a conflicting formulary record "
                    "already exists."
                ),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (f"{self.object.display_name} was added to the medication formulary."),
        )

        return response


class MedicationCatalogUpdateView(
    LoginRequiredMixin,
    MedicationCatalogManagementMixin,
    HTMXTemplateMixin,
    UpdateView,
):
    """
    Update medication terminology and formulary information.
    """

    model = Medication
    form_class = MedicationForm

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(
            {
                "form_mode": "update",
                "medications": (medication_catalog_queryset()),
                "can_manage_catalog": True,
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        try:
            with transaction.atomic():
                response = super().form_valid(form)

        except IntegrityError:
            form.add_error(
                None,
                ("These changes conflict with an existing medication record."),
            )

            return self.form_invalid(form)

        messages.success(
            self.request,
            (f"{self.object.display_name} was updated."),
        )

        return response


class MedicationCatalogDeleteView(
    LoginRequiredMixin,
    MedicationCatalogManagementMixin,
    HTMXTemplateMixin,
    DeleteView,
):
    """
    Legacy medication catalog delete workflow.

    NOTE:
    The preferred production workflow is retirement rather
    than hard deletion, especially once a medication has been
    referenced by clinical records.
    """

    model = Medication

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(
        self,
        **kwargs,
    ):
        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(
            {
                "form_mode": "delete",
                "medications": (medication_catalog_queryset()),
                "can_manage_catalog": True,
            }
        )

        return context

    def form_valid(
        self,
        form,
    ):
        medication_name = self.object.display_name

        response = super().form_valid(form)

        messages.success(
            self.request,
            (f"{medication_name} was removed from the medication catalog."),
        )

        return response


medication_catalog = MedicationCatalogListView.as_view()


# ============================================================
# LOCAL MEDICATION SEARCH API
# ============================================================


@login_required
@require_GET
def medication_list_api(
    request: HttpRequest,
) -> JsonResponse:
    """
    Return active local medication concepts for clinical
    ordering/search.

    Used by:
    - CPOE medication ordering
    - medication reconciliation
    - other medication-selection workflows

    Inventory quantity is advisory only and must not determine
    clinical search eligibility.
    """

    query = request.GET.get("q", "").strip()

    medications = (
        Medication.objects.active()
        .search(query)
        .order_by(
            "generic_name",
            "strength",
            "dosage_form",
            "code",
            "pk",
        )[:MEDICATION_SEARCH_LIMIT]
    )

    results = []

    for medication in medications:
        quantity = medication.quantity_on_hand

        reorder_level = medication.reorder_level

        results.append(
            {
                "id": medication.pk,
                "code": medication.code,
                "display_name": (medication.display_name),
                "generic_name": (medication.generic_name),
                "brand_name": (medication.brand_name),
                "strength": (medication.strength),
                "dosage_form": (medication.dosage_form),
                "route": (medication.route),
                "unit_of_measure": (medication.unit_of_measure),
                "rxnorm_rxcui": (medication.rxnorm_rxcui),
                "formulary_status": (medication.formulary_status),
                "is_restricted": (
                    medication.formulary_status
                    == (Medication.FormularyStatus.RESTRICTED)
                ),
                "is_high_alert": (medication.is_high_alert),
                "is_lasa": (medication.is_lasa),
                "is_controlled": (medication.is_controlled),
                # Inventory is advisory metadata only.
                "available_quantity": (quantity),
                "reorder_level": (reorder_level),
                "low_stock": (
                    quantity is not None
                    and reorder_level is not None
                    and quantity <= reorder_level
                ),
            }
        )

    return JsonResponse(
        {
            "query": query,
            "count": len(results),
            "results": results,
        }
    )


# ============================================================
# RXNORM SEARCH API
# ============================================================


@login_required
@require_GET
def us_medication_search_api(
    request: HttpRequest,
) -> JsonResponse:
    """
    Search NIH/NLM RxNorm terminology without automatically
    adding results to the local formulary.

    RxNorm terminology does not imply:
    - local formulary approval
    - physical stock
    - clinical appropriateness
    - permission to prescribe
    """

    query = request.GET.get("q", "").strip()

    if len(query) < RXNORM_SEARCH_MIN_LENGTH:
        return JsonResponse(
            {
                "query": query,
                "count": 0,
                "results": [],
            }
        )

    try:
        rxnorm_results = RxNormClient().search(query)

    except RxNormUnavailable as error:
        logger.warning(
            ("RxNorm search unavailable for query %r: %s"),
            query,
            error,
        )

        return JsonResponse(
            {
                "detail": (
                    "The RxNorm medication terminology "
                    "service is temporarily unavailable."
                )
            },
            status=503,
        )

    except Exception:
        logger.exception(
            ("Unexpected error while searching RxNorm for %r."),
            query,
        )

        return JsonResponse(
            {"detail": ("The medication terminology search could not be completed.")},
            status=502,
        )

    {
        "rxcui": result.rxcui,
        "display_name": (result.display_name),
        "generic_name": (result.generic_name),
        "brand_name": (result.brand_name),
        "strength": (result.strength),
        "dosage_form": (result.dosage_form),
        "route": (result.route),
        "term_type": (result.term_type),
        "is_imported": (local_medication is not None),
        "local_medication_id": (local_medication.pk if local_medication else None),
        "local_is_active": (local_medication.is_active if local_medication else False),
        "local_formulary_status": (
            local_medication.formulary_status if local_medication else None
        ),
    }

    results = []

    for result in rxnorm_results:
        local_medication = local_medications.get(result.rxcui)

        results.append(
            {
                "rxcui": (result.rxcui),
                "display_name": (result.name),
                "term_type": (result.term_type),
                "is_imported": (local_medication is not None),
                "local_medication_id": (
                    local_medication.pk if local_medication else None
                ),
                "local_is_active": (
                    local_medication.is_active if local_medication else False
                ),
                "local_formulary_status": (
                    local_medication.formulary_status if local_medication else None
                ),
            }
        )

    return JsonResponse(
        {
            "query": query,
            "count": len(results),
            "results": results,
        }
    )


# ============================================================

# RXNORM SEARCH API

# ============================================================


@login_required
@require_GET
def us_medication_search_api(
    request: HttpRequest,
) -> JsonResponse:
    """

    Search NIH/NLM RxNorm terminology without automatically

    adding results to the local formulary.

    Search results include normalized:

    - generic name

    - strength

    - dosage form

    - route

    - RxCUI

    - term type

    RxNorm terminology does not imply:

    - local formulary approval

    - physical stock

    - clinical appropriateness

    - prescribing authorization

    """

    query = request.GET.get("q", "").strip()

    if len(query) < RXNORM_SEARCH_MIN_LENGTH:
        return JsonResponse(
            {
                "query": query,
                "count": 0,
                "results": [],
            }
        )

    # ========================================================

    # RXNORM SEARCH

    # ========================================================

    try:
        rxnorm_results = RxNormClient().search(query)

    except RxNormUnavailable as error:
        logger.warning(
            "RxNorm search unavailable for query %r: %s",
            query,
            error,
        )

        return JsonResponse(
            {
                "detail": (
                    "The RxNorm medication terminology "
                    "service is temporarily unavailable."
                )
            },
            status=503,
        )

    except Exception:
        logger.exception(
            "Unexpected error while searching RxNorm for %r.",
            query,
        )

        return JsonResponse(
            {"detail": ("The medication terminology search could not be completed.")},
            status=502,
        )

    # ========================================================

    # LOCAL MEDICATION MATCHES

    # ========================================================

    rxcuis = [result.rxcui for result in rxnorm_results if result.rxcui]

    local_medications = {
        medication.rxnorm_rxcui: medication
        for medication in (Medication.objects.filter(rxnorm_rxcui__in=rxcuis))
    }

    # ========================================================

    # RESPONSE RESULTS

    # ========================================================

    results = []

    for result in rxnorm_results:
        local_medication = local_medications.get(result.rxcui)

        results.append(
            {
                "rxcui": (result.rxcui),
                "display_name": (result.display_name),
                "generic_name": (result.generic_name),
                "brand_name": (result.brand_name),
                "strength": (result.strength),
                "dosage_form": (result.dosage_form),
                "route": (result.route),
                "term_type": (result.term_type),
                "is_imported": (local_medication is not None),
                "local_medication_id": (
                    local_medication.pk if local_medication else None
                ),
                "local_is_active": (
                    local_medication.is_active if local_medication else False
                ),
                "local_formulary_status": (
                    local_medication.formulary_status if local_medication else None
                ),
            }
        )

    return JsonResponse(
        {
            "query": query,
            "count": len(results),
            "results": results,
        }
    )


# ============================================================

# RXNORM ORDER-PICKER IMPORT API

# ============================================================


@login_required
@require_POST
def us_medication_import_api(
    request: HttpRequest,
) -> JsonResponse:
    """

    Import or reuse an RxNorm medication so it can be selected

    immediately by MedicationOrderForm.

    This endpoint is used specifically by the medication-order

    picker.

    Behavior:

    - receives an RxCUI

    - retrieves normalized RxNorm details

    - creates or updates a local pharmacy.Medication

    - preserves strength, dosage form, and route

    - keeps the record NON_FORMULARY

    - activates it so MedicationOrderForm can reference it

    - returns the local Medication primary key

    """

    # ========================================================

    # VALIDATE RXCUI

    # ========================================================

    rxcui = request.POST.get("rxcui", "").strip()

    if not rxcui:
        return JsonResponse(
            {
                "success": False,
                "error": "RxCUI is required.",
            },
            status=400,
        )

    if not rxcui.isdigit():
        return JsonResponse(
            {
                "success": False,
                "error": "Invalid RxCUI.",
            },
            status=400,
        )

    # ========================================================

    # RETRIEVE RXNORM CONCEPT

    # ========================================================

    try:
        rxnorm_medication = RxNormClient().get(rxcui)

    except RxNormUnavailable as error:
        logger.warning(
            "RxNorm concept %s unavailable: %s",
            rxcui,
            error,
        )

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The RxNorm medication terminology "
                    "service is temporarily unavailable."
                ),
            },
            status=503,
        )

    except Exception as error:
        logger.exception(
            "Unable to retrieve RxNorm concept %s.",
            rxcui,
        )

        return JsonResponse(
            {
                "success": False,
                "error": (
                    f"Unable to retrieve the selected RxNorm medication: {error}"
                ),
            },
            status=400,
        )

    # ========================================================

    # NORMALIZED VALUES

    # ========================================================

    rxnorm_rxcui = str(rxnorm_medication.rxcui).strip()

    generic_name = (
        getattr(
            rxnorm_medication,
            "generic_name",
            "",
        )
        or rxnorm_medication.name
        or "Unknown medication"
    )

    generic_name = " ".join(str(generic_name).split()).strip()

    brand_name = (
        getattr(
            rxnorm_medication,
            "brand_name",
            "",
        )
        or ""
    )

    brand_name = " ".join(str(brand_name).split()).strip()

    strength = (
        getattr(
            rxnorm_medication,
            "strength",
            "",
        )
        or "Unspecified"
    )

    strength = " ".join(str(strength).split()).strip()

    dosage_form = (
        getattr(
            rxnorm_medication,
            "dosage_form",
            "",
        )
        or "Unspecified"
    )

    dosage_form = " ".join(str(dosage_form).split()).strip()

    route = (
        getattr(
            rxnorm_medication,
            "route",
            "",
        )
        or "Unspecified"
    )

    route = " ".join(str(route).split()).strip()

    # ========================================================

    # CREATE OR UPDATE LOCAL MEDICATION

    # ========================================================

    try:
        with transaction.atomic():
            medication = Medication.objects.filter(rxnorm_rxcui=rxnorm_rxcui).first()

            created = False

            if medication is None:
                medication = Medication.objects.create(
                    code=(f"RXNORM-{rxnorm_rxcui}"),
                    terminology_source=(Medication.TerminologySource.RXNORM),
                    rxnorm_rxcui=(rxnorm_rxcui),
                    generic_name=(generic_name),
                    brand_name=(brand_name),
                    strength=(strength),
                    dosage_form=(dosage_form),
                    route=(route),
                    unit_of_measure="unit",
                    formulary_status=(Medication.FormularyStatus.NON_FORMULARY),
                    # Required for the MedicationOrderForm
                    # ModelChoiceField to accept the selected
                    # local Medication row.
                    is_active=True,
                    quantity_on_hand=0,
                    created_by=(request.user),
                    updated_by=(request.user),
                )

                created = True

            else:
                changed_fields = []

                if generic_name and medication.generic_name != generic_name:
                    medication.generic_name = generic_name

                    changed_fields.append("generic_name")

                if brand_name and medication.brand_name != brand_name:
                    medication.brand_name = brand_name

                    changed_fields.append("brand_name")

                if (
                    strength
                    and strength != "Unspecified"
                    and medication.strength != strength
                ):
                    medication.strength = strength

                    changed_fields.append("strength")

                if (
                    dosage_form
                    and dosage_form != "Unspecified"
                    and medication.dosage_form != dosage_form
                ):
                    medication.dosage_form = dosage_form

                    changed_fields.append("dosage_form")

                if route and route != "Unspecified" and medication.route != route:
                    medication.route = route

                    changed_fields.append("route")

                if not medication.is_active:
                    medication.is_active = True

                    changed_fields.append("is_active")

                if medication.formulary_status == (Medication.FormularyStatus.RETIRED):
                    medication.formulary_status = (
                        Medication.FormularyStatus.NON_FORMULARY
                    )

                    changed_fields.append("formulary_status")

                medication.updated_by = request.user

                changed_fields.append("updated_by")

                if changed_fields:
                    medication.save(update_fields=list(dict.fromkeys(changed_fields)))

    except IntegrityError:
        logger.exception(
            "Medication import conflict for RxCUI %s.",
            rxnorm_rxcui,
        )

        return JsonResponse(
            {
                "success": False,
                "error": (
                    "The medication could not be imported "
                    "because of a medication catalog conflict."
                ),
            },
            status=409,
        )

    # ========================================================

    # RESPONSE

    # ========================================================

    return JsonResponse(
        {
            "success": True,
            "created": created,
            "medication": {
                "id": (medication.pk),
                "code": (medication.code),
                "display_name": (medication.display_name),
                "generic_name": (medication.generic_name),
                "brand_name": (medication.brand_name),
                "strength": (medication.strength),
                "dosage_form": (medication.dosage_form),
                "route": (medication.route),
                "rxnorm_rxcui": (medication.rxnorm_rxcui),
                "formulary_status": (medication.formulary_status),
                "is_active": (medication.is_active),
                "available_quantity": (medication.quantity_on_hand),
                "low_stock": (medication.is_low_stock),
            },
        },
        status=(201 if created else 200),
    )


# ============================================================

# RXNORM FORMULARY-MANAGEMENT IMPORT

# ============================================================


@login_required
@require_POST
def import_us_medication(
    request: HttpRequest,
) -> JsonResponse:
    """

    Import an RxNorm concept into the medication catalog for

    pharmacy/formulary review.

    Unlike us_medication_import_api(), this endpoint does not

    automatically activate a new medication.

    Intended workflow:

    - Pharmacy staff imports RxNorm terminology.

    - Record remains NON_FORMULARY.

    - Record remains inactive.

    - Pharmacy later reviews and approves it.

    """

    if not can_manage_medication_catalog(request.user):
        return JsonResponse(
            {
                "detail": (
                    "You do not have permission "
                    "to add medications to the "
                    "local medication catalog."
                )
            },
            status=403,
        )

    # ========================================================

    # VALIDATE RXCUI

    # ========================================================

    rxcui = request.POST.get("rxcui", "").strip()

    if not rxcui or not rxcui.isdigit():
        return JsonResponse(
            {"detail": ("A valid numeric RxNorm concept identifier is required.")},
            status=400,
        )

    # ========================================================

    # EXISTING MEDICATION

    # ========================================================

    existing_medication = Medication.objects.filter(rxnorm_rxcui=rxcui).first()

    if existing_medication:
        return JsonResponse(
            {
                "id": (existing_medication.pk),
                "code": (existing_medication.code),
                "display_name": (existing_medication.display_name),
                "generic_name": (existing_medication.generic_name),
                "brand_name": (existing_medication.brand_name),
                "strength": (existing_medication.strength),
                "dosage_form": (existing_medication.dosage_form),
                "route": (existing_medication.route),
                "formulary_status": (existing_medication.formulary_status),
                "is_active": (existing_medication.is_active),
                "available_quantity": (existing_medication.quantity_on_hand),
                "already_imported": True,
                "requires_formulary_review": (not existing_medication.is_active),
            },
            status=200,
        )

    # ========================================================

    # FETCH RXNORM CONCEPT

    # ========================================================

    try:
        rxnorm_medication = RxNormClient().get(rxcui)

    except RxNormUnavailable as error:
        logger.warning(
            "RxNorm concept %s unavailable: %s",
            rxcui,
            error,
        )

        return JsonResponse(
            {
                "detail": (
                    "The RxNorm medication terminology "
                    "service is temporarily unavailable."
                )
            },
            status=503,
        )

    except Exception:
        logger.exception(
            "Unexpected error retrieving RxNorm concept %s.",
            rxcui,
        )

        return JsonResponse(
            {"detail": ("The selected medication concept could not be retrieved.")},
            status=502,
        )

    if not rxnorm_medication:
        raise Http404("The selected RxNorm medication concept was not found.")

    # ========================================================

    # NORMALIZED VALUES

    # ========================================================

    generic_name = rxnorm_medication.generic_name or rxnorm_medication.name

    strength = rxnorm_medication.strength or "Unspecified"

    dosage_form = rxnorm_medication.dosage_form or "Unspecified"

    route = rxnorm_medication.route or "Unspecified"

    # ========================================================

    # CREATE LOCAL TERMINOLOGY RECORD

    # ========================================================

    try:
        with transaction.atomic():
            medication, created = Medication.objects.get_or_create(
                rxnorm_rxcui=(rxnorm_medication.rxcui),
                defaults={
                    "code": (f"RXNORM-{rxnorm_medication.rxcui}"),
                    "terminology_source": (Medication.TerminologySource.RXNORM),
                    "generic_name": (generic_name),
                    "brand_name": (rxnorm_medication.brand_name or ""),
                    "strength": (strength),
                    "dosage_form": (dosage_form),
                    "route": (route),
                    "unit_of_measure": ("unit"),
                    "formulary_status": (Medication.FormularyStatus.NON_FORMULARY),
                    "is_active": False,
                    "quantity_on_hand": 0,
                    "created_by": (request.user),
                    "updated_by": (request.user),
                },
            )

    except IntegrityError:
        logger.exception(
            "Medication import conflict for RxCUI %s.",
            rxcui,
        )

        medication = Medication.objects.filter(rxnorm_rxcui=rxcui).first()

        if medication is None:
            return JsonResponse(
                {
                    "detail": (
                        "The medication could not be "
                        "imported because of a "
                        "catalog data conflict."
                    )
                },
                status=409,
            )

        created = False

    # ========================================================

    # RESPONSE

    # ========================================================

    return JsonResponse(
        {
            "id": (medication.pk),
            "code": (medication.code),
            "display_name": (medication.display_name),
            "generic_name": (medication.generic_name),
            "brand_name": (medication.brand_name),
            "strength": (medication.strength),
            "dosage_form": (medication.dosage_form),
            "route": (medication.route),
            "terminology_source": (medication.terminology_source),
            "formulary_status": (medication.formulary_status),
            "is_active": (medication.is_active),
            "available_quantity": (medication.quantity_on_hand),
            "already_imported": (not created),
            "requires_formulary_review": (not medication.is_active),
        },
        status=(201 if created else 200),
    )


# ============================================================
# RXNORM IMPORT
# ============================================================


@login_required
@require_POST
def import_us_medication(
    request: HttpRequest,
) -> JsonResponse:
    """
    Import an RxNorm concept into the local medication catalog.

    Imported terminology is intentionally created as:
    - RxNorm terminology source
    - NON_FORMULARY
    - inactive

    A separate local formulary review must occur before the
    medication becomes available for routine ordering.
    """

    if not can_manage_medication_catalog(request.user):
        return JsonResponse(
            {
                "detail": (
                    "You do not have permission "
                    "to add medications to the "
                    "local formulary."
                )
            },
            status=403,
        )

    rxcui = request.POST.get("rxcui", "").strip()

    if not rxcui or not rxcui.isdigit():
        return JsonResponse(
            {"detail": ("A valid numeric RxNorm concept identifier is required.")},
            status=400,
        )

    # --------------------------------------------------------
    # ALREADY IMPORTED
    # --------------------------------------------------------

    existing_medication = Medication.objects.filter(rxnorm_rxcui=rxcui).first()

    if existing_medication:
        return JsonResponse(
            {
                "id": (existing_medication.pk),
                "code": (existing_medication.code),
                "display_name": (existing_medication.display_name),
                "generic_name": (existing_medication.generic_name),
                "strength": (existing_medication.strength),
                "dosage_form": (existing_medication.dosage_form),
                "route": (existing_medication.route),
                "formulary_status": (existing_medication.formulary_status),
                "is_active": (existing_medication.is_active),
                "available_quantity": (existing_medication.quantity_on_hand),
                "already_imported": True,
                "requires_formulary_review": (not existing_medication.is_active),
            },
            status=200,
        )

    # --------------------------------------------------------
    # FETCH RXNORM CONCEPT
    # --------------------------------------------------------

    try:
        rxnorm_medication = RxNormClient().get(rxcui)

    except RxNormUnavailable as error:
        logger.warning(
            ("RxNorm concept %s unavailable: %s"),
            rxcui,
            error,
        )

        return JsonResponse(
            {
                "detail": (
                    "The RxNorm medication terminology "
                    "service is temporarily unavailable."
                )
            },
            status=503,
        )

    except Exception:
        logger.exception(
            ("Unexpected error retrieving RxNorm concept %s."),
            rxcui,
        )

        return JsonResponse(
            {"detail": ("The selected medication concept could not be retrieved.")},
            status=502,
        )

    if not rxnorm_medication:
        raise Http404(("The selected RxNorm medication concept was not found."))

    # --------------------------------------------------------
    # CREATE LOCAL TERMINOLOGY RECORD
    # --------------------------------------------------------

    try:
        with transaction.atomic():
            medication, created = Medication.objects.get_or_create(
                rxnorm_rxcui=(rxnorm_medication.rxcui),
                defaults={
                    "code": (f"RXNORM-{rxnorm_medication.rxcui}"),
                    "terminology_source": (Medication.TerminologySource.RXNORM),
                    "generic_name": (rxnorm_medication.name),
                    # RxNorm search results may not yet
                    # provide locally curated product data.
                    "strength": ("Unspecified"),
                    "dosage_form": ("Unspecified"),
                    "route": ("Unspecified"),
                    "unit_of_measure": ("unit"),
                    # External terminology import does
                    # not constitute local formulary
                    # approval.
                    "formulary_status": (Medication.FormularyStatus.NON_FORMULARY),
                    "is_active": False,
                    # Terminology import does not imply
                    # local stock.
                    "quantity_on_hand": 0,
                    "created_by": (request.user),
                    "updated_by": (request.user),
                },
            )

    except IntegrityError:
        logger.exception(
            ("Medication import conflict for RxCUI %s."),
            rxcui,
        )

        medication = Medication.objects.filter(rxnorm_rxcui=rxcui).first()

        if medication is None:
            return JsonResponse(
                {
                    "detail": (
                        "The medication could not be "
                        "imported because of a "
                        "formulary data conflict."
                    )
                },
                status=409,
            )

        created = False

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return JsonResponse(
        {
            "id": medication.pk,
            "code": medication.code,
            "display_name": (medication.display_name),
            "generic_name": (medication.generic_name),
            "strength": (medication.strength),
            "dosage_form": (medication.dosage_form),
            "route": medication.route,
            "terminology_source": (medication.terminology_source),
            "formulary_status": (medication.formulary_status),
            "is_active": (medication.is_active),
            "available_quantity": (medication.quantity_on_hand),
            "already_imported": (not created),
            "requires_formulary_review": (not medication.is_active),
        },
        status=(201 if created else 200),
    )
