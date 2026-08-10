from django import forms

from apps.pharmacy.models import Medication

from .models import MedicationOrder


class MedicationOrderForm(forms.ModelForm):
    class Meta:
        model = MedicationOrder
        fields = (
            "medication",
            "dose",
            "route",
            "frequency",
            "quantity",
            "instructions",
        )
        widgets = {
            "medication": forms.Select(
                attrs={
                    "data-medication-select": "",
                    "data-medication-api": "/pharmacy/api/medications/",
                }
            ),
            "route": forms.TextInput(
                attrs={"data-medication-route": ""},
            ),
            "instructions": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["medication"].queryset = Medication.objects.active()
