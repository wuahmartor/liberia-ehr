from django.urls import path

from . import views

app_name = "inventory"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("items/", views.item_list, name="item-list"),
    path("items/new/", views.item_create, name="item-create"),
    path("items/<uuid:item_id>/", views.item_detail, name="item-detail"),
    path("receiving/new/", views.lot_create, name="lot-create"),
    path("transactions/", views.transaction_list, name="transaction-list"),
    path("transactions/new/", views.transaction_create, name="transaction-create"),
    path("equipment/", views.equipment, name="equipment"),
    path("analytics/", views.analytics, name="analytics"),
]
