



from .views import AdministrationDashboardView
from django.urls import path

from . import views


app_name = "administration"


urlpatterns = [
     path(

        "",

        AdministrationDashboardView.as_view(),

        name="dashboard",

    ),
]