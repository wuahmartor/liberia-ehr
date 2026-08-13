from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import DiagnosisErrorForm, PatientDiagnosisForm, PatientProcedureForm
from .models import (
    ClinicalConcept,
    ClinicalConceptTerm,
    PatientDiagnosis,
    PatientProcedure,
    ProcedureCode,
    TerminologySource,
)


def _context(patient=None, encounter=None, **extra):
    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "diagnoses",
        "selected_patient": patient,
        "active_encounter": encounter,
        **extra,
    }


def _active_encounter(patient):
    return (
        Encounter.objects.filter(patient=patient, is_active=True)
        .order_by("-start_datetime")
        .first()
    )


@login_required
def diagnosis_list(request, patient_id=None):
    patient = get_object_or_404(Patient, pk=patient_id) if patient_id else None
    qs = PatientDiagnosis.objects.select_related(
        "patient", "encounter", "concept", "concept__source", "recorded_by"
    )
    if patient:
        qs = qs.filter(patient=patient)
    elif request.GET.get("patient"):
        patient = get_object_or_404(Patient, pk=request.GET["patient"])
        qs = qs.filter(patient=patient)
    else:
        # Clinical records remain patient-contextual; never expose a global
        # cross-patient problem list when no chart is selected.
        qs = qs.none()
    status = request.GET.get("status", "current")
    if status == "current":
        qs = qs.filter(is_current_problem=True).exclude(
            clinical_status=PatientDiagnosis.DiagnosisStatus.ENTERED_IN_ERROR
        )
    elif status != "all":
        qs = qs.filter(clinical_status=status)
    query = request.GET.get("q", "").strip()
    if query:
        qs = qs.filter(
            Q(code_snapshot__icontains=query)
            | Q(display_snapshot__icontains=query)
            | Q(patient__mrn__icontains=query)
        )
    context = _context(
        patient,
        _active_encounter(patient) if patient else None,
        diagnoses=qs,
        query=query,
        selected_status=status,
        status_choices=PatientDiagnosis.DiagnosisStatus.choices,
    )
    return render(
        request,
        "diagnoses/partials/list_content.html"
        if request.headers.get("HX-Request")
        else "diagnoses/list.html",
        context,
    )


@login_required
@require_http_methods(["GET", "POST"])
def diagnosis_create(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter = (
        get_object_or_404(Encounter, pk=request.GET["encounter"], patient=patient)
        if request.GET.get("encounter")
        else _active_encounter(patient)
    )
    form = PatientDiagnosisForm(
        request.POST or None, patient=patient, encounter=encounter
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            diagnosis = form.save(commit=False)
            diagnosis.patient, diagnosis.recorded_by = patient, request.user
            if (
                diagnosis.verification_status
                == PatientDiagnosis.VerificationStatus.CONFIRMED
            ):
                diagnosis.confirmed_by, diagnosis.confirmed_at = (
                    request.user,
                    timezone.now(),
                )
            diagnosis.populate_snapshots()
            diagnosis.full_clean()
            diagnosis.save()
        messages.success(request, "Diagnosis added to the patient record.")
        return redirect("diagnoses:detail", diagnosis_id=diagnosis.pk)
    return render(
        request,
        "diagnoses/form.html",
        _context(
            patient, encounter, form=form, page_title="Add diagnosis", is_create=True
        ),
    )


@login_required
@require_http_methods(["GET", "POST"])
def diagnosis_update(request, diagnosis_id):
    diagnosis = get_object_or_404(
        PatientDiagnosis.objects.select_related("patient", "encounter", "concept"),
        pk=diagnosis_id,
    )
    form = PatientDiagnosisForm(
        request.POST or None, instance=diagnosis, patient=diagnosis.patient
    )
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        if (
            updated.verification_status == PatientDiagnosis.VerificationStatus.CONFIRMED
            and not updated.confirmed_at
        ):
            updated.confirmed_by, updated.confirmed_at = request.user, timezone.now()
        updated.full_clean()
        updated.save()
        messages.success(request, "Diagnosis updated.")
        return redirect("diagnoses:detail", diagnosis_id=updated.pk)
    return render(
        request,
        "diagnoses/form.html",
        _context(
            diagnosis.patient,
            diagnosis.encounter,
            form=form,
            diagnosis=diagnosis,
            page_title="Edit diagnosis",
        ),
    )


@login_required
def diagnosis_detail(request, diagnosis_id):
    diagnosis = get_object_or_404(
        PatientDiagnosis.objects.select_related(
            "patient",
            "encounter",
            "concept",
            "concept__source",
            "recorded_by",
            "confirmed_by",
        ).prefetch_related("manifestations__concept"),
        pk=diagnosis_id,
    )
    return render(
        request,
        "diagnoses/detail.html",
        _context(
            diagnosis.patient,
            diagnosis.encounter,
            diagnosis=diagnosis,
            error_form=DiagnosisErrorForm(),
        ),
    )


@login_required
@require_http_methods(["POST"])
def diagnosis_entered_in_error(request, diagnosis_id):
    diagnosis = get_object_or_404(PatientDiagnosis, pk=diagnosis_id)
    form = DiagnosisErrorForm(request.POST)
    if form.is_valid():
        diagnosis.clinical_status = PatientDiagnosis.DiagnosisStatus.ENTERED_IN_ERROR
        diagnosis.is_current_problem = False
        audit = f"Entered in error by {request.user} at {timezone.localtime():%Y-%m-%d %H:%M}: {form.cleaned_data['reason']}"
        diagnosis.notes = f"{diagnosis.notes}\n\n{audit}".strip()
        diagnosis.save(
            update_fields=[
                "clinical_status",
                "is_current_problem",
                "notes",
                "updated_at",
            ]
        )
        messages.warning(
            request, "Diagnosis retained for audit and marked entered in error."
        )
        return redirect("diagnoses:patient-list", patient_id=diagnosis.patient_id)
    messages.error(
        request, "Provide a reason before marking the diagnosis entered in error."
    )
    return redirect("diagnoses:detail", diagnosis_id=diagnosis.pk)


@login_required
def icd10_search(request):
    query = request.GET.get(
        "q",
        request.GET.get("concept_query", request.GET.get("note_diagnosis_query", "")),
    ).strip()
    results = ClinicalConcept.objects.none()
    if len(query) >= 2:
        term_ids = ClinicalConceptTerm.objects.filter(
            term__icontains=query, is_active=True
        ).values("concept_id")
        results = (
            ClinicalConcept.objects.filter(
                source__source_type=TerminologySource.SourceType.ICD_10,
                source__is_active=True,
                is_active=True,
            )
            .filter(
                Q(code__icontains=query)
                | Q(title__icontains=query)
                | Q(pk__in=term_ids)
            )
            .select_related("source")
            .distinct()
            .order_by("code")[:20]
        )
    template = (
        "diagnoses/partials/note_icd10_results.html"
        if request.GET.get("target") == "clinical-note"
        else "diagnoses/partials/icd10_results.html"
    )
    return render(request, template, {"results": results, "query": query})


@login_required
def procedure_list(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    procedures = (
        PatientProcedure.objects.filter(patient=patient)
        .exclude(status=PatientProcedure.Status.ENTERED_IN_ERROR)
        .select_related(
            "procedure_code", "procedure_code__source", "encounter", "performed_by"
        )
    )
    return render(
        request,
        "diagnoses/procedure_list.html",
        _context(patient, _active_encounter(patient), procedures=procedures),
    )


@login_required
@require_http_methods(["GET", "POST"])
def procedure_create(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter = (
        get_object_or_404(Encounter, pk=request.GET["encounter"], patient=patient)
        if request.GET.get("encounter")
        else _active_encounter(patient)
    )
    form = PatientProcedureForm(
        request.POST or None, patient=patient, encounter=encounter
    )
    if request.method == "POST" and form.is_valid():
        procedure = form.save(commit=False)
        procedure.patient = patient
        procedure.recorded_by = request.user
        procedure.full_clean()
        procedure.save()
        messages.success(request, "Coded procedure added to the patient record.")
        return redirect("diagnoses:procedure-list", patient_id=patient.pk)
    return render(
        request,
        "diagnoses/procedure_form.html",
        _context(patient, encounter, form=form),
    )


@login_required
def cpt_search(request):
    query = request.GET.get(
        "procedure_query", request.GET.get("q", request.GET.get("note_procedure_query", ""))
    ).strip()
    results = ProcedureCode.objects.none()
    if len(query) >= 2:
        results = (
            ProcedureCode.objects.filter(
                code_system=ProcedureCode.CodeSystem.CPT, is_active=True
            )
            .filter(
                Q(code__icontains=query)
                | Q(title__icontains=query)
                | Q(description__icontains=query)
            )
            .select_related("source")
            .order_by("code")[:20]
        )
    template = (
        "diagnoses/partials/note_cpt_results.html"
        if request.GET.get("target") == "clinical-note"
        else "diagnoses/partials/cpt_results.html"
    )
    return render(request, template, {"results": results, "query": query})
