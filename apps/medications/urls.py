from django.urls import path

from . import views


app_name = "medications"


urlpatterns = [

    path(
        "mar/shift/",
        views.shift_mar,
        name="shift-mar",
    ),

    # ============================================================
    # GLOBAL MEDICATION ACTIVITY
    # ============================================================

    path(
        "",
        views.medication_list,
        name="list",
    ),

    # ============================================================
    # PATIENT MEDICATION RECORD
    # ============================================================

    path(
        "patient/<uuid:patient_id>/",
        views.patient_medication_list,
        name="patient-list",
    ),

    # ============================================================
    # MEDICATION RECONCILIATION
    # ============================================================

    path(
        "patient/<uuid:patient_id>/reconciliation/",
        views.reconciliation,
        name="reconciliation",
    ),

    # ============================================================
    # MEDICATION ADMINISTRATION RECORD
    # ============================================================

    path(
        "encounter/<uuid:encounter_id>/mar/",
        views.medication_administration_record,
        name="mar",
    ),
]
