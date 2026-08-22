from django.contrib import admin
from .models import LabClinicalRecommendation, LabOrder, LabOrderItem, LabPanel, LabPanelTest, LabReferenceRange, LabResult, LabSpecimen, LabTestDefinition

class PanelTestInline(admin.TabularInline):
    model = LabPanelTest
    extra = 0

@admin.register(LabPanel)
class PanelAdmin(admin.ModelAdmin):
    list_display = ("name", "loinc_code", "is_active")
    inlines = (PanelTestInline,)

@admin.register(LabTestDefinition)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "loinc_code", "default_unit", "is_active")
    search_fields = ("name", "code", "loinc_code")

@admin.register(LabReferenceRange)
class RangeAdmin(admin.ModelAdmin):
    list_display = ("test", "label", "sex", "lower_bound", "upper_bound", "unit", "is_locally_validated")

admin.site.register((LabOrder, LabOrderItem, LabSpecimen, LabResult, LabClinicalRecommendation))
