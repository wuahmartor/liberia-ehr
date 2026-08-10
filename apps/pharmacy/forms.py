from django import forms

from .models import Medication


class MedicationForm(forms.ModelForm):
    class Meta:
        model = Medication
        fields = (
            "code",
            "generic_name",
            "brand_name",
            "dosage_form",
            "strength",
            "route",
            "unit_of_measure",
            "is_active",
            "requires_prescription",
            "is_controlled",
            "reorder_level",
            "quantity_on_hand",
        )

