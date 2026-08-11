from __future__ import annotations

from django import forms

from apps.orders.models import MedicationOrder

from .models import MedicationAdministration

# ============================================================

# TAILWIND

# ============================================================

INPUT_CLASS = (

    "block w-full rounded-md "

    "border border-slate-300 "

    "bg-white px-2.5 py-2 "

    "text-xs text-slate-900 "

    "shadow-sm outline-none "

    "focus:border-emerald-500 "

    "focus:ring-2 "

    "focus:ring-emerald-500/20"

)

SELECT_CLASS = INPUT_CLASS

TEXTAREA_CLASS = (

    "block w-full rounded-md "

    "border border-slate-300 "

    "bg-white px-2.5 py-2 "

    "text-xs text-slate-900 "

    "shadow-sm outline-none "

    "focus:border-emerald-500 "

    "focus:ring-2 "

    "focus:ring-emerald-500/20"

)

# ============================================================

# MEDICATION ADMINISTRATION FORM

# ============================================================

class MedicationAdministrationForm(

    forms.ModelForm,

):

    """

    Detailed medication administration form.

    Routine MAR Give actions no longer require this full form.

    The compact MAR writes the administration immediately.

    This form remains available for detailed administration

    workflows when additional bedside documentation is needed.

    """

    class Meta:

        model = MedicationAdministration

        fields = (

            "medication_order",

            "dose_administered",

            "route",

            "administration_site",

            "status",

            "scheduled_at",

            "reason",

            "notes",

            "witnessed_by",

        )

        widgets = {

            "medication_order":

                forms.Select(

                    attrs={

                        "class":

                            SELECT_CLASS,

                        "data-medication-order-select":

                            "",

                    }

                ),

            "dose_administered":

                forms.TextInput(

                    attrs={

                        "class":

                            INPUT_CLASS,

                        "autocomplete":

                            "off",

                        "placeholder":

                            "e.g. 500 mg",

                    }

                ),

            "route":

                forms.TextInput(

                    attrs={

                        "class":

                            INPUT_CLASS,

                        "autocomplete":

                            "off",

                        "placeholder":

                            "e.g. Oral",

                    }

                ),

            "administration_site":

                forms.TextInput(

                    attrs={

                        "class":

                            INPUT_CLASS,

                        "autocomplete":

                            "off",

                        "placeholder":

                            "Optional site",

                    }

                ),

            "status":

                forms.Select(

                    attrs={

                        "class":

                            SELECT_CLASS,

                        "x-model":

                            "status",

                    }

                ),

            "scheduled_at":

                forms.DateTimeInput(

                    attrs={

                        "class":

                            INPUT_CLASS,

                        "type":

                            "datetime-local",

                    },

                    format=(

                        "%Y-%m-%dT%H:%M"

                    ),

                ),

            "reason":

                forms.Textarea(

                    attrs={

                        "class":

                            TEXTAREA_CLASS,

                        "rows":

                            2,

                        "placeholder": (

                            "Required when held, "

                            "refused, omitted, "

                            "or not given"

                        ),

                    }

                ),

            "notes":

                forms.Textarea(

                    attrs={

                        "class":

                            TEXTAREA_CLASS,

                        "rows":

                            2,

                        "placeholder":

                            "Optional administration notes",

                    }

                ),

            "witnessed_by":

                forms.Select(

                    attrs={

                        "class":

                            SELECT_CLASS,

                    }

                ),

        }

    # ========================================================

    # INITIALIZATION

    # ========================================================

    def __init__(

        self,

        *args,

        encounter=None,

        **kwargs,

    ):

        super().__init__(

            *args,

            **kwargs,

        )

        self.encounter = encounter

        self.fields[

            "medication_order"

        ].queryset = (

            MedicationOrder.objects.none()

        )

        if encounter is not None:

            self.fields[

                "medication_order"

            ].queryset = (

                MedicationOrder.objects

                .filter(

                    encounter=encounter,

                )

                .select_related(

                    "medication",

                    "patient",

                    "encounter",

                )

                .order_by(

                    "medication__generic_name",

                    "medication__brand_name",

                    "ordered_at",

                )

            )

        self.fields[

            "medication_order"

        ].required = True

        self.fields[

            "scheduled_at"

        ].required = False

        self.fields[

            "administration_site"

        ].required = False

        self.fields[

            "reason"

        ].required = False

        self.fields[

            "notes"

        ].required = False

        self.fields[

            "witnessed_by"

        ].required = False

        self.fields[

            "scheduled_at"

        ].input_formats = [

            "%Y-%m-%dT%H:%M",

        ]

    # ========================================================

    # MEDICATION ORDER VALIDATION

    # ========================================================

    def clean_medication_order(

        self,

    ):

        order = (

            self.cleaned_data

            .get(

                "medication_order"

            )

        )

        if order is None:

            raise forms.ValidationError(

                "Select a medication order."

            )

        if (

            self.encounter

            and order.encounter_id

            != self.encounter.pk

        ):

            raise forms.ValidationError(

                (

                    "This medication order "

                    "does not belong to the "

                    "active encounter."

                )

            )

        return order

    # ========================================================

    # FORM VALIDATION

    # ========================================================

    def clean(

        self,

    ):

        cleaned_data = (

            super().clean()

        )

        order = (

            cleaned_data.get(

                "medication_order"

            )

        )

        status = (

            cleaned_data.get(

                "status"

            )

        )

        reason = (

            cleaned_data.get(

                "reason"

            )

            or ""

        ).strip()

        dose = (

            cleaned_data.get(

                "dose_administered"

            )

            or ""

        ).strip()

        route = (

            cleaned_data.get(

                "route"

            )

            or ""

        ).strip()

        if order:

            self.instance.medication = (

                order.medication

            )

            if not dose:

                order_dose = str(

                    order.dose or ""

                ).strip()

                order_unit = str(

                    order.dose_unit or ""

                ).strip()

                if (

                    order_dose

                    and order_unit

                ):

                    cleaned_data[

                        "dose_administered"

                    ] = (

                        f"{order_dose} "

                        f"{order_unit}"

                    )

                elif order_dose:

                    cleaned_data[

                        "dose_administered"

                    ] = order_dose

            if not route:

                cleaned_data[

                    "route"

                ] = (

                    str(

                        order.route

                        or ""

                    ).strip()

                )

        administered_status = getattr(

            MedicationAdministration.Status,

            "ADMINISTERED",

            "administered",

        )

        if (

            status

            == administered_status

        ):

            final_dose = (

                cleaned_data.get(

                    "dose_administered"

                )

                or ""

            ).strip()

            final_route = (

                cleaned_data.get(

                    "route"

                )

                or ""

            ).strip()

            if not final_dose:

                self.add_error(

                    "dose_administered",

                    (

                        "The medication order "

                        "does not contain a usable dose."

                    ),

                )

            if not final_route:

                self.add_error(

                    "route",

                    (

                        "The medication order "

                        "does not contain a usable route."

                    ),

                )

        elif status and not reason:

            self.add_error(

                "reason",

                (

                    "Document why the medication "

                    "was not administered."

                ),

            )

        return cleaned_data