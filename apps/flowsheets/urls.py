from django.urls import path

from . import views

app_name = "flowsheets"

urlpatterns = [
    path("", views.index, name="index"),
    path("patient/<uuid:patient_id>/", views.patient_flowsheet, name="patient"),
    path("patient/<uuid:patient_id>/<slug:definition_slug>/", views.patient_flowsheet, name="patient-definition"),
    path("encounter/<uuid:encounter_id>/", views.encounter_flowsheet, name="encounter"),
    path("patient/<uuid:patient_id>/new/<uuid:definition_id>/", views.create_entry, name="create"),
    path("entries/<uuid:entry_id>/", views.entry_detail, name="detail"),
    path("entries/<uuid:entry_id>/correct/", views.correct_entry, name="correct"),
    path("entries/<uuid:entry_id>/entered-in-error/", views.entered_in_error, name="entered-in-error"),
]
