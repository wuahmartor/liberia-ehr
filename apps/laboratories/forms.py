from django import forms

from apps.diagnoses.models import PatientDiagnosis
from .models import LabOrder, LabPanel, LabResult, LabTestDefinition

INPUT = "w-full rounded-md border border-slate-300 px-2 py-1.5 text-xs focus:border-emerald-500"


class LabOrderForm(forms.Form):
    indication_diagnosis = forms.ModelChoiceField(label="Clinical indication (ICD diagnosis)", queryset=PatientDiagnosis.objects.none(), widget=forms.Select(attrs={"class": INPUT}))
    panel = forms.ModelChoiceField(required=False, queryset=LabPanel.objects.none(), empty_label="Select a panel (optional)", widget=forms.Select(attrs={"class": INPUT}))
    standalone_tests = forms.ModelMultipleChoiceField(required=False, queryset=LabTestDefinition.objects.none(), widget=forms.SelectMultiple(attrs={"class": f"{INPUT} min-h-40"}), help_text="Select individual tests when a complete panel is not needed.")
    priority = forms.ChoiceField(choices=LabOrder.Priority.choices, widget=forms.Select(attrs={"class": INPUT}))
    clinical_indication = forms.CharField(label="Additional indication details", required=False, max_length=500, widget=forms.Textarea(attrs={"class": INPUT, "rows": 2}))
    def __init__(self, *args, patient, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["panel"].queryset = LabPanel.objects.filter(is_active=True).prefetch_related("tests")
        self.fields["standalone_tests"].queryset = LabTestDefinition.objects.filter(is_active=True)
        self.fields["indication_diagnosis"].queryset = patient.diagnoses.filter(clinical_status__in=(PatientDiagnosis.DiagnosisStatus.ACTIVE, PatientDiagnosis.DiagnosisStatus.RECURRENCE)).exclude(verification_status=PatientDiagnosis.VerificationStatus.REFUTED).select_related("concept")
        self.fields["indication_diagnosis"].label_from_instance = lambda diagnosis: f"{diagnosis.code_snapshot or diagnosis.concept.code} — {diagnosis.display_snapshot}"

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("panel") and not cleaned.get("standalone_tests"):
            raise forms.ValidationError("Select a panel or at least one standalone laboratory test.")
        return cleaned


class LabResultForm(forms.Form):
    numeric_value = forms.DecimalField(max_digits=14, decimal_places=4, widget=forms.NumberInput(attrs={"class": INPUT, "step": "any"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": INPUT, "rows": 2}))
