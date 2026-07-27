from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.accounts.decorators import (
    active_staff_required,
    clinical_staff_required,
    role_required,
)
from apps.accounts.models import UserProfile


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

    return {
        "time_range": time_range,
        "time_range_label": TIME_RANGE_LABELS[time_range],
        "user_profile": profile,
        "user_role": profile.role if profile else "",
        "user_role_label": (
            profile.get_role_display()
            if profile
            else ""
        ),
        "user_facility": (
            profile.facility
            if profile
            else None
        ),
        "vitals_status": "Stable",
        "lab_status": "2 Abnormal",
        "medication_status": "8 Active",
        "io_balance": "+250 mL",
        "pain_score": "3 / 10",
        "clinical_alerts": [
            {
                "icon": "▲",
                "icon_class": "text-amber-500",
                "title": "Possible Drug Interaction",
                "message": (
                    "Lisinopril may increase potassium levels when "
                    "combined with spironolactone."
                ),
                "action_label": "Review",
            },
            {
                "icon": "△",
                "icon_class": "text-red-500",
                "title": "Sepsis Risk Alert",
                "message": (
                    "Medium risk score. Monitor vital signs and "
                    "laboratory results."
                ),
                "action_label": "",
            },
        ],
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
        UserProfile.Role.NURSE_PRACTITIONER: (
            "Advanced Practice Clinical Dashboard"
        ),
        UserProfile.Role.PHARMACIST: "Pharmacy Dashboard",
        UserProfile.Role.LAB_TECHNICIAN: "Laboratory Dashboard",
        UserProfile.Role.RADIOLOGY_TECHNICIAN: "Radiology Dashboard",
        UserProfile.Role.DATA_ANALYST: "Healthcare Analytics",
        UserProfile.Role.INFORMATICIST: "Nursing Informatics Dashboard",
        UserProfile.Role.BILLING_OFFICER: "Billing Dashboard",
        UserProfile.Role.RECEPTIONIST: "Front Desk Dashboard",
        UserProfile.Role.COMMUNITY_HEALTH_WORKER: (
            "Community Health Dashboard"
        ),
        UserProfile.Role.AUDITOR: "Audit Dashboard",
        UserProfile.Role.PATIENT: "Patient Portal",
    }

    return dashboard_titles.get(
        role,
        "EHR Dashboard",
    )