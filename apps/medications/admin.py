from __future__ import annotations

from django.contrib import admin

from .models import MedicationAdministration


@admin.register(MedicationAdministration)
class MedicationAdministrationAdmin(admin.ModelAdmin):

    # ========================================================
    # LIST
    # ========================================================

    list_display = (
        "medication",
        "patient",
        "encounter",
        "status",
        "dose_administered",
        "route",
        "scheduled_at",
        "administered_at",
        "administered_by",
    )

    list_filter = (
        "status",
        "route",
        "medication__is_high_alert",
        "medication__is_controlled",
        "medication__is_lasa",
    )

    search_fields = (
        "medication__generic_name",
        "medication__brand_name",
        "medication__code",
        "medication__rxnorm_rxcui",
        "patient__mrn",
        "encounter__encounter_number",
        "dose_administered",
        "reason",
        "notes",
    )

    ordering = (
        "-administered_at",
    )

    date_hierarchy = "administered_at"

    list_per_page = 50

    # ========================================================
    # DATABASE OPTIMIZATION
    # ========================================================

    list_select_related = (
        "patient",
        "encounter",
        "medication",
        "medication_order",
        "administered_by",
        "witnessed_by",
    )

    # ========================================================
    # READ ONLY
    # ========================================================

    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
    )

    # ========================================================
    # FIELDSETS
    # ========================================================

    fieldsets = (
        (
            "Medication Order",
            {
                "fields": (
                    "medication_order",
                    "medication",
                )
            },
        ),

        (
            "Patient / Encounter",
            {
                "fields": (
                    "patient",
                    "encounter",
                )
            },
        ),

        (
            "Administration",
            {
                "fields": (
                    "status",
                    "dose_administered",
                    "route",
                    "administration_site",
                    "scheduled_at",
                    "administered_at",
                )
            },
        ),

        (
            "Clinical Documentation",
            {
                "fields": (
                    "reason",
                    "notes",
                )
            },
        ),

        (
            "Clinicians",
            {
                "fields": (
                    "administered_by",
                    "witnessed_by",
                )
            },
        ),

        (
            "Audit",
            {
                "classes": (
                    "collapse",
                ),
                "fields": (
                    "id",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    # ========================================================
    # DELETE PROTECTION
    # ========================================================

    def has_delete_permission(
        self,
        request,
        obj=None,
    ):
        """
        Medication administration records are clinical records.

        Corrections should eventually use an amendment/correction
        workflow rather than hard deletion.
        """
        return False