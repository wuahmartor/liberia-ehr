from django.urls import path

from . import views

app_name = "nursing"

urlpatterns = [
    path(
        "patient/<uuid:patient_id>/encounter/<uuid:encounter_id>/",
        views.workspace,
        name="workspace",
    ),
]
