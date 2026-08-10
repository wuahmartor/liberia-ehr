from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse

from apps.encounters.models import Encounter
from apps.orders.models import MedicationOrder
from apps.patients.models import Patient

from .forms import MedicationAdministrationForm
from .models import MedicationAdministration


# ============================================================
# CONSTANTS
# ============================================================


GLOBAL_LIST_LIMIT = 100


# ============================================================
# SHARED CONTEXT
# ============================================================


def medication_context(
    *,
    section: str,
    selected_patient: Patient | None = None,
    active_encounter: Encounter | None = None,
) -> dict[str, Any]:

    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "medications",
        "active_clinical_section": section,
        "selected_patient": selected_patient,
        "active_encounter": active_encounter,
    }


# ============================================================
# HELPERS
# ============================================================


def get_active_patient_encounter(
    patient: Patient,
) -> Encounter | None:
    """
    Return the patient's most recent active encounter.
    """

    return (
        Encounter.objects
        .filter(
            patient=patient,
            is_active=True,
        )
        .order_by(
            "-start_datetime",
            "-pk",
        )
        .first()
    )


def medication_order_queryset() -> QuerySet[MedicationOrder]:
    """
    Shared medication order queryset.

    Pharmacy medication terminology is joined here to prevent
    unnecessary database queries.
    """

    return (
        MedicationOrder.objects
        .select_related(
            "patient",
            "encounter",
            "medication",
            "ordered_by",
        )
    )


def administration_queryset() -> QuerySet[MedicationAdministration]:
    """
    Shared administration queryset.
    """

    return (
        MedicationAdministration.objects
        .select_related(
            "patient",
            "encounter",
            "medication",
            "medication_order",
            "administered_by",
            "witnessed_by",
        )
    )


# ============================================================
# DASHBOARD
# ============================================================


@login_required
def dashboard(
    request: HttpRequest,
) -> HttpResponse:
    """
    Medication application entry point.
    """

    return redirect(
        "medications:list"
    )


# ============================================================
# GLOBAL MEDICATION ACTIVITY
# ============================================================


@login_required
def medication_list(
    request: HttpRequest,
) -> HttpResponse:
    """
    Cross-patient medication activity.

    This is primarily useful to clinical staff as an operational view.
    """

    query = (
        request.GET.get("q")
        or ""
    ).strip()

    medication_orders = medication_order_queryset()

    administrations = administration_queryset()

    if query:

        medication_orders = medication_orders.filter(
            Q(medication__generic_name__icontains=query)
            | Q(medication__brand_name__icontains=query)
            | Q(medication__code__icontains=query)
            | Q(patient__mrn__icontains=query)
        )

        administrations = administrations.filter(
            Q(medication__generic_name__icontains=query)
            | Q(medication__brand_name__icontains=query)
            | Q(medication__code__icontains=query)
            | Q(patient__mrn__icontains=query)
        )

    medication_orders = medication_orders.order_by(
        "-ordered_at"
    )[:GLOBAL_LIST_LIMIT]

    administrations = administrations.order_by(
        "-administered_at"
    )[:GLOBAL_LIST_LIMIT]

    context = medication_context(
        section="list"
    )

    context.update(
        {
            "medication_orders": medication_orders,
            "administrations": administrations,
            "search_query": query,
        }
    )

    return render(
        request,
        "medications/medication_list.html",
        context,
    )


# ============================================================
# PATIENT MEDICATION RECORD
# ============================================================


@login_required
def patient_medication_list(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    active_encounter = get_active_patient_encounter(
        patient
    )

    medication_orders = (
        medication_order_queryset()
        .filter(
            patient=patient,
        )
        .order_by(
            "-ordered_at"
        )
    )

    administrations = (
        administration_queryset()
        .filter(
            patient=patient,
        )
        .order_by(
            "-administered_at"
        )
    )

    context = medication_context(
        section="list",
        selected_patient=patient,
        active_encounter=active_encounter,
    )

    context.update(
        {
            "medication_orders": medication_orders,
            "administrations": administrations,
        }
    )

    return render(
        request,
        "medications/medication_list.html",
        context,
    )


# ============================================================
# MAR
# ============================================================


@login_required
def medication_administration_record(
    request: HttpRequest,
    encounter_id,
) -> HttpResponse:
    """
    Medication Administration Record for an encounter.

    Administrations are created from medication orders rather than
    independently selected formulary medications.
    """

    encounter = get_object_or_404(
        Encounter.objects.select_related(
            "patient",
        ),
        pk=encounter_id,
    )

    patient = encounter.patient

    # --------------------------------------------------------
    # CLOSED ENCOUNTER
    # --------------------------------------------------------

    if not encounter.is_open:

        messages.error(
            request,
            (
                "Medication administrations can only be "
                "recorded for an open encounter."
            ),
        )

        return redirect(
            "medications:patient-list",
            patient_id=patient.pk,
        )

    # --------------------------------------------------------
    # AVAILABLE MEDICATION ORDERS
    # --------------------------------------------------------

    medication_orders = (
        medication_order_queryset()
        .filter(
            encounter=encounter,
            patient=patient,
        )
        .order_by(
            "-ordered_at"
        )
    )

    # --------------------------------------------------------
    # FORM
    # --------------------------------------------------------

    if request.method == "POST":

        form = MedicationAdministrationForm(
            request.POST,
            encounter=encounter,
        )

        if form.is_valid():

            with transaction.atomic():

                administration = form.save(
                    commit=False
                )

                order = form.cleaned_data[
                    "medication_order"
                ]

                # Clinical context comes from the encounter/order,
                # not from user-submitted hidden values.
                administration.patient = patient
                administration.encounter = encounter
                administration.medication_order = order
                administration.medication = order.medication
                administration.administered_by = request.user

                administration.full_clean()
                administration.save()

            messages.success(
                request,
                (
                    "Medication administration "
                    "recorded successfully."
                ),
            )

            return redirect(
                reverse(
                    "medications:mar",
                    kwargs={
                        "encounter_id": encounter.pk,
                    },
                )
            )

    else:

        form = MedicationAdministrationForm(
            encounter=encounter,
        )

    # --------------------------------------------------------
    # ADMINISTRATION HISTORY
    # --------------------------------------------------------

    administrations = (
        administration_queryset()
        .filter(
            encounter=encounter,
        )
        .order_by(
            "-administered_at"
        )
    )

    exceptions = administrations.exclude(
        status=MedicationAdministration.Status.ADMINISTERED
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = medication_context(
        section="mar",
        selected_patient=patient,
        active_encounter=encounter,
    )

    context.update(
        {
            "form": form,
            "medication_orders": medication_orders,
            "administrations": administrations,
            "administration_exceptions": exceptions,
        }
    )

    return render(
        request,
        "medications/mar.html",
        context,
    )


# ============================================================
# MEDICATION RECONCILIATION
# ============================================================


@login_required
def reconciliation(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    """
    Patient medication reconciliation workspace.

    A dedicated reconciliation model can be added later to capture
    source, verification status, discrepancy type, reviewer, and
    reconciliation timestamp.
    """

    patient = get_object_or_404(
        Patient,
        pk=patient_id,
    )

    active_encounter = get_active_patient_encounter(
        patient
    )

    medication_orders = (
        medication_order_queryset()
        .filter(
            patient=patient,
        )
        .order_by(
            "-ordered_at"
        )
    )

    administrations = (
        administration_queryset()
        .filter(
            patient=patient,
        )
        .order_by(
            "-administered_at"
        )
    )

    context = medication_context(
        section="reconciliation",
        selected_patient=patient,
        active_encounter=active_encounter,
    )

    context.update(
        {
            "medication_orders": medication_orders,
            "administrations": administrations,
        }
    )

    return render(
        request,
        "medications/reconciliation.html",
        context,
    )