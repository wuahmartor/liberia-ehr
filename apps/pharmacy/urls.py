from django.urls import path

from . import views


app_name = "pharmacy"


urlpatterns = [

    # ============================================================
    # PHARMACY DASHBOARD
    # ============================================================

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # ============================================================
    # PHARMACY CLINICAL WORKFLOW
    # ============================================================

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
        "interactions/",
        views.interactions,
        name="interactions",
    ),

    path(
        "rejected/",
        views.rejected,
        name="rejected",
    ),

    # ============================================================
    # PHARMACY INVENTORY
    # ============================================================

    path(
        "inventory/",
        views.inventory,
        name="inventory",
    ),

    # ============================================================
    # MEDICATION FORMULARY / CATALOG
    # ============================================================

    path(
        "medications/",
        views.medication_catalog,
        name="medication-catalog",
    ),

    path(
        "medications/new/",
        views.MedicationCatalogCreateView.as_view(),
        name="medication-catalog-create",
    ),

    path(
        "medications/<int:pk>/edit/",
        views.MedicationCatalogUpdateView.as_view(),
        name="medication-catalog-update",
    ),

    path(
        "medications/<int:pk>/delete/",
        views.MedicationCatalogDeleteView.as_view(),
        name="medication-catalog-delete",
    ),

    # ============================================================
    # LOCAL MEDICATION API
    # ============================================================

    path(
        "api/medications/",
        views.medication_list_api,
        name="medication-list-api",
    ),

    # ============================================================
    # RXNORM / EXTERNAL MEDICATION TERMINOLOGY API
    # ============================================================

    path(
        "api/rxnorm/search/",
        views.us_medication_search_api,
        name="rxnorm-search-api",
    ),

    path(
        "api/rxnorm/import/",
        views.import_us_medication,
        name="rxnorm-import-api",
    ),
]