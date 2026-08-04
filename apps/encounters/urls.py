"""
Liberia EHR Encounter URLs

File:
apps/encounters/urls.py
"""

from django.urls import path

from .views import (
    EncounterCancelView,
    EncounterCompleteView,
    EncounterCreateView,
    EncounterDeleteView,
    EncounterDetailView,
    EncounterEnteredInErrorView,
    EncounterListView,
    EncounterUpdateView,
)


app_name = "encounters"


urlpatterns = [
    # =================================================================
    # ENCOUNTER LIST
    # =================================================================

    path(
        "",
        EncounterListView.as_view(),
        name="list",
    ),

    # =================================================================
    # CREATE ENCOUNTER
    # =================================================================

    path(
        "create/",
        EncounterCreateView.as_view(),
        name="create",
    ),

    # =================================================================
    # ENCOUNTER DETAIL
    # =================================================================

    path(
        "<uuid:pk>/",
        EncounterDetailView.as_view(),
        name="detail",
    ),

    # =================================================================
    # UPDATE ENCOUNTER
    # =================================================================

    path(
        "<uuid:pk>/update/",
        EncounterUpdateView.as_view(),
        name="update",
    ),

    # =================================================================
    # COMPLETE ENCOUNTER
    # =================================================================

    path(
        "<uuid:pk>/complete/",
        EncounterCompleteView.as_view(),
        name="complete",
    ),

    # =================================================================
    # CANCEL ENCOUNTER
    # =================================================================

    path(
        "<uuid:pk>/cancel/",
        EncounterCancelView.as_view(),
        name="cancel",
    ),

    # =================================================================
    # ENTERED IN ERROR
    # =================================================================

    path(
        "<uuid:pk>/entered-in-error/",
        EncounterEnteredInErrorView.as_view(),
        name="entered_in_error",
    ),

    # =================================================================
    # DELETE ENCOUNTER
    # =================================================================

    path(
        "<uuid:pk>/delete/",
        EncounterDeleteView.as_view(),
        name="delete",
    ),
]