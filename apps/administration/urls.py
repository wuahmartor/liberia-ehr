"""
============================================================
ADMINISTRATION URL CONFIGURATION

File:
apps/administration/urls.py

Purpose:
- Route Administration dashboards and scheduling workflows.
============================================================
"""

from django.urls import path

from . import views

app_name = "administration"


urlpatterns = [
    # ========================================================
    # ADMINISTRATION DASHBOARD
    # ========================================================
    path(
        "",
        views.AdministrationDashboardView.as_view(),
        name="dashboard",
    ),
    # ========================================================
    # SCHEDULING
    # ========================================================
    path(
        "scheduling/",
        views.SchedulingListView.as_view(),
        name="scheduling",
    ),
    path(
        "scheduling/create/",
        views.SchedulingCreateView.as_view(),
        name="scheduling_create",
    ),
    path(
        "scheduling/<uuid:appointment_id>/",
        views.SchedulingDetailView.as_view(),
        name="scheduling_detail",
    ),
    path(
        "scheduling/<uuid:appointment_id>/update/",
        views.SchedulingUpdateView.as_view(),
        name="scheduling_update",
    ),
    path(
        "scheduling/<uuid:appointment_id>/cancel/",
        views.SchedulingCancelView.as_view(),
        name="scheduling_cancel",
    ),
    path(
        "scheduling/<uuid:appointment_id>/restore/",
        views.SchedulingRestoreView.as_view(),
        name="scheduling_restore",
    ),
    # Dependent field options
    path(
        "scheduling/options/departments/",
        views.SchedulingDepartmentOptionsView.as_view(),
        name="scheduling_department_options",
    ),
    path(
        "scheduling/options/units/",
        views.SchedulingUnitOptionsView.as_view(),
        name="scheduling_unit_options",
    ),
    path(
        "scheduling/options/rooms/",
        views.SchedulingRoomOptionsView.as_view(),
        name="scheduling_room_options",
    ),
    # ========================================================
    # USER AND ACCESS MANAGEMENT
    # ========================================================
    path(
        "users/",
        views.UserAccountListView.as_view(),
        name="users",
    ),
    path("users/new/", views.UserAccountFormView.as_view(), name="user_create"),
    path(
        "users/<int:user_id>/edit/",
        views.UserAccountFormView.as_view(),
        name="user_update",
    ),
    path(
        "users/<int:user_id>/toggle/",
        views.UserAccountToggleView.as_view(),
        name="user_toggle",
    ),
    path(
        "users/<int:user_id>/password/",
        views.UserPasswordResetView.as_view(),
        name="user_password",
    ),
    path(
        "roles/",
        views.RolePermissionListView.as_view(),
        name="roles",
    ),
    path("roles/new/", views.RolePermissionFormView.as_view(), name="role_create"),
    path(
        "roles/<int:group_id>/edit/",
        views.RolePermissionFormView.as_view(),
        name="role_update",
    ),
    # ========================================================
    # ORGANIZATION AND FACILITIES
    # ========================================================
    path(
        "facilities/",
        views.FacilityAdministrationView.as_view(),
        name="facilities",
    ),
    path(
        "departments/",
        views.DepartmentAdministrationView.as_view(),
        name="departments",
    ),
    path(
        "clinical-units/",
        views.DepartmentAdministrationView.as_view(),
        name="clinical_units",
    ),
    path(
        "rooms/",
        views.RoomBedAdministrationView.as_view(),
        name="rooms",
    ),
    path("beds/", views.RoomBedAdministrationView.as_view(), name="beds"),
    # ========================================================
    # SYSTEM CONFIGURATION
    # ========================================================
    path(
        "system-settings/",
        views.SystemSettingsView.as_view(),
        name="system_settings",
    ),
    path(
        "clinical-dictionaries/",
        views.ClinicalDictionaryView.as_view(),
        name="clinical_dictionaries",
    ),
    path(
        "integrations/",
        views.IntegrationListView.as_view(),
        name="integrations",
    ),
    path(
        "data-management/", views.SystemSettingsView.as_view(), name="data_management"
    ),
    path(
        "configuration/<str:kind>/new/",
        views.ConfigurationFormView.as_view(),
        name="configuration_create",
    ),
    path(
        "configuration/<str:kind>/<int:object_id>/",
        views.ConfigurationFormView.as_view(),
        name="configuration_update",
    ),
    # ========================================================
    # MONITORING AND COMPLIANCE
    # ========================================================
    path(
        "audit-logs/",
        views.AuditLogListView.as_view(),
        name="audit_logs",
    ),
    path(
        "system-health/",
        views.SystemHealthView.as_view(),
        name="system_health",
    ),
]
