
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