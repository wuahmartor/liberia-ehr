from django.urls import path

from . import views

app_name = "decision_support"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/<uuid:alert_id>/", views.alert_detail, name="alert-detail"),
    path("alerts/<uuid:alert_id>/action/", views.alert_action, name="alert-action"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("risk/", views.risk_scores, name="risk"),
    path("rules/", views.rules, name="rules"),
    path("rules/new/", views.rule_form, name="rule-create"),
    path("rules/<int:rule_id>/", views.rule_form, name="rule-update"),
]
