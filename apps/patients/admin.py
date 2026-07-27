from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet

from .models import (
    EmergencyContact,
    InsuranceCoverage,
    Patient,
    PatientAddress,
    PatientAlias,
    PatientConsent,
    PatientContactPoint,
    PatientFlag,
    PatientFlagAcknowledgment,
    PatientIdentifier,
    PatientMergeRecord,
)


class AuditFieldsAdminMixin:
    """
    Makes system-generated audit fields read-only when they exist.
    """

    audit_field_names = (
        "id",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    )

    def get_readonly_fields(self, request, obj=None):
        model_field_names = {
            field.name
            for field in self.model._meta.get_fields()
        }

        return tuple(
            field_name
            for field_name in self.audit_field_names
            if field_name in model_field_names
        )

    def save_model(self, request, obj, form, change):
        if hasattr(obj, "created_by_id"):
            if not obj.created_by_id:
                obj.created_by = request.user

        if hasattr(obj, "updated_by_id"):
            obj.updated_by = request.user

        super().save_model(request, obj, form, change)


class PatientRelatedInline(admin.StackedInline):
    extra = 0
    show_change_link = True
    classes = ("collapse",)


class PatientIdentifierInline(PatientRelatedInline):
    model = PatientIdentifier
    verbose_name = "Patient identifier"
    verbose_name_plural = "Patient identifiers"


class PatientAliasInline(PatientRelatedInline):
    model = PatientAlias
    verbose_name = "Alias"
    verbose_name_plural = "Aliases"


class PatientAddressInline(PatientRelatedInline):
    model = PatientAddress
    verbose_name = "Address"
    verbose_name_plural = "Addresses"


class PatientContactPointInline(PatientRelatedInline):
    model = PatientContactPoint
    verbose_name = "Contact point"
    verbose_name_plural = "Contact points"


class EmergencyContactInline(PatientRelatedInline):
    model = EmergencyContact
    verbose_name = "Emergency contact"
    verbose_name_plural = "Emergency contacts"


class PatientConsentInline(PatientRelatedInline):
    model = PatientConsent
    verbose_name = "Consent"
    verbose_name_plural = "Consents"


class InsuranceCoverageInline(PatientRelatedInline):
    model = InsuranceCoverage
    verbose_name = "Insurance coverage"
    verbose_name_plural = "Insurance coverages"


class PatientFlagInline(PatientRelatedInline):
    model = PatientFlag
    verbose_name = "Clinical or administrative flag"
    verbose_name_plural = "Clinical and administrative flags"


@admin.register(Patient)
class PatientAdmin(AuditFieldsAdminMixin, admin.ModelAdmin):
    list_display = (
        "mrn",
        "display_name",
        "date_of_birth",
        "sex_at_birth",
        "registration_facility",
        "record_status",
        "is_deceased",
        "is_active",
    )

    list_display_links = (
        "mrn",
        "display_name",
    )

    list_filter = (
        "record_status",
        "is_active",
        "is_deceased",
        "sex_at_birth",
        "registration_facility",
        "confidential_record",
        "interpreter_required",
    )

    search_fields = (
        "mrn",
        "first_name",
        "middle_name",
        "last_name",
        "previous_last_name",
        "preferred_name",
        "identifiers__value",
        "contact_points__value",
    )

    autocomplete_fields = (
        "registration_facility",
    )

    date_hierarchy = "created_at"

    ordering = (
        "last_name",
        "first_name",
    )

    list_per_page = 50

    save_on_top = True

    inlines = (
        PatientIdentifierInline,
        PatientAliasInline,
        PatientAddressInline,
        PatientContactPointInline,
        EmergencyContactInline,
        PatientConsentInline,
        InsuranceCoverageInline,
        PatientFlagInline,
    )

    fieldsets = (
        (
            "Patient identity",
            {
                "fields": (
                    "id",
                    "mrn",
                    "prefix",
                    "first_name",
                    "middle_name",
                    "last_name",
                    "previous_last_name",
                    "suffix",
                    "preferred_name",
                )
            },
        ),
        (
            "Demographics",
            {
                "fields": (
                    "date_of_birth",
                    "date_of_birth_estimated",
                    "sex_at_birth",
                    "gender_identity",
                    "gender_identity_description",
                    "marital_status",
                    "blood_type",
                    "nationality",
                    "preferred_language",
                    "interpreter_required",
                )
            },
        ),
        (
            "Social information",
            {
                "classes": ("collapse",),
                "fields": (
                    "occupation",
                    "employer",
                    "education_level",
                    "religion",
                ),
            },
        ),
        (
            "Registration",
            {
                "fields": (
                    "registration_facility",
                    "record_status",
                    "registration_notes",
                    "is_active",
                )
            },
        ),
        (
            "Deceased information",
            {
                "classes": ("collapse",),
                "fields": (
                    "is_deceased",
                    "deceased_at",
                    "deceased_status_verified",
                ),
            },
        ),
        (
            "Privacy and restricted access",
            {
                "classes": ("collapse",),
                "fields": (
                    "confidential_record",
                    "restricted_access_reason",
                ),
            },
        ),
        (
            "Audit information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(
        description="Patient name",
        ordering="last_name",
    )
    def display_name(self, obj):
        preferred_name = getattr(obj, "preferred_name", "")

        if preferred_name:
            return (
                f"{obj.last_name}, {obj.first_name} "
                f'("{preferred_name}")'
            )

        middle_name = getattr(obj, "middle_name", "")

        if middle_name:
            return (
                f"{obj.last_name}, "
                f"{obj.first_name} {middle_name}"
            )

        return f"{obj.last_name}, {obj.first_name}"

    def get_queryset(self, request) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related(
                "registration_facility",
                "created_by",
                "updated_by",
            )
        )

    actions = (
        "activate_selected_patients",
        "deactivate_selected_patients",
    )

    @admin.action(description="Activate selected patient records")
    def activate_selected_patients(self, request, queryset):
        updated = queryset.update(is_active=True)

        self.message_user(
            request,
            f"{updated} patient record(s) activated.",
        )

    @admin.action(description="Deactivate selected patient records")
    def deactivate_selected_patients(self, request, queryset):
        updated = queryset.update(is_active=False)

        self.message_user(
            request,
            f"{updated} patient record(s) deactivated.",
        )

    def has_delete_permission(self, request, obj=None):
        """
        EHR patient records should normally be deactivated rather than
        permanently deleted.

        Superusers may still delete records during development.
        """

        return request.user.is_superuser


@admin.register(PatientIdentifier)
class PatientIdentifierAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "identifier_type",
        "value",
        "issuing_authority",
        "facility",
        "is_primary",
        "is_verified",
        "is_active",
    )

    list_filter = (
        "identifier_type",
        "is_primary",
        "is_verified",
        "is_active",
        "facility",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "value",
        "issuing_authority",
    )

    autocomplete_fields = (
        "patient",
        "facility",
    )

    ordering = (
        "patient",
        "identifier_type",
    )

    list_per_page = 50


@admin.register(PatientAlias)
class PatientAliasAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "first_name",
        "middle_name",
        "last_name",
        "reason",
        "is_active",
    )

    list_filter = (
        "is_active",
        "reason",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "first_name",
        "middle_name",
        "last_name",
    )

    autocomplete_fields = ("patient",)

    ordering = (
        "last_name",
        "first_name",
    )


@admin.register(PatientAddress)
class PatientAddressAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "address_type",
        "community_or_town",
        "district",
        "county_or_state",
        "country",
        "is_primary",
        "is_active",
    )

    list_filter = (
        "address_type",
        "county_or_state",
        "country",
        "is_primary",
        "is_active",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "line_1",
        "line_2",
        "community_or_town",
        "district",
        "county_or_state",
    )

    autocomplete_fields = ("patient",)

    ordering = (
        "patient",
        "-is_primary",
    )


@admin.register(PatientContactPoint)
class PatientContactPointAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "contact_type",
        "use_type",
        "value",
        "is_primary",
        "is_verified",
        "is_active",
    )

    list_filter = (
        "contact_type",
        "use_type",
        "is_primary",
        "is_verified",
        "is_active",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "value",
    )

    autocomplete_fields = ("patient",)

    ordering = (
        "patient",
        "sort_order",
    )


@admin.register(EmergencyContact)
class EmergencyContactAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "full_name",
        "relationship",
        "phone_number",
        "is_next_of_kin",
        "is_legal_guardian",
        "is_primary",
        "is_active",
    )

    list_filter = (
        "relationship",
        "is_next_of_kin",
        "is_legal_guardian",
        "may_receive_information",
        "may_make_decisions",
        "is_primary",
        "is_active",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "full_name",
        "phone_number",
        "alternate_phone",
        "email",
    )

    autocomplete_fields = ("patient",)

    ordering = (
        "patient",
        "-is_primary",
        "full_name",
    )


@admin.register(PatientConsent)
class PatientConsentAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "consent_type",
        "status",
        "effective_from",
        "effective_until",
        "granted_by_patient",
    )

    list_filter = (
        "consent_type",
        "status",
        "granted_by_patient",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "representative_name",
        "document_reference",
        "scope",
    )

    autocomplete_fields = ("patient",)

    date_hierarchy = "effective_from"

    ordering = (
        "-effective_from",
    )


@admin.register(InsuranceCoverage)
class InsuranceCoverageAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "payer_name",
        "plan_name",
        "member_number",
        "status",
        "is_primary",
        "is_verified",
    )

    list_filter = (
        "status",
        "is_primary",
        "is_verified",
        "payer_name",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "payer_name",
        "plan_name",
        "member_number",
        "group_number",
        "policy_holder_name",
    )

    autocomplete_fields = ("patient",)

    ordering = (
        "patient",
        "-is_primary",
        "payer_name",
    )


class PatientFlagAcknowledgmentInline(admin.TabularInline):
    model = PatientFlagAcknowledgment
    extra = 0
    show_change_link = True


@admin.register(PatientFlag)
class PatientFlagAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "patient",
        "title",
        "severity",
        "starts_at",
        "ends_at",
        "requires_acknowledgment",
        "is_active",
    )

    list_filter = (
        "severity",
        "requires_acknowledgment",
        "is_active",
    )

    search_fields = (
        "patient__mrn",
        "patient__first_name",
        "patient__last_name",
        "title",
        "description",
    )

    autocomplete_fields = ("patient",)

    date_hierarchy = "starts_at"

    ordering = (
        "-starts_at",
        "-severity",
    )

    inlines = (
        PatientFlagAcknowledgmentInline,
    )


@admin.register(PatientFlagAcknowledgment)
class PatientFlagAcknowledgmentAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "flag",
        "acknowledged_by",
        "acknowledged_at",
    )

    list_filter = (
        "acknowledged_at",
    )

    search_fields = (
        "flag__title",
        "flag__patient__mrn",
        "flag__patient__first_name",
        "flag__patient__last_name",
        "acknowledged_by__username",
        "acknowledged_by__first_name",
        "acknowledged_by__last_name",
    )

    autocomplete_fields = (
        "flag",
        "acknowledged_by",
    )

    ordering = (
        "-acknowledged_at",
    )


@admin.register(PatientMergeRecord)
class PatientMergeRecordAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "surviving_patient",
        "duplicate_patient",
        "status",
        "reviewed_by",
        "reviewed_at",
        "completed_at",
    )

    list_filter = (
        "status",
        "reviewed_at",
        "completed_at",
    )

    search_fields = (
        "surviving_patient__mrn",
        "surviving_patient__first_name",
        "surviving_patient__last_name",
        "duplicate_patient__mrn",
        "duplicate_patient__first_name",
        "duplicate_patient__last_name",
        "reason",
        "reversal_reason",
    )

    autocomplete_fields = (
        "surviving_patient",
        "duplicate_patient",
        "reviewed_by",
    )

    ordering = (
        "-created_at",
    )

    fieldsets = (
        (
            "Merge patients",
            {
                "fields": (
                    "surviving_patient",
                    "duplicate_patient",
                    "reason",
                    "status",
                )
            },
        ),
        (
            "Review",
            {
                "fields": (
                    "reviewed_by",
                    "reviewed_at",
                    "completed_at",
                )
            },
        ),
        (
            "Reversal",
            {
                "classes": ("collapse",),
                "fields": (
                    "reversal_reason",
                ),
            },
        ),
        (
            "Audit information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_by",
                    "updated_by",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )