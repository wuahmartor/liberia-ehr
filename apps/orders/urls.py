from django.urls import path

from . import views


app_name = "orders"


urlpatterns = [
    path(
        "list/",
        views.order_list,
        name="list",
    ),
    path(
        "patient/<uuid:patient_id>/encounter/<uuid:encounter_id>/medication-order/",
        views.medication_order,
        name="medication-order",
    ),
]
