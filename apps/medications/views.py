from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import MedicationAdministrationForm
from .models import MedicationAdministration

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

    if not encounter.is_open:
        messages.error(
            request,
            "Medication administrations can only be recorded for an open encounter.",
        )
        return redirect(
            "medications:patient-list",
            patient_id=encounter.patient_id,
        )

    if request.method == "POST":
        form = MedicationAdministrationForm(request.POST)
        if form.is_valid():
            administration = form.save(commit=False)
            administration.patient = encounter.patient
            administration.encounter = encounter
            administration.administered_by = request.user
            administration.save()
            messages.success(request, "Medication administration recorded.")
            return redirect(
                reverse(
                    "medications:mar",
                    kwargs={"encounter_id": encounter.pk},
                )
            )
    else:
        form = MedicationAdministrationForm()

    administrations = (
        MedicationAdministration.objects.filter(encounter=encounter)
        .select_related("medication", "administered_by")
        .order_by("-administered_at")
    )

    return render(
        request,
        "medications/mar.html",
        medication_context(
            section="mar",
            selected_patient=encounter.patient,
            active_encounter=encounter,
        )
        | {
            "form": form,
            "administrations": administrations,
        },
    )


@login_required
def reconciliation(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "medications/reconciliation.html",
        medication_context(section="reconciliation"),
    )