"""
Liberia EHR Encounter Forms

File:
apps/encounters/forms.py

Purpose:
- Create and update encounter records.
- Apply Tailwind CSS styling.
- Validate registration, arrival, triage, clinical-care,
  completion, and cancellation workflow.
"""

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Encounter


User = get_user_model()


class DateTimeLocalInput(forms.DateTimeInput):
    """
    HTML datetime-local input widget.
    """

    input_type = "datetime-local"


class EncounterForm(forms.ModelForm):
    """
    Form used to create and update encounters.

    The form supports:
    - New and existing patients
    - Registration completion
    - Identity verification
    - Arrival and check-in
    - Triage
    - Clinical start
    - Encounter completion
    - Staff assignment
    """

    class Meta:
        model = Encounter

        fields = [
            "patient",
            "encounter_type",
            "status",
            "priority",
            "reason_for_visit",

            "registration_completed",
            "identity_verified",
            "registered_at",
            "registered_by",

            "arrived_at",
            "check_in_user",

            "triaged_at",
            "triaged_by",

            "start_datetime",
            "clinical_start_at",
            "completed_at",
            "end_datetime",

            "attending_provider",
            "notes",
            "is_active",
        ]

        widgets = {
            "patient": forms.Select(),

            "encounter_type": forms.Select(),

            "status": forms.Select(),

            "priority": forms.Select(),

            "reason_for_visit": forms.TextInput(
                attrs={
                    "placeholder": (
                        "Enter the chief complaint or reason for visit"
                    ),
                    "maxlength": "500",
                }
            ),

            "registration_completed": forms.CheckboxInput(),

            "identity_verified": forms.CheckboxInput(),

            "registered_at": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "registered_by": forms.Select(),

            "arrived_at": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "check_in_user": forms.Select(),

            "triaged_at": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "triaged_by": forms.Select(),

            "start_datetime": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "clinical_start_at": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "completed_at": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "end_datetime": DateTimeLocalInput(
                format="%Y-%m-%dT%H:%M",
            ),

            "attending_provider": forms.Select(),

            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Enter relevant clinical or administrative notes"
                    ),
                }
            ),

            "is_active": forms.CheckboxInput(),
        }

        help_texts = {
            "patient": (
                "Select an existing patient or register a new patient first."
            ),
            "encounter_type": (
                "Select the type of care being provided."
            ),
            "status": (
                "Use Arrived after check-in, Triaged after nursing triage, "
                "In progress when clinical care begins, and Completed when "
                "the visit is finished."
            ),
            "priority": (
                "Select the urgency of the encounter."
            ),
            "reason_for_visit": (
                "Enter the patient's chief complaint or primary reason "
                "for seeking care."
            ),
            "registration_completed": (
                "Indicates that minimum registration requirements have "
                "been completed for this encounter."
            ),
            "identity_verified": (
                "Confirm that the patient's identity was verified using "
                "the required identifiers."
            ),
            "registered_at": (
                "The time registration was completed."
            ),
            "registered_by": (
                "The staff member who completed registration."
            ),
            "arrived_at": (
                "The time the patient arrived or checked in."
            ),
            "check_in_user": (
                "The staff member who checked the patient in."
            ),
            "triaged_at": (
                "The time nursing or clinical triage was completed."
            ),
            "triaged_by": (
                "The nurse or clinician who completed triage."
            ),
            "start_datetime": (
                "The administrative or planned start of the encounter."
            ),
            "clinical_start_at": (
                "The time direct clinical care began."
            ),
            "completed_at": (
                "The time clinical care was completed."
            ),
            "end_datetime": (
                "The administrative end time of the encounter."
            ),
            "attending_provider": (
                "The primary provider responsible for this encounter."
            ),
            "is_active": (
                "Inactive encounters are normally cancelled or entered "
                "in error."
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Configure field querysets, date formats, defaults,
        optional fields, labels, and Tailwind CSS classes.
        """

        self.current_user = kwargs.pop("current_user", None)

        super().__init__(*args, **kwargs)

        # =========================================================
        # ACTIVE USER QUERYSET
        # =========================================================
        active_users = User.objects.filter(
            is_active=True,
        ).order_by(
            "first_name",
            "last_name",
            "username",
        )

        user_field_names = [
            "attending_provider",
            "registered_by",
            "check_in_user",
            "triaged_by",
        ]

        for field_name in user_field_names:
            self.fields[field_name].queryset = active_users
            self.fields[field_name].required = False
            self.fields[field_name].empty_label = "Not assigned"

        # =========================================================
        # DATETIME FIELD CONFIGURATION
        # =========================================================
        datetime_field_names = [
            "registered_at",
            "arrived_at",
            "triaged_at",
            "start_datetime",
            "clinical_start_at",
            "completed_at",
            "end_datetime",
        ]

        for field_name in datetime_field_names:
            self.fields[field_name].input_formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S",
            ]

        optional_datetime_fields = [
            "registered_at",
            "arrived_at",
            "triaged_at",
            "clinical_start_at",
            "completed_at",
            "end_datetime",
        ]

        for field_name in optional_datetime_fields:
            self.fields[field_name].required = False

        # =========================================================
        # DEFAULT VALUES FOR NEW ENCOUNTERS
        # =========================================================
        if not self.is_bound and not self.instance.pk:
            current_time = (
                timezone.localtime()
                .replace(second=0, microsecond=0)
            )

            self.initial["start_datetime"] = current_time.strftime(
                "%Y-%m-%dT%H:%M"
            )

            self.initial["status"] = Encounter.EncounterStatus.ARRIVED
            self.initial["registration_completed"] = True
            self.initial["identity_verified"] = False
            self.initial["arrived_at"] = current_time.strftime(
                "%Y-%m-%dT%H:%M"
            )
            self.initial["is_active"] = True

            if self.current_user and self.current_user.is_authenticated:
                self.initial["registered_by"] = self.current_user
                self.initial["check_in_user"] = self.current_user

        # =========================================================
        # DISPLAY LABELS
        # =========================================================
        self.fields["registration_completed"].label = (
            "Registration completed"
        )

        self.fields["identity_verified"].label = (
            "Patient identity verified"
        )

        self.fields["registered_at"].label = (
            "Registration completed at"
        )

        self.fields["registered_by"].label = (
            "Registered by"
        )

        self.fields["arrived_at"].label = (
            "Arrival / check-in time"
        )

        self.fields["check_in_user"].label = (
            "Checked in by"
        )

        self.fields["triaged_at"].label = (
            "Triage completed at"
        )

        self.fields["triaged_by"].label = (
            "Triaged by"
        )

        self.fields["clinical_start_at"].label = (
            "Clinical care started at"
        )

        self.fields["completed_at"].label = (
            "Clinical care completed at"
        )

        self.fields["end_datetime"].label = (
            "Encounter ended at"
        )

        # =========================================================
        # TAILWIND CSS CLASSES
        # =========================================================
        standard_field_classes = (
            "block w-full rounded-lg "
            "border border-slate-300 "
            "bg-white px-3 py-2 "
            "text-sm text-slate-900 "
            "shadow-sm outline-none transition "
            "placeholder:text-slate-400 "
            "focus:border-ehr-500 "
            "focus:ring-2 focus:ring-ehr-500/20 "
            "disabled:cursor-not-allowed "
            "disabled:bg-slate-100 "
            "disabled:text-slate-500"
        )

        checkbox_classes = (
            "h-4 w-4 rounded "
            "border-slate-300 "
            "text-ehr-700 "
            "focus:ring-2 "
            "focus:ring-ehr-500/20"
        )

        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = checkbox_classes
            else:
                existing_classes = field.widget.attrs.get("class", "")

                field.widget.attrs["class"] = (
                    f"{existing_classes} {standard_field_classes}".strip()
                )

        # =========================================================
        # FIELD-SPECIFIC ATTRIBUTES
        # =========================================================
        self.fields["patient"].widget.attrs.update(
            {
                "autocomplete": "off",
            }
        )

        self.fields["reason_for_visit"].widget.attrs.update(
            {
                "autocomplete": "off",
            }
        )

        self.fields["notes"].widget.attrs.update(
            {
                "maxlength": "5000",
            }
        )

    def clean(self):
        """
        Validate the full encounter workflow.
        """

        cleaned_data = super().clean()

        status = cleaned_data.get("status")

        registration_completed = cleaned_data.get(
            "registration_completed"
        )
        identity_verified = cleaned_data.get(
            "identity_verified"
        )

        registered_at = cleaned_data.get("registered_at")
        registered_by = cleaned_data.get("registered_by")

        arrived_at = cleaned_data.get("arrived_at")
        check_in_user = cleaned_data.get("check_in_user")

        triaged_at = cleaned_data.get("triaged_at")
        triaged_by = cleaned_data.get("triaged_by")

        start_datetime = cleaned_data.get("start_datetime")
        clinical_start_at = cleaned_data.get("clinical_start_at")
        completed_at = cleaned_data.get("completed_at")
        end_datetime = cleaned_data.get("end_datetime")

        current_time = timezone.now()

        # =========================================================
        # REGISTRATION WORKFLOW
        # =========================================================
        if registration_completed and not registered_at:
            cleaned_data["registered_at"] = current_time
            registered_at = current_time

        if registration_completed and not registered_by:
            if self.current_user and self.current_user.is_authenticated:
                cleaned_data["registered_by"] = self.current_user
                registered_by = self.current_user

        if registered_at and not registration_completed:
            self.add_error(
                "registration_completed",
                (
                    "Mark registration as completed when a registration "
                    "completion time has been entered."
                ),
            )

        if identity_verified and not registration_completed:
            self.add_error(
                "identity_verified",
                (
                    "Registration must be completed before identity "
                    "verification can be confirmed."
                ),
            )

        # =========================================================
        # ARRIVAL AND CHECK-IN WORKFLOW
        # =========================================================
        statuses_requiring_arrival = {
            Encounter.EncounterStatus.ARRIVED,
            Encounter.EncounterStatus.TRIAGED,
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
            Encounter.EncounterStatus.COMPLETED,
        }

        if status in statuses_requiring_arrival and not arrived_at:
            cleaned_data["arrived_at"] = current_time
            arrived_at = current_time

        if (
            status in statuses_requiring_arrival
            and not check_in_user
            and self.current_user
            and self.current_user.is_authenticated
        ):
            cleaned_data["check_in_user"] = self.current_user
            check_in_user = self.current_user

        # =========================================================
        # TRIAGE WORKFLOW
        # =========================================================
        statuses_requiring_triage = {
            Encounter.EncounterStatus.TRIAGED,
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
            Encounter.EncounterStatus.COMPLETED,
        }

        if status in statuses_requiring_triage and not triaged_at:
            cleaned_data["triaged_at"] = current_time
            triaged_at = current_time

        if (
            status in statuses_requiring_triage
            and not triaged_by
            and self.current_user
            and self.current_user.is_authenticated
        ):
            cleaned_data["triaged_by"] = self.current_user
            triaged_by = self.current_user

        if arrived_at and triaged_at and triaged_at < arrived_at:
            self.add_error(
                "triaged_at",
                "Triage cannot be completed before patient arrival.",
            )

        # =========================================================
        # CLINICAL CARE WORKFLOW
        # =========================================================
        statuses_requiring_clinical_start = {
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
            Encounter.EncounterStatus.COMPLETED,
        }

        if (
            status in statuses_requiring_clinical_start
            and not clinical_start_at
        ):
            cleaned_data["clinical_start_at"] = current_time
            clinical_start_at = current_time

        if (
            arrived_at
            and clinical_start_at
            and clinical_start_at < arrived_at
        ):
            self.add_error(
                "clinical_start_at",
                "Clinical care cannot begin before patient arrival.",
            )

        # =========================================================
        # COMPLETION WORKFLOW
        # =========================================================
        if status == Encounter.EncounterStatus.COMPLETED:
            if not completed_at:
                cleaned_data["completed_at"] = current_time
                completed_at = current_time

            if not end_datetime:
                cleaned_data["end_datetime"] = completed_at
                end_datetime = completed_at

        if (
            clinical_start_at
            and completed_at
            and completed_at < clinical_start_at
        ):
            self.add_error(
                "completed_at",
                (
                    "Clinical completion cannot occur before clinical "
                    "care begins."
                ),
            )

        # =========================================================
        # GENERAL DATE VALIDATION
        # =========================================================
        if (
            start_datetime
            and registered_at
            and registered_at < start_datetime
        ):
            self.add_error(
                "registered_at",
                (
                    "Registration completion cannot be earlier than "
                    "the encounter start."
                ),
            )

        if (
            start_datetime
            and arrived_at
            and arrived_at < start_datetime
        ):
            self.add_error(
                "arrived_at",
                (
                    "Patient arrival cannot be earlier than the "
                    "encounter start."
                ),
            )

        if (
            start_datetime
            and end_datetime
            and end_datetime < start_datetime
        ):
            self.add_error(
                "end_datetime",
                "The encounter end time cannot be before the start time.",
            )

        if (
            completed_at
            and end_datetime
            and end_datetime < completed_at
        ):
            self.add_error(
                "end_datetime",
                (
                    "The encounter end time cannot be before the "
                    "clinical completion time."
                ),
            )

        # =========================================================
        # OPEN ENCOUNTER VALIDATION
        # =========================================================
        open_statuses = {
            Encounter.EncounterStatus.PLANNED,
            Encounter.EncounterStatus.SCHEDULED,
            Encounter.EncounterStatus.ARRIVED,
            Encounter.EncounterStatus.TRIAGED,
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
        }

        if status in open_statuses and completed_at:
            self.add_error(
                "completed_at",
                (
                    "Remove the completion time while the encounter "
                    "remains open."
                ),
            )

        if status in open_statuses and end_datetime:
            self.add_error(
                "end_datetime",
                (
                    "Remove the end time while the encounter remains "
                    "open, or change the status to Completed."
                ),
            )

        # =========================================================
        # CANCELLED OR ERROR WORKFLOW
        # =========================================================
        if status in {
            Encounter.EncounterStatus.CANCELLED,
            Encounter.EncounterStatus.ENTERED_IN_ERROR,
        }:
            cleaned_data["is_active"] = False

            if completed_at:
                self.add_error(
                    "completed_at",
                    (
                        "A cancelled or erroneous encounter cannot have "
                        "a clinical completion time."
                    ),
                )

        return cleaned_data