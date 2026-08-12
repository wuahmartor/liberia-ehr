from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.pharmacy.models import Medication

from .models import MedicationOrder

# ============================================================

# TAILWIND FIELD CLASSES

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

    "block min-h-20 w-full rounded-md "

    "border border-slate-300 bg-white "

    "px-2 py-2 text-xs text-slate-900 "

    "outline-none "

    "focus:border-emerald-500 "

    "focus:ring-1 focus:ring-emerald-500"

)

DATE_TIME_CLASS = (

    "block h-8 w-full rounded-md "

    "border border-slate-300 bg-white "

    "px-2 text-xs text-slate-900 "

    "outline-none "

    "focus:border-emerald-500 "

    "focus:ring-1 focus:ring-emerald-500"

)

# ============================================================

# MEDICATION ORDER FORM

# ============================================================

class MedicationOrderForm(

    forms.ModelForm,

):

    class Meta:

        model = MedicationOrder

        fields = (

            "medication",

            "dose",

            "dose_unit",

            "route",

            "frequency",

            "quantity",

            "start_datetime",

            "stop_date",

            "instructions",

            "order_method",

            "order_type",

            "clinical_indication",

            "ordered_by",

        )

        widgets = {

            "order_method": forms.Select(attrs={"class": SELECT_CLASS}),

            "order_type": forms.Select(attrs={"class": SELECT_CLASS}),

            "clinical_indication": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Diagnosis, symptom, or treatment indication",
                }
            ),

            "ordered_by": forms.Select(attrs={"class": SELECT_CLASS}),

            # =================================================

            # MEDICATION

            # =================================================

            "medication": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                    # JavaScript medication picker hook.

                    "data-medication-select": "",

                    # LOCAL database only.

                    "data-medication-api": (

                        "/pharmacy/api/medications/"

                    ),

                }

            ),

            # =================================================

            # DOSE

            # =================================================

            "dose": forms.TextInput(

                attrs={

                    "class": INPUT_CLASS,

                    "placeholder": "e.g. 500",

                    "inputmode": "decimal",

                    "autocomplete": "off",

                }

            ),

            # =================================================

            # DOSE UNIT

            # =================================================

            "dose_unit": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                }

            ),

            # =================================================

            # ROUTE

            # =================================================

            "route": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                    # Allows medication picker to populate

                    # the route when the medication has one.

                    "data-medication-route": "",

                }

            ),

            # =================================================

            # FREQUENCY

            # =================================================

            "frequency": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                }

            ),

            # =================================================

            # QUANTITY

            # =================================================

            "quantity": forms.NumberInput(

                attrs={

                    "class": INPUT_CLASS,

                    "placeholder": "e.g. 30",

                    "step": "0.001",

                    "min": "0",

                }

            ),

            # =================================================

            # START DATE / TIME

            # =================================================

            "start_datetime": forms.DateTimeInput(

                attrs={

                    "class": DATE_TIME_CLASS,

                    "type": "datetime-local",

                },

                format="%Y-%m-%dT%H:%M",

            ),

            # =================================================

            # STOP DATE

            # =================================================

            "stop_date": forms.DateInput(

                attrs={

                    "class": DATE_TIME_CLASS,

                    "type": "date",

                },

                format="%Y-%m-%d",

            ),

            # =================================================

            # INSTRUCTIONS

            # =================================================

            "instructions": forms.Textarea(

                attrs={

                    "class": TEXTAREA_CLASS,

                    "rows": 3,

                    "placeholder": (

                        "Additional administration "

                        "instructions..."

                    ),

                }

            ),

        }

    # ========================================================

    # INITIALIZATION

    # ========================================================

    def __init__(

        self,

        *args,

        **kwargs,

    ):

        super().__init__(

            *args,

            **kwargs,

        )

        # ====================================================

        # MEDICATION QUERYSET

        # ====================================================

        medication_field = (

            self.fields[

                "medication"

            ]

        )

        medication_field.queryset = (

            Medication.objects

            .active()

            .order_by(

                "generic_name",

                "brand_name",

                "strength",

                "dosage_form",

                "route",

                "code",

            )

        )

        medication_field.empty_label = (

            "Search medication"

        )

        medication_field.help_text = (

            "Type at least 4 letters to search "

            "the local medication database."

        )

        self.fields["ordered_by"].queryset = (
            get_user_model().objects.filter(is_active=True).order_by(
                "last_name", "first_name", "username"
            )
        )
        self.fields["ordered_by"].label = "Ordering provider"
        self.fields["order_method"].label = "Order medium"
        self.fields["order_type"].label = "Order type"
        self.fields["clinical_indication"].label = "Clinical indication"

        # ====================================================

        # DOSE UNIT

        # ====================================================

        self.fields[

            "dose_unit"

        ].choices = [

            (

                "",

                "Select unit",

            ),

            *MedicationOrder.DoseUnit.choices,

        ]

        # ====================================================

        # ROUTE

        # ====================================================

        self.fields[

            "route"

        ].choices = [

            (

                "",

                "Select route",

            ),

            *MedicationOrder.Route.choices,

        ]

        # ====================================================

        # FREQUENCY

        # ====================================================

        self.fields[

            "frequency"

        ].choices = [

            (

                "",

                "Select frequency",

            ),

            *MedicationOrder.Frequency.choices,

        ]

        # ====================================================

        # DATE/TIME INPUT FORMATS

        # ====================================================

        self.fields[

            "start_datetime"

        ].input_formats = [

            "%Y-%m-%dT%H:%M",

        ]

        self.fields[

            "stop_date"

        ].input_formats = [

            "%Y-%m-%d",

        ]

        # ====================================================

        # DEFAULT START TIME

        # ====================================================

        if (

            not self.is_bound

            and not self.instance.pk

        ):

            self.initial[

                "start_datetime"

            ] = (

                timezone.localtime()

                .replace(

                    second=0,

                    microsecond=0,

                )

                .strftime(

                    "%Y-%m-%dT%H:%M"

                )

            )

    # ========================================================

    # MEDICATION VALIDATION

    # ========================================================

    def clean_medication(

        self,

    ):

        medication = (

            self.cleaned_data

            .get("medication")

        )

        if medication is None:

            raise forms.ValidationError(

                "Select a medication."

            )

        if not medication.is_active:

            raise forms.ValidationError(

                "This medication is inactive."

            )

        if medication.is_retired:

            raise forms.ValidationError(

                "This medication has been retired."

            )

        return medication

    # ========================================================

    # DOSE VALIDATION

    # ========================================================

    def clean_dose(

        self,

    ):

        dose = (

            self.cleaned_data

            .get(

                "dose",

                "",

            )

        )

        dose = (

            " ".join(

                str(dose).split()

            )

            .strip()

        )

        if not dose:

            raise forms.ValidationError(

                "Enter a medication dose."

            )

        return dose

    # ========================================================

    # FORM VALIDATION

    # ========================================================

    def clean(

        self,

    ):

        cleaned_data = (

            super().clean()

        )

        start_datetime = (

            cleaned_data

            .get(

                "start_datetime"

            )

        )

        stop_date = (

            cleaned_data

            .get(

                "stop_date"

            )

        )

        # ====================================================

        # START / STOP VALIDATION

        # ====================================================

        if (

            start_datetime

            and stop_date

            and stop_date

            < start_datetime.date()

        ):

            self.add_error(

                "stop_date",

                (

                    "Stop date cannot be "

                    "before the start date."

                ),

            )

        return cleaned_data
