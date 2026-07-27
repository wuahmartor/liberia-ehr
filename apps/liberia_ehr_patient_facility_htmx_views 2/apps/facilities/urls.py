from django.urls import path

from . import views


app_name = "facilities"


urlpatterns = [
    path(
        "",
        views.facility_list,
        name="list",
    ),
    path(
        "search/",
        views.facility_search,
        name="search-results",
    ),
    path(
        "new/",
        views.FacilityCreateView.as_view(),
        name="create",
    ),
    path(
        "<uuid:facility_id>/",
        views.facility_detail,
        name="detail",
    ),
    path(
        "<uuid:facility_id>/edit/",
        views.FacilityUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:facility_id>/delete/",
        views.FacilityDeleteView.as_view(),
        name="delete",
    ),
    path(
        "<uuid:facility_id>/<str:kind>/",
        views.facility_child_list,
        name="child-list",
    ),
    path(
        "<uuid:facility_id>/<str:kind>/new/",
        views.facility_child_create,
        name="child-create",
    ),
    path(
        "<uuid:facility_id>/<str:kind>/<uuid:record_id>/edit/",
        views.facility_child_update,
        name="child-update",
    ),
    path(
        "<uuid:facility_id>/<str:kind>/<uuid:record_id>/delete/",
        views.facility_child_delete,
        name="child-delete",
    ),
    path(
        "<uuid:facility_id>/options/departments/",
        views.departments_for_facility,
        name="department-options",
    ),
    path(
        "<uuid:facility_id>/options/units/",
        views.units_for_facility,
        name="unit-options",
    ),
    path(
        "units/<uuid:unit_id>/options/rooms/",
        views.rooms_for_unit,
        name="room-options",
    ),
]
