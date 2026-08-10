from django.contrib import admin

from .models import MedicationAdministration


@admin.register(MedicationAdministration)
class MedicationAdministrationAdmin(admin.ModelAdmin):
    list_display = (
        "medication",
        "patient",
        "encounter",
        "dose_administered",
        "route",
        "status",
        "administered_at",
        "administered_by",
    )
    list_filter = ("status", "route")
    search_fields = (
        "medication__generic_name",
        "medication__code",
        "patient__mrn",
        "encounter__encounter_number",
    )
    readonly_fields = ("created_at",)
