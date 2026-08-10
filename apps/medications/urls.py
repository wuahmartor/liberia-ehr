from django.urls import path

from . import views


app_name = "medications"


urlpatterns = [
    path(
        "",
        views.medication_list,
        name="list",
    ),
    path(
        "patient/<uuid:patient_id>/",
        views.patient_medication_list,
        name="patient-list",
    ),
    path(
        "encounter/<uuid:encounter_id>/mar/",
        views.medication_administration_record,
        name="mar",
    ),
]
