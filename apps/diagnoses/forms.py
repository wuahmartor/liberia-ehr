from typing import ClassVar

from django import forms
from django.core.exceptions import ValidationError

from apps.encounters.models import Encounter

from .models import PatientDiagnosis, PatientProcedure, ProcedureCode

CONTROL = "w-full rounded-md border border-slate-300 bg-white px-2.5 py-2 text-xs text-slate-900 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"


class PatientDiagnosisForm(forms.ModelForm):
    concept_query = forms.CharField(
        label="ICD-10-CM diagnosis",
        required=False,
        help_text="Search by code or clinical description, then select a result.",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "Example: E11.9 or type 2 diabetes",
                "class": CONTROL,
            }
        ),
    )

    class Meta:
        model = PatientDiagnosis
        fields = (
            "concept",
            "encounter",
            "diagnosis_type",
            "clinical_status",
            "verification_status",
            "severity",
            "diagnosed_on",
            "onset_date",
            "resolved_on",
            "is_current_problem",
            "is_sensitive",
            "notes",
        )
        widgets: ClassVar[dict] = {
            "concept": forms.HiddenInput(),
            "encounter": forms.Select(attrs={"class": CONTROL}),
            "diagnosis_type": forms.Select(attrs={"class": CONTROL}),
            "clinical_status": forms.Select(attrs={"class": CONTROL}),
            "verification_status": forms.Select(attrs={"class": CONTROL}),
            "severity": forms.Select(attrs={"class": CONTROL}),
            "diagnosed_on": forms.DateInput(attrs={"type": "date", "class": CONTROL}),
            "onset_date": forms.DateInput(attrs={"type": "date", "class": CONTROL}),
            "resolved_on": forms.DateInput(attrs={"type": "date", "class": CONTROL}),
            "notes": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": CONTROL,
                    "placeholder": "Clinical context, supporting findings, or follow-up plan",
                }
            ),
            "is_current_problem": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-slate-300 text-blue-700"}
            ),
            "is_sensitive": forms.CheckboxInput(
                attrs={"class": "h-4 w-4 rounded border-slate-300 text-blue-700"}
            ),
        }

    def __init__(self, *args, patient=None, encounter=None, **kwargs):
        super().__init__(*args, **kwargs)
        # ModelForm runs model.clean() during is_valid(). Attach the patient
        # before that validation so encounter ownership is compared against
        # the actual chart rather than a new instance with patient_id=None.
        if patient is not None:
            self.instance.patient = patient
        self.fields["encounter"].queryset = (
            Encounter.objects.filter(patient=patient).order_by("-start_datetime")
            if patient
            else Encounter.objects.none()
        )
        if encounter:
            self.initial["encounter"] = encounter.pk
        if self.instance.pk and self.instance.concept_id:
            self.initial["concept_query"] = str(self.instance.concept)

    def clean_concept(self):
        concept = self.cleaned_data.get("concept")
        if not concept:
            raise ValidationError("Select an ICD-10-CM result from the search list.")
        if (
            not concept.is_active
            or concept.source.source_type != concept.source.SourceType.ICD_10
        ):
            raise ValidationError("Select an active ICD-10-CM concept.")
        return concept

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("clinical_status") in {
            PatientDiagnosis.DiagnosisStatus.RESOLVED,
            PatientDiagnosis.DiagnosisStatus.INACTIVE,
        } and not cleaned.get("resolved_on"):
            self.add_error(
                "resolved_on",
                "Enter the resolution date for a resolved or inactive diagnosis.",
            )
        if (
            cleaned.get("clinical_status")
            == PatientDiagnosis.DiagnosisStatus.ENTERED_IN_ERROR
        ):
            self.add_error(
                "clinical_status",
                "Use the Entered in error action so the reason is captured.",
            )
        return cleaned


class DiagnosisErrorForm(forms.Form):
    reason = forms.CharField(
        label="Reason",
        min_length=5,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": CONTROL,
                "placeholder": "Explain why this diagnosis was entered in error",
            }
        ),
    )


class PatientProcedureForm(forms.ModelForm):
    procedure_query = forms.CharField(
        label="CPT procedure",
        required=False,
        help_text="Search the organization's licensed CPT catalog and select a result.",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "placeholder": "Search CPT code or procedure description",
                "class": CONTROL,
            }
        ),
    )

    class Meta:
        model = PatientProcedure
        fields = (
            "procedure_code",
            "encounter",
            "status",
            "performed_on",
            "performed_by",
            "notes",
        )
        widgets: ClassVar[dict] = {
            "procedure_code": forms.HiddenInput(),
            "encounter": forms.Select(attrs={"class": CONTROL}),
            "status": forms.Select(attrs={"class": CONTROL}),
            "performed_on": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": CONTROL}
            ),
            "performed_by": forms.Select(attrs={"class": CONTROL}),
            "notes": forms.Textarea(attrs={"rows": 4, "class": CONTROL}),
        }

    def __init__(self, *args, patient=None, encounter=None, **kwargs):
        super().__init__(*args, **kwargs)
        if patient is not None:
            self.instance.patient = patient
        self.fields["encounter"].queryset = (
            Encounter.objects.filter(patient=patient).order_by("-start_datetime")
            if patient
            else Encounter.objects.none()
        )
        if encounter:
            self.initial["encounter"] = encounter.pk
        if self.instance.pk and self.instance.procedure_code_id:
            self.initial["procedure_query"] = str(self.instance.procedure_code)

    def clean_procedure_code(self):
        code = self.cleaned_data.get("procedure_code")
        if not code:
            raise ValidationError(
                "Select a procedure from the licensed CPT search results."
            )
        if code.code_system != ProcedureCode.CodeSystem.CPT or not code.is_active:
            raise ValidationError("Select an active CPT procedure code.")
        return code
