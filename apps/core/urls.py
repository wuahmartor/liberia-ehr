from django.urls import path

from . import views


app_name = "core"


urlpatterns = [
    # Main authenticated dashboard
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # Clinical workspace
    path(
        "clinical/",
        views.clinical_overview,
        name="clinical_dashboard",
    ),
    path(
        "clinical/dashboard/",
        views.clinical_dashboard_partial,
        name="clinical_dashboard_partial",
    ),

    # Analytics and informatics
    path(
        "analytics/",
        views.analytics_dashboard,
        name="analytics_dashboard",
    ),

    # Department dashboards
    path(
        "pharmacy/",
        views.pharmacy_dashboard,
        name="pharmacy_dashboard",
    ),
    path(
        "laboratory/",
        views.laboratory_dashboard,
        name="laboratory_dashboard",
    ),
    path(
        "radiology/",
        views.radiology_dashboard,
        name="radiology_dashboard",
    ),
    path(
        "billing/",
        views.billing_dashboard,
        name="billing_dashboard",
    ),
    path(
        "front-desk/",
        views.front_desk_dashboard,
        name="front_desk_dashboard",
    ),
    path(
        "audit/",
        views.audit_dashboard,
        name="audit_dashboard",
    ),

    # Patient-facing dashboard
    path(
        "patient-portal/",
        views.patient_portal,
        name="patient_portal",
    ),

    # HTMX authentication/session check
    path(
        "session/check/",
        views.htmx_access_required,
        name="htmx_access_required",
    ),
]