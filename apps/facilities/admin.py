

from __future__ import annotations

from django.contrib import admin
from django.db.models import Count, QuerySet

from .models import (
    Bed,
    ClinicalUnit,
    Department,
    Facility,
    FacilityOperatingHour,
    FacilityService,
    Room,
)


class AuditFieldsAdminMixin:
    """
    Makes system-generated fields read-only and records the user
    creating or updating an object.
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


class FacilityRelatedInline(admin.TabularInline):
    extra = 0
    show_change_link = True
    classes = ("collapse",)


class DepartmentInline(FacilityRelatedInline):
    model = Department

    fields = (
        "name",
        "code",
        "department_type",
        "phone_extension",
        "is_clinical",
        "is_active",
    )


class ClinicalUnitInline(FacilityRelatedInline):
    model = ClinicalUnit

    fields = (
        "name",
        "code",
        "department",
        "unit_type",
        "floor_or_location",
        "accepts_admissions",
        "is_active",
    )

    autocomplete_fields = (
        "department",
    )


class FacilityServiceInline(FacilityRelatedInline):
    model = FacilityService

    fields = (
        "name",
        "code",
        "category",
        "requires_appointment",
        "accepts_walk_ins",
        "is_active",
    )


class FacilityOperatingHourInline(FacilityRelatedInline):
    model = FacilityOperatingHour

    fields = (
        "weekday",
        "opens_at",
        "closes_at",
        "is_closed",
        "is_24_hours",
        "notes",
    )


@admin.register(Facility)
class FacilityAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility_type",
        "ownership_type",
        "county_or_state",
        "operational_status",
        "department_total",
        "unit_total",
        "bed_total",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility_type",
        "ownership_type",
        "operational_status",
        "county_or_state",
        "provides_emergency_services",
        "provides_inpatient_services",
        "provides_outpatient_services",
        "provides_maternity_services",
        "provides_surgical_services",
        "provides_laboratory_services",
        "provides_pharmacy_services",
        "provides_imaging_services",
        "is_active",
    )

    search_fields = (
        "name",
        "short_name",
        "code",
        "ministry_license_number",
        "accreditation_number",
        "phone_number",
        "email",
        "community_or_city",
        "district",
        "county_or_state",
        "country",
    )

    autocomplete_fields = (
        "parent_facility",
    )

    ordering = ("name",)

    list_per_page = 50

    save_on_top = True

    inlines = (
        DepartmentInline,
        ClinicalUnitInline,
        FacilityServiceInline,
        FacilityOperatingHourInline,
    )

    fieldsets = (
        (
            "Facility identity",
            {
                "fields": (
                    "id",
                    "name",
                    "short_name",
                    "code",
                    "facility_type",
                    "ownership_type",
                    "operational_status",
                    "parent_facility",
                )
            },
        ),
        (
            "Licensing and accreditation",
            {
                "classes": ("collapse",),
                "fields": (
                    "ministry_license_number",
                    "accreditation_number",
                ),
            },
        ),
        (
            "Contact information",
            {
                "fields": (
                    "phone_number",
                    "alternate_phone",
                    "emergency_phone",
                    "email",
                    "website",
                )
            },
        ),
        (
            "Physical address",
            {
                "fields": (
                    "address_line_1",
                    "address_line_2",
                    "community_or_city",
                    "district",
                    "county_or_state",
                    "postal_code",
                    "country",
                    "directions_or_landmark",
                )
            },
        ),
        (
            "Geographic coordinates",
            {
                "classes": ("collapse",),
                "fields": (
                    "latitude",
                    "longitude",
                ),
            },
        ),
        (
            "Capacity",
            {
                "fields": (
                    "bed_capacity",
                )
            },
        ),
        (
            "Available clinical services",
            {
                "fields": (
                    "provides_emergency_services",
                    "provides_inpatient_services",
                    "provides_outpatient_services",
                    "provides_maternity_services",
                    "provides_surgical_services",
                    "provides_laboratory_services",
                    "provides_pharmacy_services",
                    "provides_imaging_services",
                )
            },
        ),
        (
            "System configuration",
            {
                "fields": (
                    "timezone_name",
                    "is_active",
                    "notes",
                )
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

    actions = (
        "activate_selected_facilities",
        "deactivate_selected_facilities",
    )

    def get_queryset(self, request) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .select_related(
                "parent_facility",
                "created_by",
                "updated_by",
            )
            .annotate(
                admin_department_total=Count(
                    "departments",
                    distinct=True,
                ),
                admin_unit_total=Count(
                    "clinical_units",
                    distinct=True,
                ),
                admin_bed_total=Count(
                    "beds",
                    distinct=True,
                ),
            )
        )

    @admin.display(
        description="Departments",
        ordering="admin_department_total",
    )
    def department_total(self, obj):
        return obj.admin_department_total

    @admin.display(
        description="Units",
        ordering="admin_unit_total",
    )
    def unit_total(self, obj):
        return obj.admin_unit_total

    @admin.display(
        description="Beds",
        ordering="admin_bed_total",
    )
    def bed_total(self, obj):
        return obj.admin_bed_total

    @admin.action(description="Activate selected facilities")
    def activate_selected_facilities(self, request, queryset):
        updated = queryset.update(
            is_active=True,
            operational_status=Facility.OperationalStatus.ACTIVE,
        )

        self.message_user(
            request,
            f"{updated} facility record(s) activated.",
        )

    @admin.action(description="Deactivate selected facilities")
    def deactivate_selected_facilities(self, request, queryset):
        updated = queryset.update(is_active=False)

        self.message_user(
            request,
            f"{updated} facility record(s) deactivated.",
        )


@admin.register(Department)
class DepartmentAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility",
        "department_type",
        "phone_extension",
        "is_clinical",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility",
        "department_type",
        "is_clinical",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "description",
        "email",
        "facility__name",
        "facility__code",
    )

    autocomplete_fields = (
        "facility",
    )

    ordering = (
        "facility__name",
        "name",
    )

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "created_by",
                "updated_by",
            )
        )


@admin.register(ClinicalUnit)
class ClinicalUnitAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility",
        "department",
        "unit_type",
        "floor_or_location",
        "accepts_admissions",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility",
        "department",
        "unit_type",
        "accepts_admissions",
        "is_clinical",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "description",
        "floor_or_location",
        "facility__name",
        "facility__code",
        "department__name",
    )

    autocomplete_fields = (
        "facility",
        "department",
    )

    ordering = (
        "facility__name",
        "name",
    )

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "department",
                "created_by",
                "updated_by",
            )
        )


class BedInline(admin.TabularInline):
    model = Bed
    extra = 0
    show_change_link = True

    fields = (
        "name",
        "code",
        "bed_type",
        "status",
        "is_active",
    )


@admin.register(Room)
class RoomAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility",
        "clinical_unit",
        "room_type",
        "floor",
        "capacity",
        "is_isolation_capable",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility",
        "clinical_unit",
        "room_type",
        "is_negative_pressure",
        "is_isolation_capable",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "floor",
        "facility__name",
        "facility__code",
        "clinical_unit__name",
    )

    autocomplete_fields = (
        "facility",
        "clinical_unit",
    )

    ordering = (
        "facility__name",
        "clinical_unit__name",
        "name",
    )

    list_per_page = 50

    inlines = (
        BedInline,
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "clinical_unit",
                "created_by",
                "updated_by",
            )
        )


@admin.register(Bed)
class BedAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility",
        "clinical_unit",
        "room",
        "bed_type",
        "status",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility",
        "clinical_unit",
        "room",
        "bed_type",
        "status",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "facility__name",
        "facility__code",
        "clinical_unit__name",
        "room__name",
        "room__code",
    )

    autocomplete_fields = (
        "facility",
        "clinical_unit",
        "room",
    )

    ordering = (
        "facility__name",
        "clinical_unit__name",
        "code",
    )

    list_per_page = 50

    actions = (
        "mark_available",
        "mark_out_of_service",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "clinical_unit",
                "room",
                "created_by",
                "updated_by",
            )
        )

    @admin.action(description="Mark selected beds as available")
    def mark_available(self, request, queryset):
        updated = queryset.filter(
            is_active=True,
        ).update(
            status=Bed.BedStatus.AVAILABLE,
        )

        self.message_user(
            request,
            f"{updated} bed(s) marked available.",
        )

    @admin.action(description="Mark selected beds out of service")
    def mark_out_of_service(self, request, queryset):
        updated = queryset.update(
            status=Bed.BedStatus.OUT_OF_SERVICE,
        )

        self.message_user(
            request,
            f"{updated} bed(s) marked out of service.",
        )


@admin.register(FacilityService)
class FacilityServiceAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "name",
        "code",
        "facility",
        "category",
        "requires_appointment",
        "accepts_walk_ins",
        "is_active",
    )

    list_display_links = (
        "name",
        "code",
    )

    list_filter = (
        "facility",
        "category",
        "requires_appointment",
        "accepts_walk_ins",
        "is_active",
    )

    search_fields = (
        "name",
        "code",
        "description",
        "facility__name",
        "facility__code",
    )

    autocomplete_fields = (
        "facility",
    )

    ordering = (
        "facility__name",
        "name",
    )

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "created_by",
                "updated_by",
            )
        )


@admin.register(FacilityOperatingHour)
class FacilityOperatingHourAdmin(
    AuditFieldsAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "facility",
        "weekday",
        "opens_at",
        "closes_at",
        "is_closed",
        "is_24_hours",
    )

    list_filter = (
        "facility",
        "weekday",
        "is_closed",
        "is_24_hours",
    )

    search_fields = (
        "facility__name",
        "facility__code",
        "notes",
    )

    autocomplete_fields = (
        "facility",
    )

    ordering = (
        "facility__name",
        "weekday",
    )

    list_per_page = 50

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "facility",
                "created_by",
                "updated_by",
            )
        )