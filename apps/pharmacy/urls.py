
from django.urls import path

from . import views


app_name = "pharmacy"


urlpatterns = [
    path(
        "",
        views.dashboard,
        name="dashboard",
    ),
    path(
        "queue/",
        views.queue,
        name="queue",
    ),
    path(
        "pending-review/",
        views.pending_review,
        name="pending-review",
    ),
    path(
        "verified/",
        views.verified,
        name="verified",
    ),
    path(
        "dispensing/",
        views.dispensing,
        name="dispensing",
    ),
    path(
        "inventory/",
        views.inventory,
        name="inventory",
    ),
    path(
        "medication-catalog/",
        views.medication_catalog,
        name="medication-catalog",
    ),
    path(
        "medication-catalog/new/",
        views.MedicationCatalogCreateView.as_view(),
        name="medication-catalog-create",
    ),
    path(
        "medication-catalog/<int:pk>/edit/",
        views.MedicationCatalogUpdateView.as_view(),
        name="medication-catalog-update",
    ),
    path(
        "medication-catalog/<int:pk>/delete/",
        views.MedicationCatalogDeleteView.as_view(),
        name="medication-catalog-delete",
    ),
    path(
        "api/medications/",
        views.medication_list_api,
        name="medication-list-api",
    ),
    path(
        "interactions/",
        views.interactions,
        name="interactions",
    ),
    path(
        "rejected/",
        views.rejected,
        name="rejected",
    ),
]