from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import MedicationOrderForm
from .models import MedicationOrder

def order_context(
    *,
    section: str,
    selected_patient: Patient | None = None,
    active_encounter: Encounter | None = None,
) -> dict:
    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "orders",
        "active_clinical_section": section,
        "selected_patient": selected_patient,
        "active_encounter": active_encounter,
    }


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/order_list.html",
        order_context(section="dashboard"),
    )


@login_required
def order_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/order_list.html",
        order_context(section="all-orders"),
    )


@login_required
def medication_order(
    request: HttpRequest,
    patient_id,
    encounter_id,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter = get_object_or_404(
        Encounter.objects.select_related("patient"),
        pk=encounter_id,
        patient=patient,
    )

    if not encounter.is_open:
        messages.error(
            request,
            "Medication orders can only be entered for an open encounter.",
        )
        return redirect("medications:patient-list", patient_id=patient.pk)

    if request.method == "POST":
        form = MedicationOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.patient = patient
            order.encounter = encounter
            order.ordered_by = request.user
            order.save()
            messages.success(request, "Medication order recorded.")
            return redirect(
                reverse(
                    "orders:medication-order",
                    kwargs={
                        "patient_id": patient.pk,
                        "encounter_id": encounter.pk,
                    },
                )
            )
    else:
        form = MedicationOrderForm()

    medication_orders = (
        MedicationOrder.objects.filter(encounter=encounter)
        .select_related("medication", "ordered_by")
        .order_by("-ordered_at")
    )

    return render(
        request,
        "orders/medication_order.html",
        order_context(
            section="medication-order",
            selected_patient=patient,
            active_encounter=encounter,
        )
        | {
            "form": form,
            "medication_orders": medication_orders,
        },
    )


@login_required
def imaging_orders(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/imaging_orders.html",
        order_context(section="imaging"),
    )


@login_required
def pending_orders(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "orders/pending_orders.html",
        order_context(section="pending"),
    )