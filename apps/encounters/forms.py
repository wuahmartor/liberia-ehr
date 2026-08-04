"""
Liberia EHR Encounter Forms

File:
apps/encounters/forms.py

Purpose:
- Create and update encounter records.
- Display only fields staff should complete manually.
- Load existing patients for encounter selection.
- Apply Tailwind CSS styling.
- Leave encounter numbers, recorder fields, timestamps, and active-state
  management to the Encounter model.

Important:
- Encounter uses a UUID primary key.
- A UUID may exist before the encounter has been saved.
- The form must therefore receive an explicit form_mode from the view:

      form_mode="create"

  or:

      form_mode="update"
"""

from django import forms
from django.contrib.auth import get_user_model

from apps.patients.models import Patient

from .models import Encounter


User = get_user_model()


class EncounterForm(forms.ModelForm):
    """
    Form used to create and update encounter records.

    Automatically managed fields are excluded from this form.

    The encounter view must save the model with:

        encounter.save(actor=request.user)
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
            "attending_provider",
            "notes",
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
                    "autocomplete": "off",
                }
            ),

            "registration_completed": forms.CheckboxInput(),

            "identity_verified": forms.CheckboxInput(),

            "attending_provider": forms.Select(),

            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "maxlength": "5000",
                    "placeholder": (
                        "Enter relevant clinical or administrative notes"
                    ),
                }
            ),
        }

        labels = {
            "patient": "Patient",
            "encounter_type": "Encounter type",
            "status": "Encounter status",
            "priority": "Priority",
            "reason_for_visit": "Reason for visit",
            "registration_completed": "Registration completed",
            "identity_verified": "Patient identity verified",
            "attending_provider": "Attending provider",
            "notes": "Encounter notes",
        }

        help_texts = {
            "patient": (
                "Select the patient receiving care during this encounter."
            ),
            "encounter_type": (
                "Select the type or setting of care being provided."
            ),
            "status": (
                "Select the current stage of the encounter workflow."
            ),
            "priority": (
                "Select the urgency of the encounter."
            ),
            "reason_for_visit": (
                "Enter the chief complaint or primary reason for care."
            ),
            "registration_completed": (
                "The responsible user, date, and time are recorded "
                "automatically."
            ),
            "identity_verified": (
                "The responsible user, date, and time are recorded "
                "automatically."
            ),
            "attending_provider": (
                "Select the primary provider responsible for this encounter."
            ),
            "notes": (
                "Enter optional clinical or administrative notes."
            ),
        }

    def __init__(self, *args, **kwargs):
        """
        Configure form mode, patient choices, provider choices,
        workflow defaults, and Tailwind CSS classes.
        """

        self.current_user = kwargs.pop(
            "current_user",
            None,
        )

        self.form_mode = kwargs.pop(
            "form_mode",
            "create",
        )

        super().__init__(*args, **kwargs)

        # =============================================================
        # CREATE OR UPDATE MODE
        # =============================================================

        valid_modes = {
            "create",
            "update",
        }

        if self.form_mode not in valid_modes:
            self.form_mode = "create"

        self.is_create = self.form_mode == "create"
        self.is_update = self.form_mode == "update"

        # =============================================================
        # PATIENT QUERYSET
        # =============================================================

        patient_queryset = Patient.objects.all().order_by(
            "last_name",
            "first_name",
            "middle_name",
        )

        self.fields["patient"].queryset = patient_queryset
        self.fields["patient"].required = True
        self.fields["patient"].empty_label = "Select a patient"

        if self.is_update:
            self.fields["patient"].disabled = True

            self.fields["patient"].help_text = (
                "The patient cannot be changed after the encounter "
                "has been created."
            )

        else:
            self.fields["patient"].disabled = False

            self.fields["patient"].help_text = (
                "Select the patient receiving care during this encounter."
            )

        # =============================================================
        # ATTENDING PROVIDER QUERYSET
        # =============================================================

        active_users = User.objects.filter(
            is_active=True,
        ).order_by(
            "first_name",
            "last_name",
            "username",
        )

        self.fields["attending_provider"].queryset = active_users
        self.fields["attending_provider"].required = False
        self.fields["attending_provider"].empty_label = (
            "Select attending provider"
        )

        # =============================================================
        # STATUS CHOICES
        # =============================================================

        editable_statuses = {
            Encounter.EncounterStatus.PLANNED,
            Encounter.EncounterStatus.SCHEDULED,
            Encounter.EncounterStatus.ARRIVED,
            Encounter.EncounterStatus.TRIAGED,
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
        }

        terminal_statuses = {
            Encounter.EncounterStatus.COMPLETED,
            Encounter.EncounterStatus.CANCELLED,
            Encounter.EncounterStatus.ENTERED_IN_ERROR,
        }

        self.fields["status"].choices = [
            choice
            for choice in Encounter.EncounterStatus.choices
            if choice[0] in editable_statuses
        ]

        if (
            self.is_update
            and self.instance.status in terminal_statuses
        ):
            current_status_choice = next(
                (
                    choice
                    for choice in Encounter.EncounterStatus.choices
                    if choice[0] == self.instance.status
                ),
                None,
            )

            if current_status_choice:
                self.fields["status"].choices = [
                    current_status_choice,
                ]

            self.fields["status"].disabled = True

            self.fields["status"].help_text = (
                "This encounter has a final status and cannot be reopened "
                "through the update form."
            )

        else:
            self.fields["status"].disabled = False

        # =============================================================
        # DEFAULT VALUES FOR NEW ENCOUNTERS
        # =============================================================

        if not self.is_bound and self.is_create:
            self.initial.setdefault(
                "encounter_type",
                Encounter.EncounterType.OUTPATIENT,
            )

            self.initial.setdefault(
                "status",
                Encounter.EncounterStatus.ARRIVED,
            )

            self.initial.setdefault(
                "priority",
                Encounter.Priority.ROUTINE,
            )

            self.initial.setdefault(
                "registration_completed",
                True,
            )

            self.initial.setdefault(
                "identity_verified",
                False,
            )

        # =============================================================
        # FIELD REQUIREMENTS
        # =============================================================

        self.fields["patient"].required = True
        self.fields["encounter_type"].required = True
        self.fields["status"].required = True
        self.fields["priority"].required = True

        self.fields["reason_for_visit"].required = False
        self.fields["registration_completed"].required = False
        self.fields["identity_verified"].required = False
        self.fields["attending_provider"].required = False
        self.fields["notes"].required = False

        # =============================================================
        # TAILWIND CSS CLASSES
        # =============================================================

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
            "disabled:border-slate-200 "
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
            if isinstance(
                field.widget,
                forms.CheckboxInput,
            ):
                field.widget.attrs["class"] = checkbox_classes

            else:
                existing_classes = field.widget.attrs.get(
                    "class",
                    "",
                )

                field.widget.attrs["class"] = (
                    f"{existing_classes} "
                    f"{standard_field_classes}"
                ).strip()

        # =============================================================
        # FIELD-SPECIFIC ATTRIBUTES
        # =============================================================

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

    def clean_patient(self):
        """
        Prevent an existing encounter from being reassigned to another
        patient.
        """

        patient = self.cleaned_data.get("patient")

        if (
            self.is_update
            and self.instance.patient_id
            and patient
            and patient.pk != self.instance.patient_id
        ):
            raise forms.ValidationError(
                "The patient assigned to an existing encounter cannot "
                "be changed."
            )

        return patient

    def clean_status(self):
        """
        Prevent terminal statuses from being selected through the normal
        create or update form.
        """

        status = self.cleaned_data.get("status")

        terminal_statuses = {
            Encounter.EncounterStatus.COMPLETED,
            Encounter.EncounterStatus.CANCELLED,
            Encounter.EncounterStatus.ENTERED_IN_ERROR,
        }

        if self.is_create and status in terminal_statuses:
            raise forms.ValidationError(
                "A new encounter cannot begin with a final status."
            )

        if (
            self.is_update
            and self.instance.status in terminal_statuses
            and status != self.instance.status
        ):
            raise forms.ValidationError(
                "A completed, cancelled, or erroneous encounter cannot "
                "be reopened through this form."
            )

        return status

    def clean(self):
        """
        Validate manually entered encounter information.

        Automatically generated workflow timestamps and recorder fields
        are handled by the Encounter model.
        """

        cleaned_data = super().clean()

        encounter_type = cleaned_data.get(
            "encounter_type"
        )

        status = cleaned_data.get(
            "status"
        )

        registration_completed = cleaned_data.get(
            "registration_completed"
        )

        identity_verified = cleaned_data.get(
            "identity_verified"
        )

        attending_provider = cleaned_data.get(
            "attending_provider"
        )

        # =============================================================
        # IDENTITY VERIFICATION
        # =============================================================

        if (
            identity_verified
            and not registration_completed
            and encounter_type
            != Encounter.EncounterType.EMERGENCY
        ):
            self.add_error(
                "identity_verified",
                (
                    "Complete registration before confirming identity "
                    "verification."
                ),
            )

        # =============================================================
        # TRIAGE
        # =============================================================

        encounters_without_formal_triage = {
            Encounter.EncounterType.LABORATORY,
            Encounter.EncounterType.IMAGING,
            Encounter.EncounterType.PHARMACY,
        }

        if (
            encounter_type in encounters_without_formal_triage
            and status == Encounter.EncounterStatus.TRIAGED
        ):
            self.add_error(
                "status",
                (
                    "This encounter type does not normally require "
                    "formal triage."
                ),
            )

        # =============================================================
        # ATTENDING PROVIDER
        # =============================================================

        provider_required_statuses = {
            Encounter.EncounterStatus.IN_PROGRESS,
            Encounter.EncounterStatus.ON_HOLD,
        }

        provider_required_types = {
            Encounter.EncounterType.OUTPATIENT,
            Encounter.EncounterType.INPATIENT,
            Encounter.EncounterType.EMERGENCY,
            Encounter.EncounterType.OBSERVATION,
            Encounter.EncounterType.TELEHEALTH,
            Encounter.EncounterType.HOME_VISIT,
            Encounter.EncounterType.COMMUNITY,
            Encounter.EncounterType.MATERNITY,
            Encounter.EncounterType.SURGICAL,
        }

        if (
            status in provider_required_statuses
            and encounter_type in provider_required_types
            and not attending_provider
        ):
            self.add_error(
                "attending_provider",
                (
                    "Select an attending provider before placing the "
                    "encounter in progress or on hold."
                ),
            )

        return cleaned_data