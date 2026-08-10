from __future__ import annotations

from django import forms

from apps.pharmacy.models import Medication

from .models import MedicationOrder

# ============================================================

# SHARED ORDER FIELD STYLES

# ============================================================

INPUT_CLASS = (

    "block h-8 w-full rounded-md "

    "border border-slate-300 bg-white "

    "px-2 text-xs text-slate-900 "

    "outline-none "

    "focus:border-emerald-500 "

    "focus:ring-1 focus:ring-emerald-500"

)

SELECT_CLASS = (

    "block h-8 w-full rounded-md "

    "border border-slate-300 bg-white "

    "px-2 text-xs text-slate-900 "

    "outline-none "

    "focus:border-emerald-500 "

    "focus:ring-1 focus:ring-emerald-500"

)

TEXTAREA_CLASS = (

    "block min-h-16 w-full resize-y rounded-md "

    "border border-slate-300 bg-white "

    "px-2 py-1.5 text-xs text-slate-900 "

    "outline-none "

    "focus:border-emerald-500 "

    "focus:ring-1 focus:ring-emerald-500"

)

# ============================================================

# MEDICATION ORDER FORM

# ============================================================

class MedicationOrderForm(forms.ModelForm):

    """

    Provider medication-order entry form.

    Pharmacy owns Medication.

    Orders owns MedicationOrder.

    The visible medication search is handled by the medication

    picker JavaScript.

    The actual submitted medication value remains this Django

    ModelChoiceField and therefore must reference a local

    pharmacy.Medication record.

    """

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

                    "class": SELECT_CLASS,

                    # Used by medication_picker_script.html.

                    "data-medication-select": "",

                    # Local Pharmacy medication search.

                    "data-medication-api": (

                        "/pharmacy/api/medications/"

                    ),

                    # External RxNorm search.

                    "data-us-medication-api": (

                        "/pharmacy/api/us-medications/"

                    ),

                    # Convert selected RxNorm medication into a

                    # local pharmacy.Medication record.

                    "data-us-medication-import-api": (

                        "/pharmacy/api/us-medications/import/"

                    ),

                }

            ),

            "dose": forms.TextInput(

                attrs={

                    "class": INPUT_CLASS,

                    "autocomplete": "off",

                    "placeholder": "e.g. 500 mg",

                }

            ),

            "route": forms.TextInput(

                attrs={

                    "class": INPUT_CLASS,

                    "autocomplete": "off",

                    "placeholder": "e.g. Oral",

                    "data-medication-route": "",

                }

            ),

            "frequency": forms.TextInput(

                attrs={

                    "class": INPUT_CLASS,

                    "autocomplete": "off",

                    "placeholder": "e.g. BID",

                }

            ),

            "quantity": forms.NumberInput(

                attrs={

                    "class": INPUT_CLASS,

                    "min": "0",

                    "step": "0.001",

                    "placeholder": "Optional",

                }

            ),

            "instructions": forms.Textarea(

                attrs={

                    "class": TEXTAREA_CLASS,

                    "rows": 2,

                    "placeholder": (

                        "Additional administration instructions"

                    ),

                }

            ),

        }

    # ========================================================

    # INITIALIZATION

    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        medication_field = self.fields["medication"]

        medication_field.queryset = (

            Medication.objects

            .active()

            .order_by(

                "generic_name",

                "brand_name",

                "strength",

                "dosage_form",

                "code",

            )

        )

        medication_field.empty_label = (

            "Search or select medication"

        )

        medication_field.help_text = (

            "Type at least 4 letters to search medications. "

            "Local formulary medications can be selected directly. "

            "RxNorm medications are converted to a local medication "

            "record when selected."

        )

    # ========================================================

    # MEDICATION VALIDATION

    # ========================================================

    def clean_medication(self):

        medication = self.cleaned_data.get("medication")

        if medication is None:

            raise forms.ValidationError(

                "Select a medication."

            )

        if not medication.is_active:

            raise forms.ValidationError(

                "This medication is not currently available for ordering."

            )

        if medication.is_retired:

            raise forms.ValidationError(

                "A retired medication cannot be ordered."

            )

        return medication

    # ========================================================

    # TEXT NORMALIZATION

    # ========================================================

    def clean_dose(self):

        value = self.cleaned_data.get("dose") or ""

        return " ".join(

            value.split()

        ).strip()

    def clean_route(self):

        value = self.cleaned_data.get("route") or ""

        return " ".join(

            value.split()

        ).strip()

    def clean_frequency(self):

        value = self.cleaned_data.get("frequency") or ""

        return " ".join(

            value.split()

        ).strip()

    def clean_instructions(self):

        return (

            self.cleaned_data.get("instructions")

            or ""

        ).strip()