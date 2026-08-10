from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.encounters.models import Encounter
from apps.patients.models import Patient


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

    return render(
        request,
        "orders/medication_order.html",
        order_context(
            section="medication-order",
            selected_patient=patient,
            active_encounter=encounter,
        ),
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