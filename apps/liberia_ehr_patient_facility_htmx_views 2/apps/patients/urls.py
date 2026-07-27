from django.urls import path

from . import views


app_name = "patients"


urlpatterns = [
    path(
        "",
        views.patient_list,
        name="list",
    ),
    path(
        "search/",
        views.patient_search,
        name="search-results",
    ),
    path(
        "new/",
        views.PatientCreateView.as_view(),
        name="create",
    ),
    path(
        "<uuid:patient_id>/",
        views.patient_detail,
        name="detail",
    ),
    path(
        "<uuid:patient_id>/sidebar/",
        views.patient_sidebar,
        name="sidebar",
    ),
    path(
        "<uuid:patient_id>/edit/",
        views.PatientUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:patient_id>/delete/",
        views.PatientDeleteView.as_view(),
        name="delete",
    ),
    path(
        "<uuid:patient_id>/<str:kind>/",
        views.patient_child_list,
        name="child-list",
    ),
    path(
        "<uuid:patient_id>/<str:kind>/new/",
        views.patient_child_create,
        name="child-create",
    ),
    path(
        "<uuid:patient_id>/<str:kind>/<uuid:record_id>/edit/",
        views.patient_child_update,
        name="child-update",
    ),
    path(
        "<uuid:patient_id>/<str:kind>/<uuid:record_id>/delete/",
        views.patient_child_delete,
        name="child-delete",
    ),
]
