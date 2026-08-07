from django import forms

from django.core.exceptions import ValidationError

from django.utils import timezone

from .models import VitalObservation

# ============================================================

# CLINICAL FLOWSHEET WIDGET STYLES

# ============================================================

CELL_CLASS = (

    "block h-8 w-full "

    "border-0 bg-transparent "

    "px-2 py-1 "

    "text-center text-xs font-semibold "

    "text-slate-900 "

    "placeholder:text-slate-300 "

    "outline-none "

    "focus:bg-emerald-50 "

    "focus:ring-2 focus:ring-inset "

    "focus:ring-emerald-500 "

    "disabled:cursor-not-allowed "

    "disabled:bg-slate-100 "

    "disabled:text-slate-500"

)

SELECT_CLASS = (

    "block h-8 w-full "

    "border-0 bg-transparent "

    "px-2 py-1 "

    "text-xs font-medium "

    "text-slate-900 "

    "outline-none "

    "focus:bg-emerald-50 "

    "focus:ring-2 focus:ring-inset "

    "focus:ring-emerald-500 "

    "disabled:cursor-not-allowed "

    "disabled:bg-slate-100 "

    "disabled:text-slate-500"

)

TEXTAREA_CLASS = (

    "block min-h-16 w-full resize-y "

    "border-0 bg-transparent "

    "px-2 py-1.5 "

    "text-xs text-slate-900 "

    "placeholder:text-slate-300 "

    "outline-none "

    "focus:bg-emerald-50 "

    "focus:ring-2 focus:ring-inset "

    "focus:ring-emerald-500 "

    "disabled:cursor-not-allowed "

    "disabled:bg-slate-100 "

    "disabled:text-slate-500"

)

# ============================================================

# VITAL OBSERVATION FORM

# ============================================================

class VitalObservationForm(forms.ModelForm):

    """

    Clinical vital-sign intake form.

    Workflow:

    - Patient comes from the selected patient workspace.

    - Encounter comes from the active encounter context.

    - Observation date/time is generated automatically.

    - Recorder is generated automatically from request.user.

    - New observations default to FINAL.

    - Only clinical measurements are presented to the clinician.

    """

    class Meta:

        model = VitalObservation

        # Patient, encounter, recorded_at, recorded_by, and status

        # are intentionally not exposed as routine intake fields.

        fields = [

            "position",

            "temperature_celsius",

            "temperature_site",

            "heart_rate",

            "respiratory_rate",

            "systolic_blood_pressure",

            "diastolic_blood_pressure",

            "oxygen_saturation",

            "oxygen_delivery_method",

            "oxygen_flow_lpm",

            "pain_score",

            "height_cm",

            "weight_kg",

            "blood_glucose_mg_dl",

            "notes",

            "correction_reason",

        ]

        labels = {

            "position": "Position",

            "temperature_celsius": "Temperature",

            "temperature_site": "Temperature site",

            "heart_rate": "Pulse",

            "respiratory_rate": "Respirations",

            "systolic_blood_pressure": "Systolic BP",

            "diastolic_blood_pressure": "Diastolic BP",

            "oxygen_saturation": "SpO₂",

            "oxygen_delivery_method": "Oxygen delivery",

            "oxygen_flow_lpm": "O₂ flow",

            "pain_score": "Pain",

            "height_cm": "Height",

            "weight_kg": "Weight",

            "blood_glucose_mg_dl": "Blood glucose",

            "notes": "Comments",

            "correction_reason": "Correction reason",

        }

        help_texts = {

            "temperature_celsius": "°C",

            "heart_rate": "bpm",

            "respiratory_rate": "/min",

            "systolic_blood_pressure": "mmHg",

            "diastolic_blood_pressure": "mmHg",

            "oxygen_saturation": "%",

            "oxygen_flow_lpm": "L/min",

            "pain_score": "0–10",

            "height_cm": "cm",

            "weight_kg": "kg",

            "blood_glucose_mg_dl": "mg/dL",

        }

        widgets = {

            # ----------------------------------------------------

            # CONTEXT

            # ----------------------------------------------------

            "position": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                    "aria-label": "Patient position",

                },

            ),

            # ----------------------------------------------------

            # TEMPERATURE

            # ----------------------------------------------------

            "temperature_celsius": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.1",

                    "min": "25",

                    "max": "45",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Temperature Celsius",

                },

            ),

            "temperature_site": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                    "aria-label": "Temperature site",

                },

            ),

            # ----------------------------------------------------

            # CARDIOVASCULAR

            # ----------------------------------------------------

            "heart_rate": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "1",

                    "min": "10",

                    "max": "300",

                    "inputmode": "numeric",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Heart rate",

                },

            ),

            "systolic_blood_pressure": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "1",

                    "min": "30",

                    "max": "300",

                    "inputmode": "numeric",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Systolic blood pressure",

                },

            ),

            "diastolic_blood_pressure": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "1",

                    "min": "10",

                    "max": "200",

                    "inputmode": "numeric",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Diastolic blood pressure",

                },

            ),

            # ----------------------------------------------------

            # RESPIRATORY

            # ----------------------------------------------------

            "respiratory_rate": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "1",

                    "min": "1",

                    "max": "100",

                    "inputmode": "numeric",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Respiratory rate",

                },

            ),

            "oxygen_saturation": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.1",

                    "min": "0",

                    "max": "100",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Oxygen saturation",

                },

            ),

            "oxygen_delivery_method": forms.Select(

                attrs={

                    "class": SELECT_CLASS,

                    "aria-label": "Oxygen delivery method",

                },

            ),

            "oxygen_flow_lpm": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.1",

                    "min": "0",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Oxygen flow",

                },

            ),

            # ----------------------------------------------------

            # PAIN

            # ----------------------------------------------------

            "pain_score": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "1",

                    "min": "0",

                    "max": "10",

                    "inputmode": "numeric",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Pain score",

                },

            ),

            # ----------------------------------------------------

            # ANTHROPOMETRICS

            # ----------------------------------------------------

            "height_cm": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.1",

                    "min": "20",

                    "max": "300",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Height centimeters",

                },

            ),

            "weight_kg": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.01",

                    "min": "0.2",

                    "max": "1000",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Weight kilograms",

                },

            ),

            # ----------------------------------------------------

            # GLUCOSE

            # ----------------------------------------------------

            "blood_glucose_mg_dl": forms.NumberInput(

                attrs={

                    "class": CELL_CLASS,

                    "step": "0.1",

                    "min": "1",

                    "max": "2000",

                    "inputmode": "decimal",

                    "placeholder": "—",

                    "autocomplete": "off",

                    "aria-label": "Blood glucose",

                },

            ),

            # ----------------------------------------------------

            # DOCUMENTATION

            # ----------------------------------------------------

            "notes": forms.Textarea(

                attrs={

                    "class": TEXTAREA_CLASS,

                    "rows": 2,

                    "placeholder": (

                        "Optional comments about measurement "

                        "conditions or clinical observations."

                    ),

                },

            ),

            "correction_reason": forms.Textarea(

                attrs={

                    "class": TEXTAREA_CLASS,

                    "rows": 2,

                    "placeholder": (

                        "Explain why the previously documented "

                        "observation is being corrected."

                    ),

                },

            ),

        }

    # ============================================================

    # INITIALIZATION

    # ============================================================

    def __init__(

        self,

        *args,

        current_user=None,

        patient=None,

        encounter=None,

        **kwargs,

    ):

        super().__init__(*args, **kwargs)

        self.current_user = current_user

        # --------------------------------------------------------

        # CREATE / UPDATE STATE

        #

        # UUID primary keys may exist before the object is saved,

        # so instance.pk must not be used to determine create mode.

        # --------------------------------------------------------

        self.is_create = self.instance._state.adding

        self.is_update = not self.instance._state.adding

        # --------------------------------------------------------

        # CONTEXT PASSED FROM VIEW

        # --------------------------------------------------------

        self.selected_patient = patient

        self.selected_encounter = encounter

        # Encounter is authoritative when supplied.

        if self.selected_encounter is not None:

            self.selected_patient = self.selected_encounter.patient

        # --------------------------------------------------------

        # UPDATE MODE

        # Existing saved observation becomes authoritative.

        # --------------------------------------------------------

        if self.is_update:

            self.selected_patient = self.instance.patient

            self.selected_encounter = self.instance.encounter

        # --------------------------------------------------------

        # AUTOMATIC OBSERVATION DATE/TIME

        #

        # Create:

        # - current local date/time

        # - minute precision

        #

        # Update:

        # - preserve original recorded_at

        # --------------------------------------------------------

        if self.is_update and self.instance.recorded_at:

            self.observation_datetime = timezone.localtime(

                self.instance.recorded_at

            )

        else:

            self.observation_datetime = (

                timezone.localtime()

                .replace(

                    second=0,

                    microsecond=0,

                )

            )

        # --------------------------------------------------------

        # OPTIONAL FIELDS

        # --------------------------------------------------------

        optional_fields = [

            "position",

            "temperature_celsius",

            "temperature_site",

            "heart_rate",

            "respiratory_rate",

            "systolic_blood_pressure",

            "diastolic_blood_pressure",

            "oxygen_saturation",

            "oxygen_delivery_method",

            "oxygen_flow_lpm",

            "pain_score",

            "height_cm",

            "weight_kg",

            "blood_glucose_mg_dl",

            "notes",

        ]

        for field_name in optional_fields:

            if field_name in self.fields:

                self.fields[field_name].required = False

        # --------------------------------------------------------

        # SELECT EMPTY LABELS

        # --------------------------------------------------------

        if "position" in self.fields:

            self.fields["position"].empty_label = "—"

        if "temperature_site" in self.fields:

            self.fields["temperature_site"].empty_label = "—"

        if "oxygen_delivery_method" in self.fields:

            self.fields[

                "oxygen_delivery_method"

            ].empty_label = "—"

        # --------------------------------------------------------

        # CORRECTION REASON

        #

        # Hidden for new observations.

        # Visible for updates.

        # --------------------------------------------------------

        self.fields["correction_reason"].required = False

        if self.is_create:

            self.fields["correction_reason"].widget = (

                forms.HiddenInput()

            )

        # --------------------------------------------------------

        # ENTERED-IN-ERROR OBSERVATIONS ARE READ ONLY

        # --------------------------------------------------------

        if (

            self.is_update

            and self.instance.status

            == VitalObservation.RecordStatus.ENTERED_IN_ERROR

        ):

            for field in self.fields.values():

                field.disabled = True

    # ============================================================

    # TEMPLATE DISPLAY HELPERS

    # ============================================================

    @property

    def observation_date_display(self):

        """

        Example:

            08/06/2026

        """

        return self.observation_datetime.strftime(

            "%m/%d/%Y"

        )

    @property

    def observation_time_display(self):

        """

        Example:

            7:42 PM

        """

        return self.observation_datetime.strftime(

            "%-I:%M %p"

        )

    @property

    def observation_datetime_display(self):

        """

        Example:

            08/06/2026 7:42 PM

        """

        return self.observation_datetime.strftime(

            "%m/%d/%Y %-I:%M %p"

        )

    # ============================================================

    # VALIDATION

    # ============================================================

    def clean(self):

        cleaned_data = super().clean()

        # --------------------------------------------------------

        # PATIENT CONTEXT REQUIRED

        # --------------------------------------------------------

        if self.selected_patient is None:

            raise ValidationError(

                (

                    "A patient must be selected before "

                    "recording vital signs."

                )

            )

        # --------------------------------------------------------

        # ENCOUNTER / PATIENT CONSISTENCY

        # --------------------------------------------------------

        if self.selected_encounter is not None:

            if (

                self.selected_encounter.patient_id

                != self.selected_patient.pk

            ):

                raise ValidationError(

                    (

                        "The active encounter does not belong "

                        "to the selected patient."

                    )

                )

        # --------------------------------------------------------

        # REQUIRE AT LEAST ONE MEASUREMENT

        # --------------------------------------------------------

        measurement_fields = [

            "temperature_celsius",

            "heart_rate",

            "respiratory_rate",

            "systolic_blood_pressure",

            "diastolic_blood_pressure",

            "oxygen_saturation",

            "pain_score",

            "height_cm",

            "weight_kg",

            "blood_glucose_mg_dl",

        ]

        has_measurement = any(

            cleaned_data.get(field_name) is not None

            for field_name in measurement_fields

        )

        if not has_measurement:

            raise ValidationError(

                (

                    "Enter at least one vital-sign "

                    "measurement before saving."

                )

            )

        # --------------------------------------------------------

        # BLOOD PRESSURE VALIDATION

        # --------------------------------------------------------

        systolic = cleaned_data.get(

            "systolic_blood_pressure"

        )

        diastolic = cleaned_data.get(

            "diastolic_blood_pressure"

        )

        if systolic is not None and diastolic is None:

            self.add_error(

                "diastolic_blood_pressure",

                "Enter the diastolic blood pressure.",

            )

        if diastolic is not None and systolic is None:

            self.add_error(

                "systolic_blood_pressure",

                "Enter the systolic blood pressure.",

            )

        if (

            systolic is not None

            and diastolic is not None

            and systolic <= diastolic

        ):

            self.add_error(

                "systolic_blood_pressure",

                (

                    "Systolic blood pressure must be greater "

                    "than diastolic pressure."

                ),

            )

        # --------------------------------------------------------

        # OXYGEN VALIDATION

        # --------------------------------------------------------

        oxygen_method = cleaned_data.get(

            "oxygen_delivery_method"

        )

        oxygen_flow = cleaned_data.get(

            "oxygen_flow_lpm"

        )

        if (

            oxygen_method

            == VitalObservation.OxygenDeliveryMethod.ROOM_AIR

            and oxygen_flow is not None

            and oxygen_flow > 0

        ):

            self.add_error(

                "oxygen_flow_lpm",

                (

                    "Oxygen flow should be blank or zero "

                    "when the patient is on room air."

                ),

            )

        # --------------------------------------------------------

        # CORRECTION VALIDATION

        # --------------------------------------------------------

        if self.is_update:

            correction_reason = (

                cleaned_data.get(

                    "correction_reason"

                )

                or ""

            ).strip()

            changed_clinical_fields = [

                field_name

                for field_name in self.changed_data

                if field_name != "correction_reason"

            ]

            if (

                changed_clinical_fields

                and not correction_reason

            ):

                self.add_error(

                    "correction_reason",

                    (

                        "Provide a reason for changing this "

                        "previously recorded observation."

                    ),

                )

        return cleaned_data

    # ============================================================

    # SAVE

    # ============================================================

    def save(self, commit=True):

        instance = super().save(

            commit=False

        )

        # --------------------------------------------------------

        # PATIENT / ENCOUNTER

        # --------------------------------------------------------

        instance.patient = self.selected_patient

        instance.encounter = self.selected_encounter

        # --------------------------------------------------------

        # CREATE

        # --------------------------------------------------------

        if self.is_create:

            instance.recorded_at = (

                self.observation_datetime

            )

            instance.status = (

                VitalObservation.RecordStatus.FINAL

            )

        # --------------------------------------------------------

        # UPDATE / CORRECTION

        # --------------------------------------------------------

        elif self.is_update:

            changed_clinical_fields = [

                field_name

                for field_name in self.changed_data

                if field_name != "correction_reason"

            ]

            if changed_clinical_fields:

                instance.status = (

                    VitalObservation.RecordStatus.CORRECTED

                )

        # --------------------------------------------------------

        # AUDITED SAVE

        # --------------------------------------------------------

        if commit:

            instance.save(

                actor=self.current_user,

            )

        return instance

# ============================================================

# ENTERED-IN-ERROR FORM

# ============================================================

class VitalEnteredInErrorForm(forms.Form):

    """

    Capture the audit reason when marking a vital observation

    as entered in error.

    """

    reason = forms.CharField(

        label="Reason",

        widget=forms.Textarea(

            attrs={

                "class": TEXTAREA_CLASS,

                "rows": 3,

                "placeholder": (

                    "Explain why this vital-sign "

                    "observation was entered in error."

                ),

            },

        ),

    )

    def clean_reason(self):

        reason = (

            self.cleaned_data["reason"]

            .strip()

        )

        if len(reason) < 5:

            raise forms.ValidationError(

                (

                    "Provide a clear reason with "

                    "at least five characters."

                )

            )

        return reason