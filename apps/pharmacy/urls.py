from django.urls import path

from . import views

app_name = "pharmacy"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("queue/", views.queue, name="queue"),
    path("review/", views.pending_review, name="pending-review"),
    path("review/<uuid:order_id>/", views.review_order, name="review-order"),
    path("verified/", views.verified, name="verified"),
    path("dispensing/", views.dispensing, name="dispensing"),
    path("dispensing/<uuid:order_id>/", views.dispense_order, name="dispense-order"),
    path("interactions/", views.interactions, name="interactions"),
    path("rejected/", views.rejected, name="rejected"),
    path("inventory/", views.inventory, name="inventory"),
    path(
        "formulary/",
        views.MedicationCatalogListView.as_view(),
        name="medication-catalog",
    ),
    path(
        "formulary/new/",
        views.MedicationCatalogCreateView.as_view(),
        name="medication-catalog-create",
    ),
    path(
        "formulary/<int:pk>/edit/",
        views.MedicationCatalogUpdateView.as_view(),
        name="medication-catalog-update",
    ),
    path(
        "formulary/<int:pk>/delete/",
        views.MedicationCatalogDeleteView.as_view(),
        name="medication-catalog-delete",
    ),
    # Backward-compatible catalog route names.
    path(
        "medications/",
        views.MedicationCatalogListView.as_view(),
        name="medication-list",
    ),
    path(
        "medications/new/",
        views.MedicationCatalogCreateView.as_view(),
        name="medication-create",
    ),
    path(
        "medications/<int:pk>/edit/",
        views.MedicationCatalogUpdateView.as_view(),
        name="medication-update",
    ),
    path(
        "medications/<int:pk>/delete/",
        views.MedicationCatalogDeleteView.as_view(),
        name="medication-delete",
    ),
    path("api/medications/", views.medication_list_api, name="medication-list-api"),
    path(
        "api/us-medications/",
        views.us_medication_search_api,
        name="us-medication-search-api",
    ),
    path(
        "api/us-medications/import/",
        views.us_medication_import_api,
        name="us-medication-import-api",
    ),
    path(
        "api/rxnorm/search/", views.us_medication_search_api, name="rxnorm-search-api"
    ),
    path(
        "api/rxnorm/import/", views.us_medication_import_api, name="rxnorm-import-api"
    ),
]
