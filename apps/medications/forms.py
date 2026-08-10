from django import forms
from django.utils import timezone

from apps.pharmacy.models import Medication

from .models import MedicationAdministration


class MedicationAdministrationForm(forms.ModelForm):
    class Meta:
        model = MedicationAdministration
        fields = (
            "medication",
            "dose_administered",
            "route",
            "status",
            "reason",
            "administered_at",
        )
        widgets = {
            "medication": forms.Select(
                attrs={
                    "data-medication-select": "",
                    "data-medication-api": "/pharmacy/api/medications/",
                    "data-us-medication-api": "/pharmacy/api/us-medications/",
                    "data-us-medication-import-api": "/pharmacy/api/us-medications/import/",
                }
            ),
            "route": forms.TextInput(
                attrs={"data-medication-route": ""},
            ),
            "reason": forms.Textarea(attrs={"rows": 3}),
            "administered_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medication"].queryset = Medication.objects.active()
        if not self.is_bound and not self.instance.pk:
            self.initial["administered_at"] = timezone.localtime().strftime(
                "%Y-%m-%dT%H:%M"
            )
