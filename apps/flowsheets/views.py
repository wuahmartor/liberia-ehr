from django.contrib import messages
import json
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import EnteredInErrorForm, FlowSheetEntryForm
from .models import FlowSheetDefinition, FlowSheetEntry


def _base_context(patient=None, encounter=None, section="flowsheets"):
    return {
        "selected_patient": patient,
        "active_encounter": encounter,
        "active_primary_nav": "clinical",
        "active_clinical_module": "flowsheets",
        "active_clinical_section": section,
    }


def _patient_entries(patient, encounter=None):
    entries = FlowSheetEntry.objects.filter(patient=patient).select_related("flowsheet", "recorded_by", "encounter")
    if encounter:
        entries = entries.filter(encounter=encounter)
    return entries.prefetch_related("values__field")


@login_required
@require_GET
def index(request):
    entries = FlowSheetEntry.objects.select_related("patient", "encounter", "flowsheet", "recorded_by").prefetch_related("values__field")[:100]
    return render(request, "flowsheets/index.html", {**_base_context(), "entries": entries, "definitions": FlowSheetDefinition.objects.filter(is_active=True)})


@login_required
@require_GET
def patient_flowsheet(request, patient_id, definition_slug=None):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter_id = request.GET.get("encounter")
    scoped_encounter = get_object_or_404(Encounter, pk=encounter_id, patient=patient) if encounter_id else None
    definitions = list(FlowSheetDefinition.objects.filter(is_active=True).prefetch_related("fields"))
    definition_id = request.GET.get("definition")
    selected_definition = next((item for item in definitions if item.slug == definition_slug), None)
    if definition_slug and selected_definition is None:
        raise Http404("Flowsheet definition not found.")
    if selected_definition is None and definition_id:
        selected_definition = next((item for item in definitions if str(item.pk) == definition_id), None)
    if selected_definition is None:
        selected_definition = next((item for item in definitions if item.slug == "nursing-systems-assessment"), definitions[0] if definitions else None)
    entries = list(_patient_entries(patient, scoped_encounter).filter(flowsheet=selected_definition)[:24]) if selected_definition else []
    matrix_rows = []
    matrix_sections = []
    if selected_definition:
        current_section = None
        for field in selected_definition.fields.all():
            cells = []
            for entry in entries:
                cells.append(next((value for value in entry.values.all() if value.field_id == field.pk), None))
            row = {"field": field, "cells": cells}
            matrix_rows.append(row)
            section_name = field.section or "General"
            if current_section is None or current_section["name"] != section_name:
                current_section = {"name": section_name, "rows": []}
                matrix_sections.append(current_section)
            current_section["rows"].append(row)
    active_encounter = scoped_encounter or Encounter.objects.filter(patient=patient, is_active=True).order_by("-start_datetime", "-created_at").first()
    return render(request, "flowsheets/patient.html", {**_base_context(patient, active_encounter), "patient": patient, "definitions": definitions, "selected_definition": selected_definition, "entries": entries, "matrix_rows": matrix_rows, "matrix_sections": matrix_sections, "assessment_types": FlowSheetEntry.AssessmentType.choices})


@login_required
@require_GET
def encounter_flowsheet(request, encounter_id):
    encounter = get_object_or_404(Encounter.objects.select_related("patient"), pk=encounter_id)
    target = reverse("flowsheets:patient", args=[encounter.patient_id])
    query_data = request.GET.copy()
    query_data["encounter"] = str(encounter.pk)
    query = query_data.urlencode()
    return redirect(f"{target}?{query}" if query else target)


@login_required
@require_http_methods(["GET", "POST"])
def create_entry(request, patient_id, definition_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    definition = get_object_or_404(FlowSheetDefinition.objects.filter(is_active=True).prefetch_related("fields"), pk=definition_id)
    encounter_id = request.GET.get("encounter") or request.POST.get("encounter")
    encounter = get_object_or_404(Encounter, pk=encounter_id, patient=patient) if encounter_id else Encounter.objects.filter(patient=patient, is_active=True).order_by("-start_datetime", "-created_at").first()
    requested_type = request.GET.get("assessment_type", FlowSheetEntry.AssessmentType.SHIFT)
    valid_types = {value for value, _label in FlowSheetEntry.AssessmentType.choices}
    initial = {"assessment_type": requested_type if requested_type in valid_types else FlowSheetEntry.AssessmentType.SHIFT, "recorded_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")}
    form = FlowSheetEntryForm(request.POST or None, definition=definition, initial=initial)
    if request.method == "POST" and form.is_valid():
        entry = form.save(patient=patient, encounter=encounter, actor=request.user)
        messages.success(request, f"{definition.name} recorded.")
        if request.headers.get("HX-Request") == "true":
            return render(request, "flowsheets/partials/entry_saved.html", {"entry": entry, "patient": patient, "definition": definition, "active_encounter": encounter})
        return redirect(entry)
    return render(request, "flowsheets/form.html", {**_base_context(patient, encounter), "patient": patient, "definition": definition, "form": form, "organized_sections": form.organized_sections(), "inline": request.headers.get("HX-Request") == "true" or request.GET.get("inline") == "1"})


@login_required
@require_GET
def entry_detail(request, entry_id):
    entry = get_object_or_404(FlowSheetEntry.objects.select_related("patient", "encounter", "flowsheet", "recorded_by", "entered_in_error_by").prefetch_related("values__field"), pk=entry_id)
    return render(request, "flowsheets/detail.html", {**_base_context(entry.patient, entry.encounter), "entry": entry, "error_form": EnteredInErrorForm()})


@login_required
@require_http_methods(["GET", "POST"])
def correct_entry(request, entry_id):
    original = get_object_or_404(
        FlowSheetEntry.objects.exclude(status=FlowSheetEntry.Status.ENTERED_IN_ERROR)
        .select_related("patient", "encounter", "flowsheet")
        .prefetch_related("values__field", "flowsheet__fields"),
        pk=entry_id,
    )
    initial = {"assessment_type": original.assessment_type, "recorded_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M"), "notes": original.notes}
    for value in original.values.all():
        raw_value = value.value_number if value.value_number is not None else value.value_boolean if value.value_boolean is not None else value.value_text
        if value.field.data_type == value.field.DataType.MULTI_CHOICE:
            try:
                raw_value = json.loads(value.value_text)
            except (TypeError, ValueError):
                raw_value = []
        initial[f"value_{value.field_id}"] = raw_value
    form = FlowSheetEntryForm(request.POST or None, definition=original.flowsheet, require_correction_reason=True, initial=initial)
    if request.method == "POST" and form.is_valid():
        correction = form.save(patient=original.patient, encounter=original.encounter, actor=request.user, corrected_from=original)
        messages.success(request, "Corrected flowsheet entry signed; the original was retained.")
        return redirect(correction)
    return render(request, "flowsheets/form.html", {**_base_context(original.patient, original.encounter), "patient": original.patient, "definition": original.flowsheet, "form": form, "organized_sections": form.organized_sections(), "corrected_from": original})


@login_required
@require_POST
def entered_in_error(request, entry_id):
    entry = get_object_or_404(FlowSheetEntry, pk=entry_id)
    form = EnteredInErrorForm(request.POST)
    if form.is_valid() and entry.status != FlowSheetEntry.Status.ENTERED_IN_ERROR:
        entry.status = FlowSheetEntry.Status.ENTERED_IN_ERROR
        entry.correction_reason = form.cleaned_data["reason"]
        entry.entered_in_error_at = timezone.now()
        entry.entered_in_error_by = request.user
        entry.save(update_fields=["status", "correction_reason", "entered_in_error_at", "entered_in_error_by"])
        messages.success(request, "Flowsheet entry marked entered in error.")
    elif not form.is_valid():
        messages.error(request, "Provide a reason of at least five characters.")
    return redirect(entry)
