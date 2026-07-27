

from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [
    path(
        "login/",
        views.login_view,
        name="login",
    ),
    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),
    path(
        "profile/",
        views.profile_view,
        name="profile",
    ),
    path(
        "access-denied/",
        views.access_denied_view,
        name="access_denied",
    ),
]