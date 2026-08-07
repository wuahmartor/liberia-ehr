

"""
============================================================
ADMINISTRATION FORMS

File:
apps/administration/forms.py

Purpose:
- Validate scheduling forms.
- Apply Tailwind styling.
- Limit organizational fields based on selected facility.
- Automatically validate appointment conflicts.
============================================================
"""

from __future__ import annotations

from datetime import timedelta

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.facilities.models import (
    ClinicalUnit,
    Department,
    Facility,
    Room,
)
from apps.patients.models import Patient

from .models import Appointment


User = get_user_model()


INPUT_CLASS = """
block w-full rounded-md border border-slate-300 bg-white
px-3 py-2 text-sm text-slate-900 shadow-sm
placeholder:text-slate-400
focus:border-ehr-500 focus:outline-none
focus:ring-2 focus:ring-ehr-500/20
disabled:cursor-not-allowed disabled:bg-slate-100
""".strip()

SELECT_CLASS = INPUT_CLASS

TEXTAREA_CLASS = """
block min-h-24 w-full rounded-md border border-slate-300
bg-white px-3 py-2 text-sm text-slate-900 shadow-sm
placeholder:text-slate-400
focus:border-ehr-500 focus:outline-none
focus:ring-2 focus:ring-ehr-500/20
""".strip()

CHECKBOX_CLASS = """
h-4 w-4 rounded border-slate-300 text-ehr-700
focus:ring-ehr-500
""".strip()


class AppointmentForm(forms.ModelForm):
    """
    Create and update scheduled appointments.
    """

    class Meta:
        model = Appointment

        fields = [
            "patient",
            "appointment_type",
            "status",
            "priority",
            "facility",
            "department",
            "clinical_unit",
            "room",
            "provider",
            "start_datetime",
            "end_datetime",
            "reason_for_visit",
            "patient_instructions",
            "internal_notes",
            "is_active",
        ]

        widgets = {
            "patient": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "appointment_type": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "status": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "priority": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "facility": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "department": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "clinical_unit": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "room": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "provider": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                },
            ),
            "start_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": INPUT_CLASS,
                    "type": "datetime-local",
                },
            ),
            "end_datetime": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": INPUT_CLASS,
                    "type": "datetime-local",
                },
            ),
            "reason_for_visit": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 3,
                    "placeholder": (
                        "Enter the reason for the appointment."
                    ),
                },
            ),
            "patient_instructions": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 3,
                    "placeholder": (
                        "Instructions that may be shared "
                        "with the patient."
                    ),
                },
            ),
            "internal_notes": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 3,
                    "placeholder": (
                        "Internal scheduling notes."
                    ),
                },
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                },
            ),
        }

        labels = {
            "clinical_unit": "Clinical unit",
            "start_datetime": "Start date and time",
            "end_datetime": "End date and time",
            "patient_instructions": "Patient instructions",
            "internal_notes": "Internal notes",
            "is_active": "Active appointment",
        }

    def __init__(
        self,
        *args,
        current_user=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.current_user = current_user

        self.fields["patient"].queryset = (
            Patient.objects
            .filter(is_active=True)
            .order_by(
                "last_name",
                "first_name",
            )
        )

        self.fields["facility"].queryset = (
            Facility.objects
            .filter(is_active=True)
            .order_by("name")
        )

        self.fields["department"].queryset = (
            Department.objects.none()
        )

        self.fields["clinical_unit"].queryset = (
            ClinicalUnit.objects.none()
        )

        self.fields["room"].queryset = (
            Room.objects.none()
        )

        self.fields["provider"].queryset = (
            User.objects
            .filter(
                is_active=True,
                is_staff=True,
            )
            .order_by(
                "last_name",
                "first_name",
                "username",
            )
        )

        self.fields["provider"].required = True
        self.fields["facility"].required = True
        self.fields["department"].required = True
        self.fields["clinical_unit"].required = True

        self.fields["room"].required = False

        # add clearer empty labels:
        self.fields["provider"].empty_label = "Select provider"
        self.fields["facility"].empty_label = "Select facility"
        self.fields["department"].empty_label = "Select department"
        self.fields["clinical_unit"].empty_label = "Select clinical unit"
        
        self.fields["room"].empty_label = "Select room, if applicable"

        self._configure_organization_querysets()

        if not self.instance.pk:
            now = timezone.localtime().replace(
                second=0,
                microsecond=0,
            )

            rounded_minutes = (
                ((now.minute // 15) + 1) * 15
            )

            if rounded_minutes >= 60:
                start_time = (
                    now.replace(minute=0)
                    + timedelta(hours=1)
                )
            else:
                start_time = now.replace(
                    minute=rounded_minutes,
                )

            self.initial.setdefault(
                "start_datetime",
                start_time,
            )

            self.initial.setdefault(
                "end_datetime",
                start_time + timedelta(minutes=30),
            )

            self.initial.setdefault(
                "status",
                Appointment.Status.SCHEDULED,
            )

            self.initial.setdefault(
                "priority",
                Appointment.Priority.ROUTINE,
            )

            self.initial.setdefault(
                "is_active",
                True,
            )

    def _posted_or_instance_value(
        self,
        field_name,
    ):
        if self.is_bound:
            return self.data.get(
                self.add_prefix(field_name),
            )

        value = self.initial.get(field_name)

        if value:
            return getattr(
                value,
                "pk",
                value,
            )

        return getattr(
            self.instance,
            f"{field_name}_id",
            None,
        )

    def _configure_organization_querysets(self):
        facility_id = self._posted_or_instance_value(
            "facility",
        )

        department_id = self._posted_or_instance_value(
            "department",
        )

        clinical_unit_id = self._posted_or_instance_value(
            "clinical_unit",
        )

        if facility_id:
            self.fields["department"].queryset = (
                Department.objects
                .filter(
                    facility_id=facility_id,
                    is_active=True,
                )
                .order_by("name")
            )

            self.fields["clinical_unit"].queryset = (
                ClinicalUnit.objects
                .filter(
                    facility_id=facility_id,
                    is_active=True,
                )
                .order_by("name")
            )

            self.fields["room"].queryset = (
                Room.objects
                .filter(
                    facility_id=facility_id,
                    is_active=True,
                )
                .order_by("name")
            )

        if department_id:
            self.fields["clinical_unit"].queryset = (
                ClinicalUnit.objects
                .filter(
                    department_id=department_id,
                    is_active=True,
                )
                .order_by("name")
            )

        if clinical_unit_id:
            self.fields["room"].queryset = (
                Room.objects
                .filter(
                    clinical_unit_id=clinical_unit_id,
                    is_active=True,
                )
                .order_by("name")
            )

    def clean(self):
        cleaned_data = super().clean()

        start_datetime = cleaned_data.get(
            "start_datetime",
        )

        end_datetime = cleaned_data.get(
            "end_datetime",
        )

        if (
            start_datetime
            and end_datetime
            and end_datetime <= start_datetime
        ):
            self.add_error(
                "end_datetime",
                (
                    "The appointment end time must be "
                    "after the start time."
                ),
            )

        return cleaned_data


class AppointmentCancelForm(forms.Form):
    """
    Cancel an appointment while preserving its record.
    """

    cancellation_reason = forms.CharField(
        label="Cancellation reason",
        widget=forms.Textarea(
            attrs={
                "class": TEXTAREA_CLASS,
                "rows": 4,
                "placeholder": (
                    "Document why this appointment "
                    "is being cancelled."
                ),
            },
        ),
    )