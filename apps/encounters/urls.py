from django.urls import path

from .views import (
    EncounterCancelView,
    EncounterCompleteView,
    EncounterCreateView,
    EncounterDeleteView,
    EncounterDetailView,
    EncounterListView,
    EncounterUpdateView,
)


app_name = "encounters"


urlpatterns = [
    path(
        "",
        EncounterListView.as_view(),
        name="list",
    ),

    path(
        "create/",
        EncounterCreateView.as_view(),
        name="create",
    ),

    path(
        "<uuid:pk>/",
        EncounterDetailView.as_view(),
        name="detail",
    ),

    path(
        "<uuid:pk>/update/",
        EncounterUpdateView.as_view(),
        name="update",
    ),

    path(
        "<uuid:pk>/complete/",
        EncounterCompleteView.as_view(),
        name="complete",
    ),

    path(
        "<uuid:pk>/cancel/",
        EncounterCancelView.as_view(),
        name="cancel",
    ),

    path(
        "<uuid:pk>/delete/",
        EncounterDeleteView.as_view(),
        name="delete",
    ),
]