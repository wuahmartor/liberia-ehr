from django.urls import path

from . import views


app_name = "patients"


urlpatterns = [
    # ========================================================
    # PATIENT LIST AND SEARCH
    # ========================================================
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

    # ========================================================
    # PATIENT CREATE
    # ========================================================
    path(
        "new/",
        views.PatientCreateView.as_view(),
        name="create",
    ),

    # ========================================================
    # PATIENT DETAIL AND WORKSPACE
    # ========================================================
    path(
        "<uuid:patient_id>/",
        views.patient_detail,
        name="detail",
    ),
    path(
        "<uuid:patient_id>/overview/",
        views.patient_overview,
        name="overview",
    ),
    path(
        "<uuid:patient_id>/sidebar/",
        views.patient_sidebar,
        name="sidebar",
    ),

    # ========================================================
    # PATIENT UPDATE AND STATUS
    # ========================================================
    path(
        "<uuid:patient_id>/edit/",
        views.PatientUpdateView.as_view(),
        name="update",
    ),
    path(
        "<uuid:patient_id>/archive/",
        views.PatientArchiveView.as_view(),
        name="archive",
    ),
    path(
        "<uuid:patient_id>/restore/",
        views.PatientRestoreView.as_view(),
        name="restore",
    ),

    # Backward-compatible delete URL.
    # This now performs soft archival rather than hard deletion.
    path(
        "<uuid:patient_id>/delete/",
        views.PatientArchiveView.as_view(),
        name="delete",
    ),

    # ========================================================
    # PATIENT MERGE
    # ========================================================
    path(
        "<uuid:patient_id>/merge/",
        views.patient_merge_review,
        name="merge-review",
    ),

    # ========================================================
    # PATIENT FLAG ACKNOWLEDGMENT
    # ========================================================
    path(
        "<uuid:patient_id>/flags/"
        "<int:flag_id>/acknowledge/",
        views.patient_flag_acknowledge,
        name="flag-acknowledge",
    ),

    # ========================================================
    # CHILD RECORD LISTS
    # ========================================================
    path(
        "<uuid:patient_id>/records/<str:kind>/",
        views.patient_child_list,
        name="child-list",
    ),

    # ========================================================
    # CHILD RECORD CREATE
    # ========================================================
    path(
        "<uuid:patient_id>/records/<str:kind>/new/",
        views.patient_child_create,
        name="child-create",
    ),

    # ========================================================
    # CHILD RECORD UPDATE
    # Child records currently use integer primary keys.
    # ========================================================
    path(
        "<uuid:patient_id>/records/<str:kind>/"
        "<int:record_id>/edit/",
        views.patient_child_update,
        name="child-update",
    ),

    # ========================================================
    # CHILD RECORD DELETE
    # ========================================================
    path(
        "<uuid:patient_id>/records/<str:kind>/"
        "<int:record_id>/delete/",
        views.patient_child_delete,
        name="child-delete",
    ),
]