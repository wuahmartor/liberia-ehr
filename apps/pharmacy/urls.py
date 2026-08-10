from django.urls import path

from . import views

app_name = "pharmacy"

urlpatterns = [

    # ========================================================

    # PHARMACY WORKSPACE

    # ========================================================

    path(

        "",

        views.dashboard,

        name="dashboard",

    ),

    # ========================================================

    # MEDICATION CATALOG

    # ========================================================

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

    # ========================================================

    # MEDICATION APIs

    # ========================================================

    path(

        "api/medications/",

        views.medication_list_api,

        name="medication-list-api",

    ),

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

]