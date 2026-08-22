from django.urls import path
from . import views

app_name = "laboratories"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("patient/<uuid:patient_id>/", views.patient_results, name="patient-results"),
    path("patient/<uuid:patient_id>/encounter/<uuid:encounter_id>/order/", views.create_order, name="create-order"),
    path("orders/<uuid:order_id>/", views.order_detail, name="order-detail"),
    path("orders/<uuid:order_id>/collect/", views.collect_specimen, name="collect-specimen"),
    path("items/<uuid:item_id>/result/", views.enter_result, name="enter-result"),
    path("results/<uuid:result_id>/verify/", views.verify_result, name="verify-result"),
    path("results/<uuid:result_id>/acknowledge-critical/", views.acknowledge_critical, name="acknowledge-critical"),
    path("results/<uuid:result_id>/decision-support.json", views.result_json, name="result-json"),
]
