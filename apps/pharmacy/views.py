from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import MedicationForm
from .models import Medication


def pharmacy_context(section: str) -> dict:
    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "pharmacy",
        "active_clinical_section": section,
    }


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    low_stock_count = Medication.objects.filter(
        quantity_on_hand__lte=F("reorder_level"),
    ).count()
    return render(
        request,
        "pharmacy/dashboard.html",
        pharmacy_context("dashboard")
        | {
            "catalog_count": Medication.objects.active().count(),
            "low_stock_count": low_stock_count,
        },
    )


@login_required
def queue(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/queue.html",
        pharmacy_context("queue"),
    )


@login_required
def pending_review(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/pending_review.html",
        pharmacy_context("pending-review"),
    )


@login_required
def verified(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/verified.html",
        pharmacy_context("verified"),
    )


@login_required
def dispensing(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/dispensing.html",
        pharmacy_context("dispensing"),
    )


@login_required
def inventory(request: HttpRequest) -> HttpResponse:
    medications = Medication.objects.filter(
        quantity_on_hand__lte=F("reorder_level"),
    ).order_by("quantity_on_hand", "generic_name")
    return render(
        request,
        "pharmacy/inventory.html",
        pharmacy_context("inventory") | {"medications": medications},
    )


class MedicationCatalogListView(LoginRequiredMixin, ListView):
    model = Medication
    context_object_name = "medications"
    template_name = "pharmacy/medication_catalog.html"

    def get_queryset(self):
        return Medication.objects.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(pharmacy_context("medication-catalog"))
        return context


class MedicationCatalogCreateView(LoginRequiredMixin, CreateView):
    model = Medication
    form_class = MedicationForm
    template_name = "pharmacy/medication_catalog.html"
    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(pharmacy_context("medication-catalog"))
        context["form_mode"] = "create"
        context["medications"] = Medication.objects.all()
        return context


class MedicationCatalogUpdateView(LoginRequiredMixin, UpdateView):
    model = Medication
    form_class = MedicationForm
    template_name = "pharmacy/medication_catalog.html"
    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(pharmacy_context("medication-catalog"))
        context["form_mode"] = "update"
        context["medications"] = Medication.objects.all()
        return context


class MedicationCatalogDeleteView(LoginRequiredMixin, DeleteView):
    model = Medication
    template_name = "pharmacy/medication_catalog.html"
    success_url = reverse_lazy("pharmacy:medication-catalog")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(pharmacy_context("medication-catalog"))
        context["form_mode"] = "delete"
        context["medications"] = Medication.objects.all()
        return context


medication_catalog = MedicationCatalogListView.as_view()


@login_required
@require_GET
def medication_list_api(request: HttpRequest) -> JsonResponse:
    """Return active catalog medications for order and MAR selection."""
    query = request.GET.get("q", "")
    medications = Medication.objects.active().search(query).order_by(
        "generic_name",
        "code",
        "pk",
    )[:50]

    return JsonResponse(
        [
            {
                "id": medication.pk,
                "code": medication.code,
                "display_name": medication.display_name,
                "generic_name": medication.generic_name,
                "strength": medication.strength,
                "dosage_form": medication.dosage_form,
                "route": medication.route,
                "available_quantity": medication.quantity_on_hand,
            }
            for medication in medications
        ],
        safe=False,
    )


@login_required
def interactions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/interactions.html",
        pharmacy_context("interactions"),
    )


@login_required
def rejected(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/rejected.html",
        pharmacy_context("rejected"),
    )