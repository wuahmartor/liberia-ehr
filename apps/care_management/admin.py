from django.contrib import admin

from .models import CareShift, PatientStaffAssignment


@admin.register(CareShift)
class CareShiftAdmin(admin.ModelAdmin):
    list_display = ("name", "facility", "starts_at", "ends_at", "created_by")
    list_filter = ("facility", "starts_at", "ends_at")
    search_fields = ("name", "notes")


@admin.register(PatientStaffAssignment)
class PatientStaffAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "patient",
        "staff",
        "assignment_role",
        "shift",
        "status",
        "assigned_at",
        "staff_logged_out_at",
    )
    list_filter = ("assignment_role", "status", "shift")
    search_fields = (
        "patient__first_name",
        "patient__last_name",
        "patient__mrn",
        "staff__first_name",
        "staff__last_name",
        "staff__username",
    )
    readonly_fields = ("assigned_at",)
