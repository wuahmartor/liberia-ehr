from __future__ import annotations

from django.contrib import admin
from django.utils import timezone

from .models import DispenseRecord, InventoryTransaction, Medication, PharmacyReview


@admin.register(PharmacyReview)
class PharmacyReviewAdmin(admin.ModelAdmin):
    list_display = ("order", "status", "reviewed_by", "reviewed_at")
    list_filter = ("status", "reviewed_at")
    search_fields = ("order__patient__mrn", "order__medication__generic_name")


@admin.register(DispenseRecord)
class DispenseRecordAdmin(admin.ModelAdmin):
    list_display = ("medication", "order", "quantity", "dispensed_by", "dispensed_at")
    list_filter = ("dispensed_at",)
    search_fields = ("order__patient__mrn", "medication__generic_name", "lot_number")


@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "medication",
        "movement_type",
        "quantity_change",
        "balance_after",
        "recorded_by",
        "recorded_at",
    )
    list_filter = ("movement_type", "recorded_at")
    search_fields = ("medication__generic_name", "medication__code", "reference")


# ============================================================
# MEDICATION ADMIN
# ============================================================


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    """
    Administrative formulary management.

    Clinical medication ordering should occur through the EHR workflow,
    not through Django Admin.
    """

    # ========================================================
    # LIST
    # ========================================================

    list_display = (
        "code",
        "generic_name",
        "brand_name",
        "strength",
        "dosage_form",
        "route",
        "formulary_status",
        "stock_status",
        "quantity_on_hand",
        "is_high_alert",
        "is_controlled",
        "is_active",
    )

    list_display_links = (
        "code",
        "generic_name",
    )

    list_filter = (
        "formulary_status",
        "is_active",
        "terminology_source",
        "requires_prescription",
        "is_controlled",
        "is_high_alert",
        "is_lasa",
        "dosage_form",
        "route",
    )

    search_fields = (
        "code",
        "rxnorm_rxcui",
        "generic_name",
        "brand_name",
        "strength",
        "dosage_form",
        "route",
        "therapeutic_class",
    )

    ordering = (
        "generic_name",
        "strength",
        "code",
    )

    list_per_page = 50

    date_hierarchy = "created_at"

    # ========================================================
    # READ-ONLY
    # ========================================================

    readonly_fields = (
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "retired_at",
        "retired_by",
    )

    # ========================================================
    # FIELDSETS
    # ========================================================

    fieldsets = (
        (
            "Medication Identification",
            {
                "fields": (
                    "code",
                    "terminology_source",
                    "rxnorm_rxcui",
                )
            },
        ),
        (
            "Medication Description",
            {
                "fields": (
                    "generic_name",
                    "brand_name",
                    "strength",
                    "dosage_form",
                    "route",
                    "therapeutic_class",
                )
            },
        ),
        (
            "Formulary",
            {
                "fields": (
                    "formulary_status",
                    "is_active",
                    "requires_prescription",
                )
            },
        ),
        (
            "Medication Safety",
            {
                "fields": (
                    "is_controlled",
                    "controlled_substance_class",
                    "is_high_alert",
                    "is_lasa",
                    "safety_notes",
                )
            },
        ),
        (
            "Inventory",
            {
                "fields": (
                    "unit_of_measure",
                    "quantity_on_hand",
                    "reorder_level",
                )
            },
        ),
        (
            "Retirement",
            {
                "classes": ("collapse",),
                "fields": (
                    "retired_at",
                    "retired_by",
                    "retirement_reason",
                ),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_by",
                    "created_at",
                    "updated_by",
                    "updated_at",
                ),
            },
        ),
    )

    # ========================================================
    # ACTIONS
    # ========================================================

    actions = (
        "retire_selected_medications",
        "reactivate_selected_medications",
    )

    # ========================================================
    # STOCK DISPLAY
    # ========================================================

    @admin.display(
        description="Stock",
        ordering="quantity_on_hand",
    )
    def stock_status(self, obj: Medication) -> str:
        if obj.quantity_on_hand <= 0:
            return "Out"

        if obj.quantity_on_hand <= obj.reorder_level:
            return "Low"

        return "Available"

    # ========================================================
    # AUDIT
    # ========================================================

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        if not obj.pk and not obj.created_by_id:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    # ========================================================
    # RETIRE ACTION
    # ========================================================

    @admin.action(description="Retire selected medications")
    def retire_selected_medications(
        self,
        request,
        queryset,
    ):
        count = queryset.exclude(
            formulary_status=Medication.FormularyStatus.RETIRED,
        ).update(
            formulary_status=Medication.FormularyStatus.RETIRED,
            is_active=False,
            retired_at=timezone.now(),
            retired_by=request.user,
            updated_by=request.user,
        )

        self.message_user(
            request,
            f"{count} medication(s) retired.",
        )

    # ========================================================
    # REACTIVATE ACTION
    # ========================================================

    @admin.action(description="Reactivate selected medications")
    def reactivate_selected_medications(
        self,
        request,
        queryset,
    ):
        count = queryset.update(
            formulary_status=Medication.FormularyStatus.FORMULARY,
            is_active=True,
            retired_at=None,
            retired_by=None,
            retirement_reason="",
            updated_by=request.user,
        )

        self.message_user(
            request,
            f"{count} medication(s) reactivated.",
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
        Disable routine hard deletion.

        Pharmacy/formulary records should be retired instead of deleted.
        """

        return False
