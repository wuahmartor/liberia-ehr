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

from django.shortcuts import redirect, render

from django.urls import reverse, reverse_lazy

from django.views.decorators.http import require_GET, require_POST

from django.views.generic import (

    CreateView,

    DeleteView,

    ListView,

    UpdateView,

)

from .forms import MedicationForm

from .models import Medication

from .rxnorm import RxNormClient, RxNormUnavailable

logger = logging.getLogger(__name__)



# ============================================================
# PERMISSIONS
# ============================================================


def can_manage_medication_catalog(user) -> bool:
    """
    Temporary formulary-management permission.

    Replace later with the Liberia EHR role/permission system.
    """
    return bool(
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
        )
    )


class MedicationCatalogManagementMixin:
    """
    Restrict medication formulary changes to authorized staff.
    """

    def dispatch(self, request, *args, **kwargs):
        if not can_manage_medication_catalog(request.user):
            raise PermissionDenied(
                "You do not have permission to modify the medication formulary."
            )

        return super().dispatch(request, *args, **kwargs)


# ============================================================
# HTMX
# ============================================================


class HTMXTemplateMixin:
    """
    Return only the medication workspace during HTMX requests.

    Normal browser requests receive the complete page.
    """

    partial_template_name = (
        "pharmacy/partials/medication_catalog_workspace.html"
    )

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]

        return super().get_template_names()


class HTMXTemplateMixin:
    """
    Return only the pharmacy workspace for HTMX requests.
    """

    partial_template_name = (
        "pharmacy/partials/medication_catalog_workspace.html"
    )

    def get_template_names(self):
        if self.request.headers.get("HX-Request") == "true":
            return [self.partial_template_name]

        return super().get_template_names()

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

    Determine whether the current user may modify the local medication

    formulary/catalog.

    For now:

    - superusers are allowed

    - staff users are allowed

    This function gives us one place to replace this later with your

    Liberia EHR role/permission system.

    """

    return bool(

        user.is_authenticated

        and (

            user.is_superuser

            or user.is_staff

        )

    )

class MedicationCatalogListView(
    LoginRequiredMixin,
    HTMXTemplateMixin,
    ListView,
):

    """

    Restrict medication catalog create/update/delete operations.

    Reading the formulary should generally be available to authenticated

    clinical staff, while changes to the formulary should be controlled.

    """

    def dispatch(self, request, *args, **kwargs):

        if not can_manage_medication_catalog(request.user):

            raise PermissionDenied(

                "You do not have permission to modify the medication formulary."

            )

        return super().dispatch(request, *args, **kwargs)

# ============================================================

# QUERY HELPERS

# ============================================================

def medication_catalog_queryset() -> QuerySet[Medication]:

    """

    Base queryset used throughout pharmacy views.

    Centralizing this prevents slightly different formulary behavior

    across the application.

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

    Return medications at or below their configured reorder point.

    Inventory status is deliberately separate from formulary activity:

    a medication may remain clinically valid even when local stock is zero.

    """

    return (

        Medication.objects.filter(

            quantity_on_hand__lte=F("reorder_level"),

        )

        .order_by(

            "quantity_on_hand",

            "generic_name",

            "strength",

            "pk",

        )

    )

# ============================================================

# PHARMACY DASHBOARD

# ============================================================

@login_required

def dashboard(request: HttpRequest) -> HttpResponse:

    """

    Pharmacy operational dashboard.

    At this stage this summarizes the medication catalog and local stock.

    Prescription verification and dispensing metrics should come from

    dedicated medication-order / pharmacy-workflow models once connected.

    """

    low_stock = low_stock_queryset()

    context = pharmacy_context("dashboard") | {

        "catalog_count": Medication.objects.active().count(),

        "low_stock_count": low_stock.count(),

        "low_stock_medications": low_stock[:10],

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

def queue(request: HttpRequest) -> HttpResponse:

    """

    Pharmacy work queue.

    IMPORTANT:

    This should eventually display medication orders/prescriptions awaiting

    pharmacy processing rather than Medication catalog records.

    """

    return render(

        request,

        "pharmacy/queue.html",

        pharmacy_context("queue"),

    )

@login_required

def pending_review(request: HttpRequest) -> HttpResponse:

    """

    Orders requiring pharmacist clinical review.

    Future workflow should evaluate:

    - patient identity

    - allergies

    - duplicate therapies

    - interactions

    - renal/hepatic considerations

    - indication

    - dose

    - route

    - frequency

    - duration

    - pregnancy/lactation considerations where applicable

    - required monitoring

    """

    return render(

        request,

        "pharmacy/pending_review.html",

        pharmacy_context("pending-review"),

    )

@login_required

def verified(request: HttpRequest) -> HttpResponse:

    """

    Medication orders that have completed pharmacy verification.

    """

    return render(

        request,

        "pharmacy/verified.html",

        pharmacy_context("verified"),

    )

@login_required

def dispensing(request: HttpRequest) -> HttpResponse:

    """

    Medication dispensing workspace.

    This should ultimately operate on verified medication orders and create

    auditable dispensing transactions.

    """

    return render(

        request,

        "pharmacy/dispensing.html",

        pharmacy_context("dispensing"),

    )

@login_required

def interactions(request: HttpRequest) -> HttpResponse:

    """

    Medication interaction review workspace.

    Interaction results should be treated as decision support rather than

    an autonomous prescribing decision.

    """

    return render(

        request,

        "pharmacy/interactions.html",

        pharmacy_context("interactions"),

    )

@login_required

def rejected(request: HttpRequest) -> HttpResponse:

    """

    Pharmacy rejected / returned-for-clarification medication orders.

    Eventually this should preserve:

    - rejection reason

    - pharmacist

    - timestamp

    - communication to prescriber

    - resolution status

    """

    return render(

        request,

        "pharmacy/rejected.html",

        pharmacy_context("rejected"),

    )

# ============================================================

# INVENTORY

# ============================================================

@login_required

def inventory(request: HttpRequest) -> HttpResponse:

    """

    Pharmacy inventory exception view.

    The clinical formulary and the inventory ledger should remain separate

    concepts. This page therefore concentrates on stock exceptions rather

    than determining whether medications may be prescribed.

    """

    medications = low_stock_queryset()

    context = pharmacy_context("inventory") | {

        "medications": medications,

        "low_stock_count": medications.count(),

    }

    return render(

        request,

        "pharmacy/inventory.html",

        context,

    )

# ============================================================

# MEDICATION CATALOG

# ============================================================

class MedicationCatalogListView(LoginRequiredMixin, ListView):

    """

    Searchable medication formulary/catalog.

    This is terminology/formulary management and should not be confused

    with medication orders for individual patients.

    """

    model = Medication

    context_object_name = "medications"

    template_name = "pharmacy/medication_catalog.html"

    paginate_by = CATALOG_PAGE_SIZE

    def get_queryset(self) -> QuerySet[Medication]:

        queryset = medication_catalog_queryset()

        query = self.request.GET.get("q", "").strip()

        status = self.request.GET.get("status", "all").strip().lower()

        if query:

            # Prefer the model manager's search implementation when possible.

            try:

                queryset = Medication.objects.search(query)

            except AttributeError:

                queryset = queryset.filter(

                    Q(generic_name__icontains=query)

                    | Q(code__icontains=query)

                    | Q(strength__icontains=query)

                    | Q(dosage_form__icontains=query)

                    | Q(route__icontains=query)

                    | Q(rxnorm_rxcui__icontains=query)

                )

        if status == "active":

            queryset = queryset.filter(is_active=True)

        elif status == "inactive":

            queryset = queryset.filter(is_active=False)

        return queryset.order_by(

            "generic_name",

            "strength",

            "dosage_form",

            "code",

            "pk",

        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(

            {

                "form_mode": None,

                "search_query": self.request.GET.get("q", "").strip(),

                "status_filter": self.request.GET.get("status", "all"),

                "can_manage_catalog": can_manage_medication_catalog(

                    self.request.user

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

    Add a medication concept to the local formulary.

    """

    model = Medication

    form_class = MedicationForm

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(

            {

                "form_mode": "create",

                "medications": medication_catalog_queryset(),

                "can_manage_catalog": True,

            }

        )

        return context

    def form_valid(self, form):

        try:

            with transaction.atomic():

                response = super().form_valid(form)

        except IntegrityError:

            form.add_error(

                None,

                (

                    "This medication could not be created because a "

                    "conflicting formulary record already exists."

                ),

            )

            return self.form_invalid(form)

        messages.success(

            self.request,

            f"{self.object.display_name} was added to the medication formulary.",

        )

        return response

class MedicationCatalogUpdateView(
    LoginRequiredMixin,
    MedicationCatalogManagementMixin,
    HTMXTemplateMixin,
    UpdateView,
):

    """

    Update medication terminology/formulary information.

    Existing clinical medication orders should retain their historical

    values rather than being retroactively changed by catalog edits.

    """

    model = Medication

    form_class = MedicationForm

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(

            {

                "form_mode": "update",

                "medications": medication_catalog_queryset(),

                "can_manage_catalog": True,

            }

        )

        return context

    def form_valid(self, form):

        try:

            with transaction.atomic():

                response = super().form_valid(form)

        except IntegrityError:

            form.add_error(

                None,

                (

                    "These changes conflict with an existing medication "

                    "record."

                ),

            )

            return self.form_invalid(form)

        messages.success(

            self.request,

            f"{self.object.display_name} was updated.",

        )

        return response

class MedicationCatalogDeleteView(
    LoginRequiredMixin,
    MedicationCatalogManagementMixin,
    HTMXTemplateMixin,
    DeleteView,
    ):

    """

    Medication catalog removal.

    IMPORTANT:

    For a production EHR, hard deletion of medications that have ever been

    referenced in clinical records should normally be prohibited.

    The preferred workflow is to deactivate/retire the formulary entry.

    """

    model = Medication

    template_name = "pharmacy/medication_catalog.html"

    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update(pharmacy_context("medication-catalog"))

        context.update(

            {

                "form_mode": "delete",

                "medications": medication_catalog_queryset(),

                "can_manage_catalog": True,

            }

        )

        return context

    def form_valid(self, form):

        medication_name = self.object.display_name

        response = super().form_valid(form)

        messages.success(

            self.request,

            f"{medication_name} was removed from the medication catalog.",

        )

        return response

medication_catalog = MedicationCatalogListView.as_view()

# ============================================================

# LOCAL MEDICATION SEARCH API

# ============================================================

@login_required

@require_GET

def medication_list_api(request: HttpRequest) -> JsonResponse:

    """

    Return active medication concepts for CPOE, medication reconciliation,

    and MAR selection.

    IMPORTANT:

    quantity_on_hand is informational only.

    Local inventory must NOT determine whether a medication can appear in

    clinical ordering/documentation searches.

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

                "display_name": medication.display_name,

                "generic_name": medication.generic_name,

                "strength": medication.strength,

                "dosage_form": medication.dosage_form,

                "route": medication.route,

                "unit_of_measure": medication.unit_of_measure,

                "rxnorm_rxcui": medication.rxnorm_rxcui,

                # Inventory is advisory metadata only.

                "available_quantity": quantity,

                "reorder_level": reorder_level,

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

# RXNORM SEARCH

# ============================================================

@login_required

@require_GET

def us_medication_search_api(request: HttpRequest) -> JsonResponse:

    """

    Search NIH/NLM RxNorm terminology without saving results locally.

    RxNorm provides normalized medication terminology. It does not by

    itself establish that a medication is stocked, approved, clinically

    appropriate, or available locally.

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

            "RxNorm search unavailable for query %r: %s",

            query,

            error,

        )

        return JsonResponse(

            {

                "detail": (

                    "The RxNorm medication terminology service is "

                    "temporarily unavailable."

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

            {

                "detail": (

                    "The medication terminology search could not be "

                    "completed."

                )

            },

            status=502,

        )

    rxcuis = [

        result.rxcui

        for result in rxnorm_results

        if result.rxcui

    ]

    imported_rxcuis = set(

        Medication.objects.filter(

            rxnorm_rxcui__in=rxcuis,

        ).values_list(

            "rxnorm_rxcui",

            flat=True,

        )

    )

    results = [

        {

            "rxcui": medication.rxcui,

            "display_name": medication.name,

            "term_type": medication.term_type,

            "is_imported": medication.rxcui in imported_rxcuis,

        }

        for medication in rxnorm_results

    ]

    return JsonResponse(

        {

            "query": query,

            "count": len(results),

            "results": results,

        }

    )

# ============================================================

# RXNORM IMPORT

# ============================================================

@login_required

@require_POST

def import_us_medication(request: HttpRequest) -> JsonResponse:

    """

    Import an RxNorm concept into the local medication formulary.

    Only authorized formulary managers should perform this action.

    Imported terminology should still undergo local formulary review.

    """

    if not can_manage_medication_catalog(request.user):

        return JsonResponse(

            {

                "detail": (

                    "You do not have permission to add medications "

                    "to the local formulary."

                )

            },

            status=403,

        )

    rxcui = request.POST.get("rxcui", "").strip()

    if not rxcui or not rxcui.isdigit():

        return JsonResponse(

            {

                "detail": (

                    "A valid numeric RxNorm concept identifier is required."

                )

            },

            status=400,

        )

    existing_medication = Medication.objects.filter(

        rxnorm_rxcui=rxcui,

    ).first()

    if existing_medication:

        return JsonResponse(

            {

                "id": existing_medication.pk,

                "code": existing_medication.code,

                "display_name": existing_medication.display_name,

                "generic_name": existing_medication.generic_name,

                "strength": existing_medication.strength,

                "dosage_form": existing_medication.dosage_form,

                "route": existing_medication.route,

                "available_quantity": existing_medication.quantity_on_hand,

                "already_imported": True,

            },

            status=200,

        )

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

                    "The RxNorm medication terminology service is "

                    "temporarily unavailable."

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

            {

                "detail": (

                    "The selected medication concept could not be retrieved."

                )

            },

            status=502,

        )

    if not rxnorm_medication:

        raise Http404("The selected RxNorm medication concept was not found.")

    try:

        with transaction.atomic():

            medication, created = Medication.objects.get_or_create(

                rxnorm_rxcui=rxnorm_medication.rxcui,

                defaults={

                    "code": f"RXNORM-{rxnorm_medication.rxcui}",

                    "generic_name": rxnorm_medication.name,

                    # These values indicate that local clinical/formulary

                    # review is still required.

                    "dosage_form": "Unspecified",

                    "strength": "Unspecified",

                    "route": "Unspecified",

                    "unit_of_measure": "unit",

                    # RxNorm import does not imply physical inventory.

                    "quantity_on_hand": 0,

                },

            )

    except IntegrityError:

        logger.exception(

            "Medication import conflict for RxCUI %s.",

            rxcui,

        )

        medication = Medication.objects.filter(

            rxnorm_rxcui=rxcui,

        ).first()

        if medication is None:

            return JsonResponse(

                {

                    "detail": (

                        "The medication could not be imported because of "

                        "a formulary data conflict."

                    )

                },

                status=409,

            )

        created = False

    return JsonResponse(

        {

            "id": medication.pk,

            "code": medication.code,

            "display_name": medication.display_name,

            "generic_name": medication.generic_name,

            "strength": medication.strength,

            "dosage_form": medication.dosage_form,

            "route": medication.route,

            "available_quantity": medication.quantity_on_hand,

            "already_imported": not created,

            # Make the workflow explicit to the UI.

            "requires_formulary_review": created,

        },

        status=201 if created else 200,

    )