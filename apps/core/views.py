from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.decorators import (
    active_staff_required,
    clinical_staff_required,
    role_required,
)
from apps.accounts.models import UserProfile
from apps.clinical_notes.models import ClinicalNote
from apps.diagnoses.models import PatientDiagnosis
from apps.encounters.models import Encounter
from apps.medications.models import MedicationAdministration
from apps.nursing.models import NursingAssessment, NursingTask
from apps.orders.models import MedicationOrder
from apps.patients.models import Patient
from apps.pharmacy.models import Medication, PharmacyReview
from apps.vitals.models import VitalObservation

TIME_RANGE_LABELS = {
    "24h": "Last 24 Hours",
    "48h": "Last 48 Hours",
    "7d": "Last 7 Days",
    "encounter": "Current Encounter",
}


def is_htmx_request(request):
    """
    Return True when the request was submitted through HTMX.
    """

    return request.headers.get("HX-Request") == "true"


def get_user_profile(request):
    """
    Safely retrieve the authenticated user's EHR profile.
    """

    if not request.user.is_authenticated:
        return None

    return getattr(request.user, "profile", None)


def get_clinical_dashboard_context(request):
    """
    Build shared context for the clinical dashboard.

    This function is used by both the full-page view and
    the HTMX partial view.
    """

    time_range = request.GET.get("time_range", "24h")

    if time_range not in TIME_RANGE_LABELS:
        time_range = "24h"

    profile = get_user_profile(request)
    now = timezone.now()
    window = {
        "24h": timedelta(hours=24),
        "48h": timedelta(hours=48),
        "7d": timedelta(days=7),
        "encounter": timedelta(hours=24),
    }[time_range]
    since = now - window
    open_statuses = (
        Encounter.EncounterStatus.PLANNED,
        Encounter.EncounterStatus.SCHEDULED,
        Encounter.EncounterStatus.ARRIVED,
        Encounter.EncounterStatus.TRIAGED,
        Encounter.EncounterStatus.IN_PROGRESS,
        Encounter.EncounterStatus.ON_HOLD,
    )
    encounters = Encounter.objects.select_related("patient", "attending_provider")
    recent_encounters = encounters.filter(start_datetime__gte=since)
    open_encounters = encounters.filter(is_active=True, status__in=open_statuses)
    active_orders = MedicationOrder.objects.filter(status=MedicationOrder.Status.ACTIVE)
    administrations = MedicationAdministration.objects.filter(
        administered_at__gte=since
    )
    vitals = VitalObservation.objects.active().filter(recorded_at__gte=since)
    assessments = NursingAssessment.objects.filter(recorded_at__gte=since)
    open_tasks = NursingTask.objects.filter(completed_at__isnull=True)
    encounter_mix = list(
        recent_encounters.values("encounter_type")
        .annotate(total=Count("pk"))
        .order_by("-total", "encounter_type")
    )
    type_labels = dict(Encounter.EncounterType.choices)
    for item in encounter_mix:
        item["label"] = type_labels.get(item["encounter_type"], item["encounter_type"])

    return {
        "time_range": time_range,
        "time_range_label": TIME_RANGE_LABELS[time_range],
        "user_profile": profile,
        "user_role": profile.role if profile else "",
        "user_role_label": (profile.get_role_display() if profile else ""),
        "user_facility": (profile.facility if profile else None),
        "generated_at": now,
        "registered_patients": Patient.objects.filter(is_active=True).count(),
        "open_encounter_count": open_encounters.count(),
        "new_encounter_count": recent_encounters.count(),
        "completed_encounter_count": encounters.filter(
            status=Encounter.EncounterStatus.COMPLETED, completed_at__gte=since
        ).count(),
        "active_diagnosis_count": PatientDiagnosis.objects.filter(
            clinical_status=PatientDiagnosis.DiagnosisStatus.ACTIVE
        ).count(),
        "vitals_count": vitals.count(),
        "patients_with_vitals": vitals.values("patient_id").distinct().count(),
        "high_pain_count": vitals.filter(pain_score__gte=7).count(),
        "active_medication_count": active_orders.count(),
        "meds_administered_count": administrations.filter(
            status=MedicationAdministration.Status.ADMINISTERED
        ).count(),
        "meds_not_given_count": administrations.exclude(
            status=MedicationAdministration.Status.ADMINISTERED
        ).count(),
        "pending_pharmacy_count": active_orders.filter(
            Q(pharmacy_review__isnull=True)
            | Q(pharmacy_review__status=PharmacyReview.Status.PENDING)
        ).count(),
        "low_stock_count": Medication.objects.low_stock().count(),
        "assessment_count": assessments.count(),
        "fall_risk_count": assessments.filter(fall_risk=True).count(),
        "pressure_risk_count": assessments.filter(pressure_injury_risk=True).count(),
        "open_nursing_task_count": open_tasks.count(),
        "overdue_nursing_task_count": open_tasks.filter(due_at__lt=now).count(),
        "signed_note_count": ClinicalNote.objects.filter(
            status=ClinicalNote.Status.SIGNED, signed_at__gte=since
        ).count(),
        "draft_note_count": ClinicalNote.objects.filter(
            status=ClinicalNote.Status.DRAFT
        ).count(),
        "recent_encounters": open_encounters.order_by("-start_datetime")[:8],
        "encounter_mix": encounter_mix,
    }


def get_base_navigation_context(
    active_primary_nav="clinical",
    active_secondary_nav="patients",
):
    """
    Return navigation state used by the two-row EHR navigation.
    """

    return {
        "active_primary_nav": active_primary_nav,
        "active_secondary_nav": active_secondary_nav,
    }


@login_required
@active_staff_required
@require_GET
def dashboard(request):
    """
    Main role-aware EHR dashboard.

    Clinical users are currently sent to the clinical overview.
    Other role dashboards can be expanded as their modules are built.
    """

    profile = get_user_profile(request)

    context = get_clinical_dashboard_context(request)
    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="patients",
        )
    )

    context["dashboard_title"] = "Clinical Overview"

    if profile:
        context["dashboard_title"] = get_dashboard_title(profile.role)

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@clinical_staff_required
@require_GET
def clinical_overview(request):
    """
    Display the full clinical overview page.

    Access is limited to authenticated clinical staff.
    """

    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="patients",
        )
    )

    context["dashboard_title"] = "Clinical Overview"

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@clinical_staff_required
@require_GET
def clinical_dashboard_partial(request):
    """
    Return only the clinical dashboard workspace for HTMX requests.

    A normal browser request is redirected to the complete clinical page.
    """

    if not is_htmx_request(request):
        return clinical_overview(request)

    context = get_clinical_dashboard_context(request)

    return render(
        request,
        "core/partials/clinical_dashboard.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.DATA_ANALYST,
    UserProfile.Role.INFORMATICIST,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def analytics_dashboard(request):
    """
    Healthcare analytics and nursing informatics workspace.

    This temporarily uses the clinical overview template until
    a dedicated analytics template is created.
    """

    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="analytics",
            active_secondary_nav="clinical-analytics",
        )
    )

    context.update(
        {
            "dashboard_title": "Healthcare Analytics",
            "dashboard_mode": "analytics",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def administration_dashboard(request):
    """
    Administrative dashboard for system and facility administrators.
    """

    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="administration",
            active_secondary_nav="facilities",
        )
    )

    context.update(
        {
            "dashboard_title": "EHR Administration",
            "dashboard_mode": "administration",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.PHARMACIST,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def pharmacy_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="pharmacy",
        )
    )

    context.update(
        {
            "dashboard_title": "Pharmacy Dashboard",
            "dashboard_mode": "pharmacy",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.LAB_TECHNICIAN,
    UserProfile.Role.PHYSICIAN,
    UserProfile.Role.NURSE_PRACTITIONER,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def laboratory_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="laboratory",
        )
    )

    context.update(
        {
            "dashboard_title": "Laboratory Dashboard",
            "dashboard_mode": "laboratory",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.RADIOLOGY_TECHNICIAN,
    UserProfile.Role.PHYSICIAN,
    UserProfile.Role.NURSE_PRACTITIONER,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def radiology_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="radiology",
        )
    )

    context.update(
        {
            "dashboard_title": "Radiology Dashboard",
            "dashboard_mode": "radiology",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.BILLING_OFFICER,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def billing_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="financial",
            active_secondary_nav="billing",
        )
    )

    context.update(
        {
            "dashboard_title": "Billing Dashboard",
            "dashboard_mode": "billing",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.RECEPTIONIST,
    UserProfile.Role.SYSTEM_ADMIN,
    UserProfile.Role.FACILITY_ADMIN,
)
@require_GET
def front_desk_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="clinical",
            active_secondary_nav="front-desk",
        )
    )

    context.update(
        {
            "dashboard_title": "Front Desk Dashboard",
            "dashboard_mode": "front-desk",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(
    UserProfile.Role.AUDITOR,
    UserProfile.Role.SYSTEM_ADMIN,
)
@require_GET
def audit_dashboard(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="administration",
            active_secondary_nav="audit",
        )
    )

    context.update(
        {
            "dashboard_title": "Audit Dashboard",
            "dashboard_mode": "audit",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@role_required(UserProfile.Role.PATIENT)
@require_GET
def patient_portal(request):
    """
    Temporary patient portal landing page.

    A dedicated patient portal template should replace this template
    when the patient-facing module is developed.
    """

    context = get_clinical_dashboard_context(request)

    context.update(
        get_base_navigation_context(
            active_primary_nav="patient-portal",
            active_secondary_nav="overview",
        )
    )

    context.update(
        {
            "dashboard_title": "Patient Portal",
            "dashboard_mode": "patient-portal",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


@login_required
@active_staff_required
def htmx_access_required(request):
    """
    Optional endpoint for checking an authenticated HTMX session.

    This may be used by the frontend before loading protected workspace
    components.
    """

    if not is_htmx_request(request):
        return HttpResponse(status=400)

    return HttpResponse(status=204)


def get_dashboard_title(role):
    """
    Return a dashboard title matching the user's assigned role.
    """

    dashboard_titles = {
        UserProfile.Role.SYSTEM_ADMIN: "System Administration",
        UserProfile.Role.FACILITY_ADMIN: "Facility Administration",
        UserProfile.Role.PHYSICIAN: "Physician Clinical Dashboard",
        UserProfile.Role.NURSE: "Nursing Clinical Dashboard",
        UserProfile.Role.NURSE_PRACTITIONER: ("Advanced Practice Clinical Dashboard"),
        UserProfile.Role.PHARMACIST: "Pharmacy Dashboard",
        UserProfile.Role.LAB_TECHNICIAN: "Laboratory Dashboard",
        UserProfile.Role.RADIOLOGY_TECHNICIAN: "Radiology Dashboard",
        UserProfile.Role.DATA_ANALYST: "Healthcare Analytics",
        UserProfile.Role.INFORMATICIST: "Nursing Informatics Dashboard",
        UserProfile.Role.BILLING_OFFICER: "Billing Dashboard",
        UserProfile.Role.RECEPTIONIST: "Front Desk Dashboard",
        UserProfile.Role.COMMUNITY_HEALTH_WORKER: ("Community Health Dashboard"),
        UserProfile.Role.AUDITOR: "Audit Dashboard",
        UserProfile.Role.PATIENT: "Patient Portal",
    }

    return dashboard_titles.get(
        role,
        "EHR Dashboard",
    )
