

from __future__ import annotations

from django import forms

from .models import (
    Bed,
    ClinicalUnit,
    Department,
    Facility,
    FacilityOperatingHour,
    FacilityService,
    Room,
)


class TailwindModelForm(forms.ModelForm):
    input_class = (
        "w-full rounded-md border-slate-300 bg-white px-3 py-2 text-sm "
        "shadow-sm focus:border-ehr-500 focus:ring-ehr-500"
    )
    checkbox_class = (
        "h-4 w-4 rounded border-slate-300 text-ehr-700 "
        "focus:ring-ehr-500"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = self.checkbox_class
            else:
                field.widget.attrs["class"] = self.input_class

            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.setdefault("rows", 3)


class FacilityForm(TailwindModelForm):
    class Meta:
        model = Facility
        fields = (
            "name",
            "short_name",
            "code",
            "facility_type",
            "ownership_type",
            "operational_status",
            "ministry_license_number",
            "accreditation_number",
            "phone_number",
            "alternate_phone",
            "emergency_phone",
            "email",
            "website",
            "address_line_1",
            "address_line_2",
            "community_or_city",
            "district",
            "county_or_state",
            "postal_code",
            "country",
            "directions_or_landmark",
            "latitude",
            "longitude",
            "parent_facility",
            "bed_capacity",
            "provides_emergency_services",
            "provides_inpatient_services",
            "provides_outpatient_services",
            "provides_maternity_services",
            "provides_surgical_services",
            "provides_laboratory_services",
            "provides_pharmacy_services",
            "provides_imaging_services",
            "timezone_name",
            "is_active",
            "notes",
        )


class DepartmentForm(TailwindModelForm):
    class Meta:
        model = Department
        fields = (
            "facility",
            "name",
            "code",
            "department_type",
            "description",
            "phone_extension",
            "email",
            "is_clinical",
            "is_active",
        )


class ClinicalUnitForm(TailwindModelForm):
    class Meta:
        model = ClinicalUnit
        fields = (
            "facility",
            "department",
            "name",
            "code",
            "unit_type",
            "description",
            "floor_or_location",
            "accepts_admissions",
            "is_clinical",
            "is_active",
        )


class RoomForm(TailwindModelForm):
    class Meta:
        model = Room
        fields = (
            "facility",
            "clinical_unit",
            "name",
            "code",
            "room_type",
            "floor",
            "capacity",
            "is_negative_pressure",
            "is_isolation_capable",
            "is_active",
        )


class BedForm(TailwindModelForm):
    class Meta:
        model = Bed
        fields = (
            "facility",
            "clinical_unit",
            "room",
            "name",
            "code",
            "bed_type",
            "status",
            "notes",
            "is_active",
        )


class FacilityOperatingHourForm(TailwindModelForm):
    class Meta:
        model = FacilityOperatingHour
        fields = (
            "facility",
            "weekday",
            "opens_at",
            "closes_at",
            "is_closed",
            "is_24_hours",
            "notes",
        )
        widgets = {
            "opens_at": forms.TimeInput(attrs={"type": "time"}),
            "closes_at": forms.TimeInput(attrs={"type": "time"}),
        }


class FacilityServiceForm(TailwindModelForm):
    class Meta:
        model = FacilityService
        fields = (
            "facility",
            "name",
            "code",
            "category",
            "description",
            "requires_appointment",
            "accepts_walk_ins",
            "is_active",
        )
