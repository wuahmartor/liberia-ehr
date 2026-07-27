from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),

    path(
        "accounts/",
        include("apps.accounts.urls"),
    ),

    path(
        "",
        include("apps.core.urls"),
    ),

    path(
        "patients/",
        include("apps.patients.urls"),
    ),

    path(
        "facilities/",
        include("apps.facilities.urls"),
    ),

    # Django password reset URLs
    path(
        "accounts/",
        include("django.contrib.auth.urls"),
    ),
]