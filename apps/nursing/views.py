from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.encounters.models import Encounter
from apps.patients.models import Patient

from .forms import (
    IntakeOutputForm,
    NursingAssessmentForm,
    NursingHandoffForm,
    NursingTaskForm,
)
from .models import (
    IntakeOutputRecord,
    NursingAssessment,
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
            with transaction.atomic():
                record = bound_form.save(commit=False)
                record.patient = patient
                record.encounter = encounter
                record.recorded_by = request.user
                record.save()
                if (
                    action == "assessment"
                    and record.assessment_type
                    == NursingAssessment.AssessmentType.DISCHARGE
                ):
                    encounter.complete(user=request.user)

            if (
                action == "assessment"
                and record.assessment_type == NursingAssessment.AssessmentType.DISCHARGE
            ):
                messages.success(
                    request,
                    "Discharge assessment recorded and encounter completed.",
                )
                return redirect("encounters:detail", pk=encounter.pk)

            messages.success(request, f"Nursing {action} recorded.")
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
    context = {
        "active_primary_nav": "clinical",
        "active_clinical_module": "nursing",
        "active_clinical_section": "workspace",
        "selected_patient": patient,
        "active_encounter": encounter,
        "assessment_form": (
            bound_form if action == "assessment" else NursingAssessmentForm()
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
        "io_totals": totals,
        "initial_panel": request.GET.get("panel", "overview"),
    }
    if action != "assessment" and request.GET.get("assessment_type") in dict(
        NursingAssessment.AssessmentType.choices
    ):
        context["assessment_form"] = NursingAssessmentForm(
            initial={"assessment_type": request.GET["assessment_type"]}
        )
    return render(request, "nursing/workspace.html", context)
