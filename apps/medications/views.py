from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from apps.encounters.models import Encounter
from apps.patients.models import Patient


def medication_context(
    *,
    section: str,
    selected_patient: Patient | None = None,
    active_encounter: Encounter | None = None,
) -> dict:
    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "medications",
        "active_clinical_section": section,
        "selected_patient": selected_patient,
        "active_encounter": active_encounter,
    }


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/medication_list.html",
        medication_context(section="list"),
    )


@login_required
def medication_list(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/medication_list.html",
        medication_context(section="list"),
    )


@login_required
def patient_medication_list(
    request: HttpRequest,
    patient_id,
) -> HttpResponse:
    patient = get_object_or_404(Patient, pk=patient_id)
    active_encounter = (
        Encounter.objects.filter(
            patient=patient,
            is_active=True,
        )
        .order_by("-start_datetime")
        .first()
    )

    return render(
        request,
        "medications/medication_list.html",
        medication_context(
            section="list",
            selected_patient=patient,
            active_encounter=active_encounter,
        ),
    )


@login_required
def medication_administration_record(
    request: HttpRequest,
    encounter_id,
) -> HttpResponse:
    encounter = get_object_or_404(
        Encounter.objects.select_related("patient"),
        pk=encounter_id,
    )

    return render(
        request,
        "medications/mar.html",
        medication_context(
            section="mar",
            selected_patient=encounter.patient,
            active_encounter=encounter,
        ),
    )


@login_required
def reconciliation(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/reconciliation.html",
        medication_context(section="reconciliation"),
    )