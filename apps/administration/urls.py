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
    path(
        "roles/",
        views.RolePermissionListView.as_view(),
        name="roles",
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
        "rooms/",
        views.RoomBedAdministrationView.as_view(),
        name="rooms",
    ),

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