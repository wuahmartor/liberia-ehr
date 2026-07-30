
from __future__ import annotations

from django import forms

from .models import (
    EmergencyContact,
    InsuranceCoverage,
    Patient,
    PatientAddress,
    PatientAlias,
    PatientConsent,
    PatientContactPoint,
    PatientFlag,
    PatientIdentifier,
    PatientMergeRecord,
    PatientRelationship,
)


class TailwindModelForm(forms.ModelForm):
    """
    Adds compact Tailwind classes without requiring django-widget-tweaks.
    """

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
            widget = field.widget

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = self.checkbox_class
            else:
                existing = widget.attrs.get("class", "")
                widget.attrs["class"] = f"{existing} {self.input_class}".strip()

            if isinstance(widget, forms.Textarea):
                widget.attrs.setdefault("rows", 3)


class PatientForm(TailwindModelForm):
    class Meta:
        model = Patient
        fields = (
            "mrn",
            "first_name",
            "middle_name",
            "last_name",
            "previous_last_name",
            "preferred_name",
            "prefix",
            "suffix",
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
            "occupation",
            "employer",
            "education_level",
            "religion",
            "registration_facility",
            "record_status",
            "is_active",
            "is_deceased",
            "deceased_at",
            "deceased_status_verified",
            "confidential_record",
            "restricted_access_reason",
            "registration_notes",
        )
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "deceased_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }


class PatientIdentifierForm(TailwindModelForm):
    class Meta:
        model = PatientIdentifier
        fields = (
            "identifier_type",
            "value",
            "issuing_authority",
            "facility",
            "issued_on",
            "expires_on",
            "is_primary",
            "is_verified",
            "is_active",
        )
        widgets = {
            "issued_on": forms.DateInput(attrs={"type": "date"}),
            "expires_on": forms.DateInput(attrs={"type": "date"}),
        }


class PatientAliasForm(TailwindModelForm):
    class Meta:
        model = PatientAlias
        fields = (
            "first_name",
            "middle_name",
            "last_name",
            "reason",
            "is_active",
        )


class PatientAddressForm(TailwindModelForm):
    class Meta:
        model = PatientAddress
        fields = (
            "address_type",
            "line_1",
            "line_2",
            "community_or_town",
            "district",
            "county_or_state",
            "postal_code",
            "country",
            "directions_or_landmark",
            "latitude",
            "longitude",
            "valid_from",
            "valid_to",
            "is_primary",
            "is_active",
        )
        widgets = {
            "valid_from": forms.DateInput(attrs={"type": "date"}),
            "valid_to": forms.DateInput(attrs={"type": "date"}),
        }


from .models import PatientAllergy


# ============================================================
# PATIENT ALLERGY FORM
# ============================================================

class PatientAllergyForm(forms.ModelForm):
    """
    Creates and updates a patient's allergy or intolerance record.

    The patient is assigned in the view and is intentionally excluded
    from the visible form.
    """

    class Meta:
        model = PatientAllergy

        fields = (
            "allergy_type",
            "substance",
            "reaction",
            "severity",
            "status",
            "verification_status",
            "onset_date",
            "recorded_date",
            "notes",
        )

        widgets = {
            "allergy_type": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                },
            ),
            "substance": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm placeholder:text-slate-400 "
                        "focus:border-red-500 focus:ring-red-500"
                    ),
                    "placeholder": (
                        "Example: Penicillin, peanuts, latex"
                    ),
                    "autocomplete": "off",
                },
            ),
            "reaction": forms.TextInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm placeholder:text-slate-400 "
                        "focus:border-red-500 focus:ring-red-500"
                    ),
                    "placeholder": (
                        "Example: Hives, swelling, anaphylaxis"
                    ),
                    "autocomplete": "off",
                },
            ),
            "severity": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                },
            ),
            "status": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                },
            ),
            "verification_status": forms.Select(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                },
            ),
            "onset_date": forms.DateInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                    "type": "date",
                },
            ),
            "recorded_date": forms.DateInput(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm focus:border-red-500 "
                        "focus:ring-red-500"
                    ),
                    "type": "date",
                },
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": (
                        "block w-full rounded-md border-slate-300 "
                        "bg-white px-3 py-2 text-sm text-slate-900 "
                        "shadow-sm placeholder:text-slate-400 "
                        "focus:border-red-500 focus:ring-red-500"
                    ),
                    "rows": 3,
                    "placeholder": (
                        "Enter additional clinical information."
                    ),
                },
            ),
        }

    def clean_substance(self) -> str:
        substance = self.cleaned_data.get("substance", "").strip()

        if not substance:
            raise forms.ValidationError(
                "Enter the substance or allergen."
            )

        return substance

    def clean_reaction(self) -> str:
        return self.cleaned_data.get("reaction", "").strip()

    def clean_notes(self) -> str:
        return self.cleaned_data.get("notes", "").strip()

class PatientContactPointForm(TailwindModelForm):
    class Meta:
        model = PatientContactPoint
        fields = (
            "contact_type",
            "use_type",
            "value",
            "extension",
            "notes",
            "is_primary",
            "is_verified",
            "is_active",
            "sort_order",
        )


class EmergencyContactForm(TailwindModelForm):
    class Meta:
        model = EmergencyContact
        fields = (
            "full_name",
            "relationship",
            "phone_number",
            "alternate_phone",
            "email",
            "address",
            "is_next_of_kin",
            "is_legal_guardian",
            "may_receive_information",
            "may_make_decisions",
            "is_primary",
            "is_active",
        )


class PatientRelationshipForm(TailwindModelForm):
    class Meta:
        model = PatientRelationship
        fields = (
            "related_patient",
            "relationship_type",
            "notes",
            "is_active",
        )


class PatientConsentForm(TailwindModelForm):
    class Meta:
        model = PatientConsent
        fields = (
            "consent_type",
            "status",
            "effective_from",
            "effective_until",
            "withdrawn_at",
            "granted_by_patient",
            "representative_name",
            "representative_relationship",
            "scope",
            "notes",
            "document_reference",
        )
        widgets = {
            "effective_from": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "effective_until": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "withdrawn_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }


class InsuranceCoverageForm(TailwindModelForm):
    class Meta:
        model = InsuranceCoverage
        fields = (
            "payer_name",
            "plan_name",
            "member_number",
            "group_number",
            "policy_holder_name",
            "relationship_to_policy_holder",
            "effective_from",
            "effective_until",
            "status",
            "is_primary",
            "is_verified",
            "verification_notes",
        )
        widgets = {
            "effective_from": forms.DateInput(attrs={"type": "date"}),
            "effective_until": forms.DateInput(attrs={"type": "date"}),
        }


class PatientFlagForm(TailwindModelForm):
    class Meta:
        model = PatientFlag
        fields = (
            "title",
            "description",
            "severity",
            "starts_at",
            "ends_at",
            "requires_acknowledgment",
            "is_active",
        )
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "ends_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }


class PatientMergeRecordForm(TailwindModelForm):
    class Meta:
        model = PatientMergeRecord
        fields = (
            "surviving_patient",
            "duplicate_patient",
            "reason",
            "status",
            "reviewed_by",
            "reviewed_at",
            "completed_at",
            "reversal_reason",
        )
        widgets = {
            "reviewed_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
            "completed_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}
            ),
        }
