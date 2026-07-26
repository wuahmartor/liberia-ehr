from django.urls import path

from . import views


app_name = "core"


urlpatterns = [
    path(
        "",
        views.clinical_overview,
        name="dashboard",
    ),
    path(
        "clinical-dashboard/",
        views.clinical_dashboard_partial,
        name="clinical-dashboard-partial",
    ),
]