from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.decision_support.models import ClinicalAlert, ClinicalRule, RiskAssessment
from apps.encounters.models import Encounter
from apps.patients.models import Patient, PatientAllergy

from .fall_risk import score_assessment
from .forms import (
    IntakeOutputForm,
    NursingAssessmentForm,
    NursingFallRiskAssessmentForm,
    NursingHandoffForm,
    NursingTaskForm,
)
from .models import (
    IntakeOutputRecord,
    NursingAssessment,
    NursingFallRiskAssessment,
    NursingHandoff,
    NursingTask,
)


@login_required
def workspace(request, patient_id, encounter_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    encounter = get_object_or_404(
        Encounter.objects.select_related("patient"),
        pk=encounter_id,
        patient=patient,
    )
    forms = {
        "assessment": NursingAssessmentForm,
        "fall_risk": NursingFallRiskAssessmentForm,
        "task": NursingTaskForm,
        "io": IntakeOutputForm,
        "handoff": NursingHandoffForm,
    }
    action = request.POST.get("nursing_action", "")
    bound_form = None

    if request.method == "POST" and not encounter.is_open:
        messages.error(
            request,
            "Nursing documentation can only be added to an open encounter.",
        )
        return redirect(
            "nursing:workspace",
            patient_id=patient.pk,
            encounter_id=encounter.pk,
        )

    if request.method == "POST" and action == "complete_task":
        task = get_object_or_404(
            NursingTask, pk=request.POST.get("task_id"), encounter=encounter
        )
        if not task.completed_at:
            task.completed_at = timezone.now()
            task.completed_by = request.user
            task.save(update_fields=["completed_at", "completed_by"])
            messages.success(request, "Nursing task completed.")
        return redirect(
            "nursing:workspace",
            patient_id=patient.pk,
            encounter_id=encounter.pk,
        )

    if request.method == "POST" and action in forms:
        form_kwargs = {"current_user": request.user} if action == "handoff" else {}
        bound_form = forms[action](request.POST, **form_kwargs)
        if bound_form.is_valid():
            if (
                action == "fall_risk"
                and NursingFallRiskAssessment.objects.filter(
                    encounter=encounter,
                    assessment_date=bound_form.cleaned_data["assessment_date"],
                    shift=bound_form.cleaned_data["shift"],
                ).exists()
            ):
                bound_form.add_error(
                    "shift",
                    (
                        "A fall-risk assessment already exists for this encounter, "
                        "date, and shift."
                    ),
                )
            if bound_form.errors:
                pass
            else:
                with transaction.atomic():
                    record = bound_form.save(commit=False)
                    record.patient = patient
                    record.encounter = encounter
                    record.recorded_by = request.user
                    if action == "fall_risk":
                        for field, value in score_assessment(
                            bound_form.cleaned_data
                        ).items():
                            setattr(record, field, value)
                    record.save()
                    if action == "fall_risk":
                        for risk_type, score, category, method, version in (
                            (
                                "Fall risk — Morse",
                                record.morse_score,
                                record.morse_level,
                                "Morse Fall Scale",
                                "standard",
                            ),
                            (
                                "Fall risk — Logistic",
                                record.logistic_probability * 100,
                                record.logistic_level,
                                "Logistic regression comparison",
                                "0.1-unvalidated",
                            ),
                            (
                                "Fall risk — XGBoost",
                                record.xgboost_probability * 100,
                                record.xgboost_level,
                                "Boosted-tree comparison",
                                "0.1-unvalidated",
                            ),
                        ):
                            RiskAssessment.objects.create(
                                patient=patient,
                                encounter=encounter,
                                risk_type=risk_type,
                                score=score,
                                category=category,
                                inputs={"nursing_fall_risk_assessment_id": record.pk},
                                method=method,
                                method_version=version,
                                calculated_by=request.user,
                            )
                        if (
                            record.overall_level
                            == NursingFallRiskAssessment.RiskLevel.HIGH
                        ):
                            rule, _ = ClinicalRule.objects.get_or_create(
                                code="inpatient-fall-risk-composite",
                                defaults={
                                    "name": "Inpatient fall risk — composite",
                                    "description": (
                                        "Per-shift fall-risk alert using Morse and "
                                        "development comparison models."
                                    ),
                                    "trigger_definition": {"overall_level": "high"},
                                    "recommendation": (
                                        "Initiate fall-prevention protocol. "
                                        "Individualize interventions. Communicate risk "
                                        "during handoff and reassess after change."
                                    ),
                                    "severity": ClinicalRule.Severity.HIGH,
                                    "evidence_reference": (
                                        "https://www.patientsafety.va.gov/docs/"
                                        "fallsToolkit/morse_falls_pocket_card.pdf"
                                    ),
                                    "owner": "Nursing and Clinical Safety",
                                    "created_by": request.user,
                                },
                            )
                            ClinicalAlert.objects.create(
                                rule=rule,
                                patient=patient,
                                encounter=encounter,
                                title="High fall risk identified",
                                message=(
                                    f"{record.get_shift_display()} assessment: Morse "
                                    f"{record.morse_score} "
                                    f"({record.get_morse_level_display()}), logistic "
                                    f"{record.logistic_probability:.0%}, XGBoost "
                                    "comparison "
                                    f"{record.xgboost_probability:.0%}."
                                ),
                                supporting_data={
                                    "assessment_id": record.pk,
                                    "comparison": record.model_comparison,
                                    "clinical_validation": (
                                        "Development models are not validated for "
                                        "autonomous clinical decisions."
                                    ),
                                },
                            )
                    if (
                        action == "assessment"
                        and record.assessment_type
                        == NursingAssessment.AssessmentType.DISCHARGE
                    ):
                        encounter.complete(user=request.user)
            if not bound_form.errors and (
                action == "assessment"
                and record.assessment_type == NursingAssessment.AssessmentType.DISCHARGE
            ):
                messages.success(
                    request,
                    "Discharge assessment recorded and encounter completed.",
                )
                return redirect("encounters:detail", pk=encounter.pk)

            if not bound_form.errors:
                messages.success(
                    request, f"Nursing {action.replace('_', ' ')} recorded."
                )
                return redirect(
                    "nursing:workspace",
                    patient_id=patient.pk,
                    encounter_id=encounter.pk,
                )

    io_today = IntakeOutputRecord.objects.filter(
        encounter=encounter, occurred_at__date=timezone.localdate()
    )
    totals = {
        "intake": io_today.filter(kind="intake").aggregate(total=Sum("volume_ml"))[
            "total"
        ]
        or 0,
        "output": io_today.filter(kind="output").aggregate(total=Sum("volume_ml"))[
            "total"
        ]
        or 0,
    }
    local_now = timezone.localtime()
    if 7 <= local_now.hour < 15:
        current_shift = NursingFallRiskAssessment.Shift.DAY
    elif 15 <= local_now.hour < 23:
        current_shift = NursingFallRiskAssessment.Shift.EVENING
    else:
        current_shift = NursingFallRiskAssessment.Shift.NIGHT
    fall_risk_due = not NursingFallRiskAssessment.objects.filter(
        encounter=encounter,
        assessment_date=local_now.date(),
        shift=current_shift,
    ).exists()
    context = {
        "active_primary_nav": "clinical",
        "active_clinical_module": "nursing",
        "active_clinical_section": "workspace",
        "selected_patient": patient,
        "active_encounter": encounter,
        "action": action,
        "assessment_form": (
            bound_form if action == "assessment" else NursingAssessmentForm()
        ),
        "fall_risk_form": (
            bound_form
            if action == "fall_risk"
            else NursingFallRiskAssessmentForm(
                initial={
                    "assessment_date": local_now.date(),
                    "shift": current_shift,
                }
            )
        ),
        "task_form": bound_form if action == "task" else NursingTaskForm(),
        "io_form": bound_form
        if action == "io"
        else IntakeOutputForm(
            initial={"occurred_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")}
        ),
        "handoff_form": (
            bound_form
            if action == "handoff"
            else NursingHandoffForm(current_user=request.user)
        ),
        "latest_assessment": NursingAssessment.objects.filter(
            encounter=encounter
        ).first(),
        "tasks": NursingTask.objects.filter(encounter=encounter)[:20],
        "io_records": IntakeOutputRecord.objects.filter(encounter=encounter)[:20],
        "latest_handoff": NursingHandoff.objects.filter(encounter=encounter).first(),
        "fall_risk_assessments": NursingFallRiskAssessment.objects.filter(
            encounter=encounter
        ).select_related("recorded_by")[:12],
        "latest_fall_risk": NursingFallRiskAssessment.objects.filter(
            encounter=encounter
        ).first(),
        "allergies": PatientAllergy.objects.filter(patient=patient).order_by(
            "status", "-severity", "substance"
        ),
        "fall_risk_due": fall_risk_due,
        "current_shift_label": dict(NursingFallRiskAssessment.Shift.choices)[
            current_shift
        ],
        "io_totals": totals,
        "initial_panel": (
            "fallRisk"
            if action == "fall_risk"
            else request.GET.get("panel", "overview")
        ),
    }
    if action != "assessment" and request.GET.get("assessment_type") in dict(
        NursingAssessment.AssessmentType.choices
    ):
        context["assessment_form"] = NursingAssessmentForm(
            initial={"assessment_type": request.GET["assessment_type"]}
        )
    return render(request, "nursing/workspace.html", context)
