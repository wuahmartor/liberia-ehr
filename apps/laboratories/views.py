from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import LabOrderForm, LabResultForm
from .models import LabOrder, LabOrderItem, LabPanel, LabResult, LabSpecimen
from .services import create_panel_order, matching_reference_range, result_payload, save_numeric_result


def context(patient=None, encounter=None):
    return {"selected_patient": patient, "active_encounter": encounter, "active_primary_nav": "clinical", "active_clinical_module": "laboratory", "active_secondary_nav": "laboratory"}


@login_required
@require_GET
def dashboard(request):
    orders = LabOrder.objects.select_related("patient", "encounter", "panel", "ordered_by").prefetch_related("items__result")[:100]
    return render(request, "laboratories/index.html", {**context(), "orders": orders, "panels": LabPanel.objects.filter(is_active=True), "critical_results": LabResult.objects.filter(flag__in=(LabResult.Flag.CRITICAL_LOW, LabResult.Flag.CRITICAL_HIGH)).select_related("order_item__order__patient", "order_item__test")[:20]})


@login_required
@require_GET
def patient_results(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter_id = request.GET.get("encounter")
    encounter = get_object_or_404(Encounter, pk=encounter_id, patient=patient) if encounter_id else None
    orders = LabOrder.objects.filter(patient=patient).select_related("panel", "encounter", "ordered_by").prefetch_related("items__test", "items__result")
    if encounter:
        orders = orders.filter(encounter=encounter)
    return render(request, "laboratories/patient_results.html", {**context(patient, encounter), "patient": patient, "orders": orders})


@login_required
@require_http_methods(["GET", "POST"])
def create_order(request, patient_id, encounter_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter = get_object_or_404(Encounter, pk=encounter_id, patient=patient)
    form = LabOrderForm(request.POST or None, patient=patient)
    if request.method == "POST" and form.is_valid():
        order = create_panel_order(patient=patient, encounter=encounter, panel=form.cleaned_data["panel"], standalone_tests=form.cleaned_data["standalone_tests"], priority=form.cleaned_data["priority"], indication=form.cleaned_data["clinical_indication"], indication_diagnosis=form.cleaned_data["indication_diagnosis"], actor=request.user)
        messages.success(request, f"{order.panel.name if order.panel else 'Standalone laboratory tests'} ordered.")
        return redirect(order)
    return render(request, "laboratories/form.html", {**context(patient, encounter), "form": form, "patient": patient})


@login_required
@require_GET
def order_detail(request, order_id):
    order = get_object_or_404(LabOrder.objects.select_related("patient", "encounter", "panel", "ordered_by").prefetch_related("items__test__reference_ranges", "items__result__recommendations", "specimens"), pk=order_id)
    return render(request, "laboratories/detail.html", {**context(order.patient, order.encounter), "order": order})


@login_required
@require_POST
def collect_specimen(request, order_id):
    order = get_object_or_404(LabOrder, pk=order_id)
    first_item = order.items.select_related("test").first()
    LabSpecimen.objects.create(order=order, specimen_type=first_item.test.specimen_type if first_item else "Blood", status=LabSpecimen.Status.COLLECTED, collected_at=timezone.now(), collected_by=request.user)
    order.status = LabOrder.Status.COLLECTED
    order.save(update_fields=["status"])
    messages.success(request, "Specimen collection documented.")
    return redirect(order)


@login_required
@require_http_methods(["GET", "POST"])
def enter_result(request, item_id):
    item = get_object_or_404(LabOrderItem.objects.select_related("order__patient", "order__encounter", "test"), pk=item_id)
    reference = matching_reference_range(item.test, item.order.patient)
    form = LabResultForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        result = save_numeric_result(order_item=item, value=form.cleaned_data["numeric_value"], notes=form.cleaned_data["notes"], actor=request.user)
        messages.success(request, f"{item.test.name} resulted as {result.get_flag_display()}.")
        return redirect(item.order)
    return render(request, "laboratories/result_entry.html", {**context(item.order.patient, item.order.encounter), "item": item, "reference": reference, "form": form})


@login_required
@require_POST
def verify_result(request, result_id):
    result = get_object_or_404(LabResult, pk=result_id)
    result.verified_by = request.user
    result.verified_at = timezone.now()
    result.save(update_fields=["verified_by", "verified_at"])
    return redirect(result.order_item.order)


@login_required
@require_POST
def acknowledge_critical(request, result_id):
    result = get_object_or_404(LabResult, pk=result_id, flag__in=(LabResult.Flag.CRITICAL_LOW, LabResult.Flag.CRITICAL_HIGH))
    note = request.POST.get("note", "").strip()
    if len(note) < 5:
        messages.error(request, "Document who was notified and the action taken.")
    else:
        result.critical_acknowledged_by = request.user
        result.critical_acknowledged_at = timezone.now()
        result.critical_acknowledgment_note = note
        result.save(update_fields=("critical_acknowledged_by", "critical_acknowledged_at", "critical_acknowledgment_note"))
        messages.success(request, "Critical-result acknowledgement documented.")
    return redirect(result.order_item.order)


@login_required
@require_GET
def result_json(request, result_id):
    from django.http import JsonResponse
    result = get_object_or_404(LabResult.objects.select_related("order_item__order", "order_item__test"), pk=result_id)
    return JsonResponse(result_payload(result))
