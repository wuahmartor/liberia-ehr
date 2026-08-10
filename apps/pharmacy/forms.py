from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Medication


# ============================================================
# SHARED TAILWIND CLASSES
# ============================================================


INPUT_CLASS = (
    "block w-full rounded-md border border-slate-300 "
    "bg-white px-2.5 py-2 text-sm text-slate-900 "
    "shadow-sm outline-none "
    "focus:border-emerald-500 focus:ring-2 "
    "focus:ring-emerald-500/20"
)

SELECT_CLASS = INPUT_CLASS

TEXTAREA_CLASS = (
    "block w-full rounded-md border border-slate-300 "
    "bg-white px-2.5 py-2 text-sm text-slate-900 "
    "shadow-sm outline-none "
    "focus:border-emerald-500 focus:ring-2 "
    "focus:ring-emerald-500/20"
)

CHECKBOX_CLASS = (
    "h-4 w-4 rounded border-slate-300 "
    "text-emerald-600 "
    "focus:ring-emerald-500"
)


# ============================================================
# MEDICATION FORM
# ============================================================


class MedicationForm(forms.ModelForm):
    """
    Formulary medication maintenance form.

    Inventory fields remain temporarily because the existing application
    stores aggregate pharmacy quantities on Medication.
    """

    class Meta:
        model = Medication

        fields = (
            # Identification
            "code",
            "terminology_source",
            "rxnorm_rxcui",

            # Medication identity
            "generic_name",
            "brand_name",
            "strength",
            "dosage_form",
            "route",
            "therapeutic_class",

            # Formulary
            "formulary_status",
            "is_active",
            "requires_prescription",

            # Safety
            "is_controlled",
            "controlled_substance_class",
            "is_high_alert",
            "is_lasa",
            "safety_notes",

            # Inventory
            "unit_of_measure",
            "reorder_level",
            "quantity_on_hand",
        )

        widgets = {
            "code": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. MED-000123",
                }
            ),

            "terminology_source": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),

            "rxnorm_rxcui": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "inputmode": "numeric",
                    "autocomplete": "off",
                    "placeholder": "RxNorm RxCUI",
                }
            ),

            "generic_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. Amoxicillin",
                }
            ),

            "brand_name": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "Optional brand/trade name",
                }
            ),

            "strength": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. 500 mg",
                }
            ),

            "dosage_form": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. Capsule",
                }
            ),

            "route": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. Oral",
                }
            ),

            "therapeutic_class": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. Penicillin antibiotic",
                }
            ),

            "formulary_status": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                }
            ),

            "is_active": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "requires_prescription": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "is_controlled": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "controlled_substance_class": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": (
                        "Jurisdiction-specific schedule/classification"
                    ),
                }
            ),

            "is_high_alert": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "is_lasa": forms.CheckboxInput(
                attrs={
                    "class": CHECKBOX_CLASS,
                }
            ),

            "safety_notes": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 3,
                    "placeholder": (
                        "Local medication safety or handling information"
                    ),
                }
            ),

            "unit_of_measure": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "autocomplete": "off",
                    "placeholder": "e.g. tablet, vial, bottle",
                }
            ),

            "reorder_level": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "step": "0.001",
                }
            ),

            "quantity_on_hand": forms.NumberInput(
                attrs={
                    "class": INPUT_CLASS,
                    "min": "0",
                    "step": "0.001",
                }
            ),
        }

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["rxnorm_rxcui"].required = False
        self.fields["brand_name"].required = False
        self.fields["therapeutic_class"].required = False
        self.fields["controlled_substance_class"].required = False
        self.fields["safety_notes"].required = False

    # ========================================================
    # FIELD VALIDATION
    # ========================================================

    def clean_code(self):
        code = self.cleaned_data.get("code", "")

        return code.strip().upper()

    def clean_generic_name(self):
        value = self.cleaned_data.get(
            "generic_name",
            "",
        )

        return " ".join(value.split()).strip()

    def clean_brand_name(self):
        value = self.cleaned_data.get(
            "brand_name",
            "",
        )

        return " ".join(value.split()).strip()

    def clean_rxnorm_rxcui(self):
        value = (
            self.cleaned_data.get("rxnorm_rxcui")
            or ""
        ).strip()

        if not value:
            return None

        if not value.isdigit():
            raise ValidationError(
                "RxNorm RxCUI must contain only numeric characters."
            )

        return value

    def clean_reorder_level(self):
        value = self.cleaned_data.get(
            "reorder_level",
        )

        if value is None:
            return Decimal("0")

        if value < 0:
            raise ValidationError(
                "Reorder level cannot be negative."
            )

        return value

    def clean_quantity_on_hand(self):
        value = self.cleaned_data.get(
            "quantity_on_hand",
        )

        if value is None:
            return Decimal("0")

        if value < 0:
            raise ValidationError(
                "Quantity on hand cannot be negative."
            )

        return value

    # ========================================================
    # CROSS-FIELD VALIDATION
    # ========================================================

    def clean(self):
        cleaned_data = super().clean()

        source = cleaned_data.get(
            "terminology_source"
        )

        rxcui = cleaned_data.get(
            "rxnorm_rxcui"
        )

        is_controlled = cleaned_data.get(
            "is_controlled",
            False,
        )

        controlled_class = (
            cleaned_data.get(
                "controlled_substance_class"
            )
            or ""
        ).strip()

        formulary_status = cleaned_data.get(
            "formulary_status"
        )

        # ----------------------------------------------------
        # RxNorm
        # ----------------------------------------------------

        if (
            source
            == Medication.TerminologySource.RXNORM
            and not rxcui
        ):
            self.add_error(
                "rxnorm_rxcui",
                (
                    "RxNorm RxCUI is required when the terminology "
                    "source is RxNorm."
                ),
            )

        # ----------------------------------------------------
        # Controlled medication
        # ----------------------------------------------------

        if not is_controlled:
            cleaned_data[
                "controlled_substance_class"
            ] = ""

        elif not controlled_class:
            # This is intentionally advisory rather than always required.
            # Different jurisdictions may have different classification
            # systems and not every controlled drug will initially have
            # its classification loaded.
            cleaned_data[
                "controlled_substance_class"
            ] = ""

        # ----------------------------------------------------
        # Retirement
        # ----------------------------------------------------

        if (
            formulary_status
            == Medication.FormularyStatus.RETIRED
        ):
            cleaned_data["is_active"] = False

        return cleaned_data