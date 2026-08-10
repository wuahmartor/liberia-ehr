from django.contrib import admin

from .models import MedicationOrder


@admin.register(MedicationOrder)
class MedicationOrderAdmin(admin.ModelAdmin):
    list_display = (
        "medication",
        "patient",
        "encounter",
        "dose",
        "route",
        "frequency",
        "status",
        "ordered_at",
    )
    list_filter = ("status", "route")
    search_fields = (
        "medication__generic_name",
        "medication__code",
        "patient__mrn",
        "encounter__encounter_number",
    )
    readonly_fields = ("ordered_at", "updated_at")
