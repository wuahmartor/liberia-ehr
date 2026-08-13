from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("diagnoses/", include("apps.diagnoses.urls")),
    path("ai-cds/", include("apps.decision_support.urls")),
    path("nursing/", include("apps.nursing.urls")),
    path("admin/", admin.site.urls),

    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),


    path(
        "patients/",
        include("apps.patients.urls"),
    ),

    path(
        "facilities/",
        include("apps.facilities.urls"),
    ),

    # ============================================================

    # ENCOUNTERS

    # ============================================================

    path(

        "encounters/",

        include("apps.encounters.urls"),

    ),

    # Django password reset URLs
    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),

    path("pharmacy/", include("apps.pharmacy.urls"),
         ),

    path("administration/", include("apps.administration.urls"),
         ),

    path(
            "",
            include("apps.core.urls"),
        ),

    path(
        "analytics/", include("apps.analytics.urls"),
    ),
    path(

        "vitals/",

            include("apps.vitals.urls"),),

    path(
    "clinical-notes/",
    include("apps.clinical_notes.urls"),
    ),

    path(
        "medications/",
        include("apps.medications.urls"),
    ),
    path(
        "orders/",
        include("apps.orders.urls"),
    ),

]
