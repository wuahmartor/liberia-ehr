from django.contrib import admin
from django.urls import include, path


urlpatterns = [
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
        "analytics/", include("apps.analytics.urls")
    ),
      path(

        "vitals/",

        include("apps.vitals.urls"),)

    
]