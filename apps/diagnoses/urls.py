from django.urls import path

from . import views

app_name = "diagnoses"
urlpatterns = [
    path("", views.diagnosis_list, name="list"),
    path("patient/<uuid:patient_id>/", views.diagnosis_list, name="patient-list"),
    path("patient/<uuid:patient_id>/new/", views.diagnosis_create, name="create"),
    path("search/icd10/", views.icd10_search, name="icd10-search"),
    path("<uuid:diagnosis_id>/", views.diagnosis_detail, name="detail"),
    path("<uuid:diagnosis_id>/edit/", views.diagnosis_update, name="update"),
    path(
        "<uuid:diagnosis_id>/entered-in-error/",
        views.diagnosis_entered_in_error,
        name="entered-in-error",
    ),
    path(
        "procedures/patient/<uuid:patient_id>/",
        views.procedure_list,
        name="procedure-list",
    ),
    path(
        "procedures/patient/<uuid:patient_id>/new/",
        views.procedure_create,
        name="procedure-create",
    ),
    path("procedures/search/cpt/", views.cpt_search, name="cpt-search"),
]
