from django.contrib import admin

from .models import Medication


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "rxnorm_rxcui",
        "generic_name",
        "brand_name",
        "strength",
        "dosage_form",
        "route",
        "quantity_on_hand",
        "unit_of_measure",
        "is_active",
        "is_controlled",
    )
    list_filter = (
        "is_active",
        "requires_prescription",
        "is_controlled",
        "dosage_form",
        "route",
    )
    search_fields = (
        "code",
        "rxnorm_rxcui",
        "generic_name",
        "brand_name",
        "strength",
    )
    ordering = ("generic_name", "code")
    readonly_fields = ("created_at", "updated_at")
