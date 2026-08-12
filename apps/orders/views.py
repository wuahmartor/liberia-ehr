from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

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
    medication_orders = (
        MedicationOrder.objects.select_related(
            "patient",
            "encounter",
            "medication",
            "ordered_by",
        )
        .order_by("-ordered_at")[:100]
    )
    return render(
        request,
        "orders/order_list.html",
        order_context(section="all-orders")
        | {"medication_orders": medication_orders},
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

    if request.method == "POST" and request.POST.get("order_action"):
        order = get_object_or_404(
            MedicationOrder,
            pk=request.POST.get("medication_order"),
            patient=patient,
            encounter=encounter,
        )
        action = request.POST.get("order_action", "").strip().lower()
        if action == "discontinue":
            provider_id = request.POST.get("discontinuation_ordered_by")
            method = request.POST.get("discontinuation_order_method", "")
            reason = request.POST.get("discontinuation_reason", "").strip()
            valid_methods = {value for value, _ in MedicationOrder.OrderMethod.choices}
            if not provider_id or method not in valid_methods or not reason:
                messages.error(
                    request, "Provider, order medium, and reason are required."
                )
                return redirect(
                    "orders:medication-order",
                    patient_id=patient.pk,
                    encounter_id=encounter.pk,
                )
            provider = get_object_or_404(
                get_user_model(), pk=provider_id, is_active=True
            )
            order.status = MedicationOrder.Status.DISCONTINUED
            order.discontinued_at = timezone.now()
            order.discontinued_by = request.user
            order.discontinuation_ordered_by = provider
            order.discontinuation_order_method = method
            order.discontinuation_received_by = (
                request.user if method in {"verbal", "telephone"} else None
            )
            order.discontinuation_reason = reason
            order.save()
            messages.success(request, "Medication discontinuation order recorded.")
            return redirect(
                "orders:medication-order",
                patient_id=patient.pk,
                encounter_id=encounter.pk,
            )
        transitions = {
            "hold": (
                {MedicationOrder.Status.ACTIVE},
                MedicationOrder.Status.ON_HOLD,
                "Medication order placed on hold.",
            ),
            "resume": (
                {MedicationOrder.Status.ON_HOLD},
                MedicationOrder.Status.ACTIVE,
                "Medication order resumed.",
            ),
            "discontinue": (
                {MedicationOrder.Status.ACTIVE, MedicationOrder.Status.ON_HOLD},
                MedicationOrder.Status.DISCONTINUED,
                "Medication order discontinued.",
            ),
        }
        transition = transitions.get(action)
        if not transition or order.status not in transition[0]:
            messages.error(
                request, "That medication order status change is not allowed."
            )
        else:
            order.status = transition[1]
            order.save(update_fields=["status", "updated_at"])
            messages.success(request, transition[2])
        return redirect(
            "orders:medication-order",
            patient_id=patient.pk,
            encounter_id=encounter.pk,
        )

    if request.method == "POST":
        form = MedicationOrderForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.patient = patient
            order.encounter = encounter
            if order.order_method in {
                MedicationOrder.OrderMethod.VERBAL,
                MedicationOrder.OrderMethod.TELEPHONE,
            }:
                order.received_by = request.user
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
            "ordering_providers": get_user_model().objects.filter(
                is_active=True
            ).order_by("last_name", "first_name", "username"),
            "order_methods": MedicationOrder.OrderMethod.choices,
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
