"""
Liberia EHR Vitals URL Configuration

File:
apps/vitals/urls.py

Purpose:
- Route vital-sign list, create, detail, update, and audit pages.
- Provide patient-specific and encounter-specific vital history.
"""

from django.urls import path

from . import views


app_name = "vitals"


urlpatterns = [
    # =========================================================
    # VITALS INDEX AND LIST
    # =========================================================
    path(
        "",
        views.VitalListView.as_view(),
        name="index",
    ),
    path(
        "list/",
        views.VitalListView.as_view(),
        name="list",
    ),

    # =========================================================
    # CREATE
    # =========================================================
    path(
        "create/",
        views.VitalCreateView.as_view(),
        name="create",
    ),

    # =========================================================
    # PATIENT AND ENCOUNTER HISTORY
    # These must appear before the generic UUID detail route.
    # =========================================================
    path(
        "patient/<uuid:patient_id>/",
        views.PatientVitalHistoryView.as_view(),
        name="patient_history",
    ),
    path(
        "encounter/<uuid:encounter_id>/",
        views.EncounterVitalListView.as_view(),
        name="encounter_list",
    ),

    # =========================================================
    # DETAIL AND RECORD ACTIONS
    # =========================================================
    path(
        "<uuid:pk>/",
        views.VitalDetailView.as_view(),
        name="detail",
    ),
    path(
        "<uuid:pk>/update/",
        views.VitalUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:pk>/entered-in-error/",
        views.VitalEnteredInErrorView.as_view(),
        name="entered_in_error",
    ),
]