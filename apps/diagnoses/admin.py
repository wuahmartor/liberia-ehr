from django.contrib import admin

from .models import (
    ClinicalConcept,
    ClinicalConceptRelationship,
    ClinicalConceptTerm,
    PatientDiagnosis,
    PatientDiagnosisManifestation,
    PatientProcedure,
    ProcedureCode,
    TerminologySource,
)


class ConceptTermInline(admin.TabularInline):
    model = ClinicalConceptTerm
    extra = 0


@admin.register(TerminologySource)
class TerminologySourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "source_type",
        "release_version",
        "language",
        "is_active",
        "last_synchronized_at",
    )
    list_filter = ("source_type", "is_active", "language")
    search_fields = ("name", "release_version")


@admin.register(ClinicalConcept)
class ClinicalConceptAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "title",
        "source",
        "concept_kind",
        "is_billable",
        "is_active",
    )
    list_filter = ("source", "concept_kind", "is_billable", "is_active")
    search_fields = ("code", "title", "fully_specified_name", "terms__term")
    readonly_fields = ("imported_at", "created_at", "updated_at")
    inlines = (ConceptTermInline,)


@admin.register(PatientDiagnosis)
class PatientDiagnosisAdmin(admin.ModelAdmin):
    list_display = (
        "display_snapshot",
        "code_snapshot",
        "patient",
        "diagnosis_type",
        "clinical_status",
        "verification_status",
        "diagnosed_on",
    )
    list_filter = (
        "clinical_status",
        "verification_status",
        "diagnosis_type",
        "severity",
        "is_current_problem",
    )
    search_fields = (
        "display_snapshot",
        "code_snapshot",
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
    )
    readonly_fields = (
        "code_snapshot",
        "display_snapshot",
        "source_snapshot",
        "created_at",
        "updated_at",
    )


admin.site.register(ClinicalConceptRelationship)
admin.site.register(PatientDiagnosisManifestation)
admin.site.register(ProcedureCode)


@admin.register(PatientProcedure)
class PatientProcedureAdmin(admin.ModelAdmin):
    list_display = (
        "display_snapshot",
        "code_snapshot",
        "patient",
        "status",
        "performed_on",
        "performed_by",
    )
    list_filter = ("status", "procedure_code__code_system")
    search_fields = (
        "display_snapshot",
        "code_snapshot",
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
    )
    readonly_fields = (
        "code_snapshot",
        "display_snapshot",
        "source_snapshot",
        "created_at",
        "updated_at",
    )
