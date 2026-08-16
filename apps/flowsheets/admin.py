from django.contrib import admin

from .models import FlowSheetDefinition, FlowSheetEntry, FlowSheetFieldDefinition, FlowSheetValue


class FlowSheetFieldInline(admin.TabularInline):
    model = FlowSheetFieldDefinition
    extra = 0
    ordering = ("display_order",)
    fields = ("display_order", "section", "subsection", "label", "key", "data_type", "unit", "show_when_field_key", "show_when_value", "is_required")


@admin.register(FlowSheetDefinition)
class FlowSheetDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "is_system", "updated_at")
    list_filter = ("category", "is_active", "is_system")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = (FlowSheetFieldInline,)


class FlowSheetValueInline(admin.TabularInline):
    model = FlowSheetValue
    extra = 0
    readonly_fields = ("field", "value_text", "value_number", "value_boolean", "flag")
    can_delete = False


@admin.register(FlowSheetEntry)
class FlowSheetEntryAdmin(admin.ModelAdmin):
    list_display = ("patient", "flowsheet", "recorded_at", "recorded_by", "status")
    list_filter = ("flowsheet", "status", "recorded_at")
    search_fields = ("patient__mrn", "patient__first_name", "patient__last_name", "notes")
    readonly_fields = ("patient", "encounter", "flowsheet", "recorded_at", "recorded_by", "status", "notes", "correction_reason", "corrected_from", "entered_in_error_at", "entered_in_error_by", "created_at")
    inlines = (FlowSheetValueInline,)

    def has_add_permission(self, request):
        return False
