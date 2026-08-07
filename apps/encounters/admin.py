from django.contrib import admin


"""
Liberia EHR Encounter Administration

File:
apps/encounters/admin.py

Purpose:
- Register encounters in Django Administration.
- Support encounter searching and autocomplete selection.
- Present encounter workflow information in a structured layout.
"""

from django.contrib import admin

from .models import Encounter


@admin.register(Encounter)
class EncounterAdmin(admin.ModelAdmin):
    list_display = (
        "encounter_number",
        "patient",
        "encounter_type",
        "status",
        "priority",
        "start_datetime",
        "attending_provider",
        "is_active",
    )

    list_filter = (
        "encounter_type",
        "status",
        "priority",
        "registration_completed",
        "identity_verified",
        "is_active",
        "start_datetime",
    )

    search_fields = (
        "encounter_number",
        "patient__mrn",
        "patient__first_name",
        "patient__middle_name",
        "patient__last_name",
        "reason_for_visit",
        "attending_provider__username",
        "attending_provider__first_name",
        "attending_provider__last_name",
    )

    autocomplete_fields = (
        "patient",
        "attending_provider",
    )

    readonly_fields = (
        "id",
        "encounter_number",
        "registered_at",
        "registered_by",
        "identity_verified_at",
        "identity_verified_by",
        "arrived_at",
        "check_in_user",
        "triaged_at",
        "triaged_by",
        "clinical_start_at",
        "clinical_started_by",
        "completed_at",
        "completed_by",
        "end_datetime",
        "cancelled_at",
        "cancelled_by",
        "entered_in_error_at",
        "entered_in_error_by",
        "created_by",
        "created_at",
        "updated_at",
        "is_active",
    )

    date_hierarchy = "start_datetime"

    ordering = (
        "-start_datetime",
    )

    list_select_related = (
        "patient",
        "attending_provider",
        "created_by",
    )

    fieldsets = (
        (
            "Encounter identity",
            {
                "fields": (
                    "id",
                    "encounter_number",
                    "patient",
                ),
            },
        ),
        (
            "Classification",
            {
                "fields": (
                    (
                        "encounter_type",
                        "status",
                        "priority",
                    ),
                    "reason_for_visit",
                ),
            },
        ),
        (
            "Registration and identity",
            {
                "fields": (
                    (
                        "registration_completed",
                        "identity_verified",
                    ),
                    (
                        "registered_at",
                        "registered_by",
                    ),
                    (
                        "identity_verified_at",
                        "identity_verified_by",
                    ),
                ),
            },
        ),
        (
            "Arrival and triage",
            {
                "fields": (
                    (
                        "arrived_at",
                        "check_in_user",
                    ),
                    (
                        "triaged_at",
                        "triaged_by",
                    ),
                ),
            },
        ),
        (
            "Clinical care",
            {
                "fields": (
                    "start_datetime",
                    (
                        "clinical_start_at",
                        "clinical_started_by",
                    ),
                    (
                        "completed_at",
                        "completed_by",
                    ),
                    "end_datetime",
                    "attending_provider",
                ),
            },
        ),
        (
            "Status and audit",
            {
                "fields": (
                    "status_reason",
                    (
                        "cancelled_at",
                        "cancelled_by",
                    ),
                    (
                        "entered_in_error_at",
                        "entered_in_error_by",
                    ),
                    "is_active",
                ),
            },
        ),
        (
            "Additional information",
            {
                "fields": (
                    "notes",
                ),
            },
        ),
        (
            "Record audit",
            {
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        obj.save(actor=request.user)