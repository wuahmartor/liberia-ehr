from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.decision_support.models import ClinicalAlert, ClinicalRule

from .models import LabClinicalRecommendation, LabOrder, LabOrderItem, LabReferenceRange, LabResult


def matching_reference_range(test, patient):
    ranges = test.reference_ranges.all()
    age = patient.age
    sex = patient.sex_at_birth if patient.sex_at_birth in ("female", "male") else "any"
    matches = [item for item in ranges if item.age_min_years <= age and (item.age_max_years is None or age <= item.age_max_years) and item.sex in ("any", sex)]
    matches.sort(key=lambda item: (item.sex != sex, -item.age_min_years))
    return matches[0] if matches else None


def classify_result(value: Decimal, reference):
    if reference is None:
        return LabResult.Flag.ABNORMAL
    if reference.critical_low is not None and value <= reference.critical_low:
        return LabResult.Flag.CRITICAL_LOW
    if reference.critical_high is not None and value >= reference.critical_high:
        return LabResult.Flag.CRITICAL_HIGH
    if reference.lower_bound is not None and value < reference.lower_bound:
        return LabResult.Flag.LOW
    if reference.upper_bound is not None and value > reference.upper_bound:
        return LabResult.Flag.HIGH
    return LabResult.Flag.NORMAL


@transaction.atomic
def create_panel_order(*, patient, encounter, panel=None, standalone_tests=(), priority, indication, indication_diagnosis=None, actor):
    indication_snapshot = indication.strip() or (f"{indication_diagnosis.code_snapshot} — {indication_diagnosis.display_snapshot}" if indication_diagnosis else "Laboratory evaluation")
    order = LabOrder.objects.create(patient=patient, encounter=encounter, panel=panel, indication_diagnosis=indication_diagnosis, priority=priority, clinical_indication=indication_snapshot, ordered_by=actor)
    tests = {item.test_id: item.test for item in panel.panel_tests.select_related("test")} if panel else {}
    tests.update({test.pk: test for test in standalone_tests})
    LabOrderItem.objects.bulk_create([LabOrderItem(order=order, test=test) for test in tests.values()])
    return order


def result_payload(result):
    return {
        "patient_id": str(result.order_item.order.patient_id), "encounter_id": str(result.order_item.order.encounter_id),
        "accession": result.order_item.order.accession_number, "test_code": result.order_item.test.code,
        "loinc_code": result.order_item.test.loinc_code, "value": str(result.numeric_value) if result.numeric_value is not None else result.text_value,
        "unit": result.unit, "flag": result.flag, "reference_range": result.reference_range_snapshot,
        "status": result.status, "resulted_at": result.resulted_at.isoformat(),
    }


def generate_recommendation(result):
    if result.flag == LabResult.Flag.NORMAL:
        return None
    critical = result.flag in (LabResult.Flag.CRITICAL_LOW, LabResult.Flag.CRITICAL_HIGH)
    qualifier = "critical" if critical else "outside the reference interval"
    recommendation, _ = LabClinicalRecommendation.objects.get_or_create(
        result=result,
        title=f"{result.order_item.test.short_name}: {result.get_flag_display()}",
        defaults={
            "recommendation": f"Review this {qualifier} result promptly in the patient's clinical context. Confirm specimen integrity, compare prior results, review relevant medications and conditions, and follow the locally approved escalation protocol.",
            "evidence_reference": result.reference_range.source_url if result.reference_range else "Local laboratory policy required",
        },
    )
    rule = ClinicalRule.objects.filter(code=f"lab-{result.order_item.test.code}-{result.flag}", is_active=True).first()
    if rule:
        ClinicalAlert.objects.get_or_create(
            rule=rule, patient=result.order_item.order.patient, encounter=result.order_item.order.encounter,
            title=recommendation.title, status=ClinicalAlert.Status.OPEN,
            defaults={"message": rule.recommendation, "supporting_data": result_payload(result)},
        )
    return recommendation


@transaction.atomic
def save_numeric_result(*, order_item, value, actor, notes=""):
    reference = matching_reference_range(order_item.test, order_item.order.patient)
    flag = classify_result(value, reference)
    snapshot = {}
    if reference:
        snapshot = {"label": reference.label, "low": str(reference.lower_bound) if reference.lower_bound is not None else None, "high": str(reference.upper_bound) if reference.upper_bound is not None else None, "critical_low": str(reference.critical_low) if reference.critical_low is not None else None, "critical_high": str(reference.critical_high) if reference.critical_high is not None else None, "unit": reference.unit, "source_title": reference.source_title, "source_url": reference.source_url, "locally_validated": reference.is_locally_validated}
    result, _ = LabResult.objects.update_or_create(
        order_item=order_item,
        defaults={"numeric_value": value, "text_value": "", "unit": reference.unit if reference else order_item.test.default_unit, "reference_range": reference, "reference_range_snapshot": snapshot, "flag": flag, "status": LabResult.Status.FINAL, "resulted_by": actor, "resulted_at": timezone.now(), "notes": notes},
    )
    generate_recommendation(result)
    order = order_item.order
    resulted = LabResult.objects.filter(order_item__order=order).count()
    order.status = LabOrder.Status.FINAL if resulted == order.items.count() else LabOrder.Status.PARTIAL
    order.save(update_fields=["status"])
    return result
