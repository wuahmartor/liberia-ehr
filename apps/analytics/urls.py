from django.urls import path

from . import views


app_name = "analytics"


urlpatterns = [
    path(
        "",
        views.analytics_dashboard,
        name="dashboard",
    ),
    path(
        "clinical/",
        views.clinical_dashboard,
        name="clinical",
    ),
    path(
        "nursing/",
        views.nursing_dashboard,
        name="nursing",
    ),
    path(
        "operations/",
        views.operations_dashboard,
        name="operations",
    ),
    path(
        "quality/",
        views.quality_dashboard,
        name="quality",
    ),
    path(
        "population-health/",
        views.surveillance_dashboard,
        name="population",
    ),
    path(
        "patient-outcomes/",
        views.patient_outcomes,
        name="patient_outcomes",
    ),
]