from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import VitalObservation

# ============================================================

# CLINICAL FLOWSHEET WIDGET STYLES

# ============================================================

CELL_CLASS = (
    "block min-h-9 w-full "
    "rounded-none border-0 bg-transparent "
    "px-2 py-1 "
    "text-center text-[11px] font-semibold "
    "text-slate-900 "
    "placeholder:text-slate-300 "
    "outline-none "
    "focus:bg-blue-50 "
    "focus:ring-1 focus:ring-inset "
    "focus:ring-blue-500 "
    "disabled:cursor-not-allowed "
    "disabled:bg-slate-100 "
    "disabled:text-slate-500"
)

SELECT_CLASS = (
    "block min-h-9 w-full "
    "rounded-none border-0 bg-transparent "
    "px-2 py-1 "
    "text-xs font-medium leading-5 "
    "text-slate-800 "
    "outline-none "
    "focus:bg-blue-50 "
    "focus:ring-1 focus:ring-inset "
    "focus:ring-blue-500 "
    "disabled:cursor-not-allowed "
    "disabled:bg-slate-100 "
    "disabled:text-slate-500"
)

TEXTAREA_CLASS = (
    "block min-h-12 w-full resize-y "
    "rounded-none border-0 bg-transparent "
    "px-1.5 py-1 "
    "text-[10px] leading-4 "
    "text-slate-800 "
    "placeholder:text-slate-300 "
    "outline-none "
    "focus:bg-blue-50 "
    "focus:ring-1 focus:ring-inset "
    "focus:ring-blue-500 "
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

    - Patient comes from selected patient context.

    - Encounter comes from active encounter context.

    - recorded_at is generated automatically.

    - recorded_by is handled by the audited model save.

    - New observations default to FINAL.

    - Previously finalized observations require a correction reason

      when clinical data is changed.

    """

    # --------------------------------------------------------

    # NON-MODEL TEMPERATURE DISPLAY UNIT

    # --------------------------------------------------------

    temperature_unit = forms.ChoiceField(
        choices=(
            ("F", "°F"),
            ("C", "°C"),
        ),
        initial="F",
        required=False,
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "aria-label": "Temperature unit",
            }
        ),
    )

    # --------------------------------------------------------

    # TEMPERATURE ENTRY FIELD

    #

    # Despite the transitional field name, this input may receive

    # either Fahrenheit or Celsius depending on temperature_unit.

    # clean() converts the value to Fahrenheit before model save.

    # --------------------------------------------------------

    temperature_fahrenheit = forms.DecimalField(
        label="Temperature",
        required=False,
        max_digits=5,
        decimal_places=1,
        widget=forms.NumberInput(
            attrs={
                "class": CELL_CLASS,
                "step": "0.1",
                "min": "25",
                "max": "113",
                "inputmode": "decimal",
                "placeholder": "—",
                "autocomplete": "off",
                "aria-label": "Temperature value",
            }
        ),
    )

    # --------------------------------------------------------

    # PAIN LOCATION

    #

    # Keep this as a ChoiceField if PainLocation.choices contains

    # every body-map value that may be submitted.

    # --------------------------------------------------------

    pain_location = forms.ChoiceField(
        label="Pain location",
        choices=VitalObservation.PainLocation.choices,
        required=False,
        widget=forms.Select(
            attrs={
                "class": SELECT_CLASS,
                "aria-label": "Pain location",
                "x-model": "painLocation",
                "x-ref": "painLocation",
            }
        ),
    )

    # ========================================================

    # META

    # ========================================================

    class Meta:
        model = VitalObservation

        # Patient, encounter, recorded_at, recorded_by, and status

        # intentionally remain outside routine clinician entry.

        fields = [
            "position",
            "temperature_fahrenheit",
            "temperature_site",
            "heart_rate",
            "heart_rhythm",
            "heart_rate_method",
            "respiratory_rate",
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
            "blood_pressure_location",
            "oxygen_saturation",
            "oxygen_delivery_method",
            "oxygen_flow_lpm",
            "pain_status",
            "pain_score",
            "pain_location",
            "pain_characteristics",
            "height_cm",
            "weight_kg",
            "blood_glucose_mg_dl",
            "notes",
            "correction_reason",
        ]

        labels = {
            "position": "Position",
            "temperature_fahrenheit": "Temperature",
            "temperature_site": "Temperature site",
            "heart_rate": "Pulse rate",
            "heart_rhythm": "Rhythm",
            "heart_rate_method": "Pulse method",
            "respiratory_rate": "Respirations",
            "systolic_blood_pressure": "Systolic BP",
            "diastolic_blood_pressure": "Diastolic BP",
            "blood_pressure_location": "BP location",
            "oxygen_saturation": "SpO₂",
            "oxygen_delivery_method": "Oxygen delivery",
            "oxygen_flow_lpm": "O₂ flow",
            "pain_status": "Pain status",
            "pain_score": "Pain score",
            "pain_location": "Pain location",
            "pain_characteristics": "Pain characteristics",
            "height_cm": "Height",
            "weight_kg": "Weight",
            "blood_glucose_mg_dl": "Blood glucose",
            "notes": "Comments",
            "correction_reason": "Correction reason",
        }

        help_texts = {
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
            # ------------------------------------------------
            # POSITION
            # ------------------------------------------------
            "position": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Patient position",
                }
            ),
            # ------------------------------------------------
            # TEMPERATURE
            #
            # temperature_fahrenheit is explicitly declared above,
            # so its widget does not belong here.
            # ------------------------------------------------
            "temperature_site": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Temperature site",
                }
            ),
            # ------------------------------------------------
            # CARDIOVASCULAR
            # ------------------------------------------------
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
                }
            ),
            "heart_rhythm": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Heart rhythm",
                }
            ),
            "heart_rate_method": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Pulse method",
                }
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
                }
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
                }
            ),
            "blood_pressure_location": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Blood pressure location",
                }
            ),
            # ------------------------------------------------
            # RESPIRATORY
            # ------------------------------------------------
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
                }
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
                }
            ),
            "oxygen_delivery_method": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Oxygen delivery method",
                    "x-model": "oxygenMethod",
                    "@change": (
                        "if (oxygenMethod === 'room_air' "
                        "&& $refs.oxygenFlow) { "
                        "$refs.oxygenFlow.value = ''; "
                        "}"
                    ),
                }
            ),
            "oxygen_flow_lpm": forms.NumberInput(
                attrs={
                    "class": CELL_CLASS,
                    "step": "0.1",
                    "min": "0",
                    "max": "60",
                    "inputmode": "decimal",
                    "placeholder": "—",
                    "autocomplete": "off",
                    "aria-label": "Oxygen flow",
                    "x-ref": "oxygenFlow",
                }
            ),
            # ------------------------------------------------
            # PAIN
            #
            # pain_location is explicitly declared above.
            # ------------------------------------------------
            "pain_status": forms.Select(
                attrs={
                    "class": SELECT_CLASS,
                    "aria-label": "Pain status",
                    "x-model": "painPresent",
                    "x-ref": "painStatus",
                }
            ),
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
                }
            ),
            "pain_characteristics": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 2,
                    "placeholder": (
                        "Describe quality, onset, pattern, "
                        "or aggravating/relieving factors."
                    ),
                    "aria-label": "Pain characteristics",
                }
            ),
            # ------------------------------------------------
            # ANTHROPOMETRICS
            # ------------------------------------------------
            "height_cm": forms.NumberInput(
                attrs={
                    "class": CELL_CLASS,
                    "step": "0.1",
                    "min": "20",
                    "max": "300",
                    "inputmode": "decimal",
                    "placeholder": "—",
                    "autocomplete": "off",
                    "aria-label": "Height in centimeters",
                }
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
                    "aria-label": "Weight in kilograms",
                }
            ),
            # ------------------------------------------------
            # GLUCOSE
            # ------------------------------------------------
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
                }
            ),
            # ------------------------------------------------
            # DOCUMENTATION
            # ------------------------------------------------
            "notes": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 2,
                    "placeholder": (
                        "Optional comments about measurement "
                        "conditions or clinical observations."
                    ),
                    "aria-label": "Vital-sign comments",
                }
            ),
            "correction_reason": forms.Textarea(
                attrs={
                    "class": TEXTAREA_CLASS,
                    "rows": 2,
                    "placeholder": (
                        "Explain why the previously documented "
                        "observation is being corrected."
                    ),
                    "aria-label": "Correction reason",
                }
            ),
        }

    # ========================================================

    # INITIALIZATION

    # ========================================================

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

        # ----------------------------------------------------

        # CREATE / UPDATE STATE

        #

        # UUID primary keys may exist before save, therefore

        # instance.pk is not reliable for determining create mode.

        # ----------------------------------------------------

        self.is_create = self.instance._state.adding

        self.is_update = not self.instance._state.adding

        # ----------------------------------------------------

        # PATIENT / ENCOUNTER CONTEXT

        # ----------------------------------------------------

        self.selected_patient = patient

        self.selected_encounter = encounter

        # Encounter is authoritative when supplied.

        if self.selected_encounter is not None:
            self.selected_patient = self.selected_encounter.patient

        # A persisted observation is authoritative during update.

        if self.is_update:
            self.selected_patient = self.instance.patient

            self.selected_encounter = self.instance.encounter

        # ----------------------------------------------------

        # TEMPERATURE DISPLAY UNIT

        # ----------------------------------------------------

        if (
            self.is_update
            and self.instance.temperature_celsius is not None
            and self.instance.temperature_fahrenheit is None
        ):
            self.fields["temperature_unit"].initial = "C"

            self.initial["temperature_fahrenheit"] = self.instance.temperature_celsius

        else:
            self.fields["temperature_unit"].initial = "F"

        # ----------------------------------------------------

        # AUTOMATIC OBSERVATION DATE / TIME

        # ----------------------------------------------------

        if self.is_update and self.instance.recorded_at:
            self.observation_datetime = timezone.localtime(self.instance.recorded_at)

        else:
            self.observation_datetime = timezone.localtime().replace(
                second=0,
                microsecond=0,
            )

        # ----------------------------------------------------

        # ROUTINE VITAL FIELDS ARE OPTIONAL

        #

        # The form-level validation below determines whether a

        # clinically meaningful combination has been supplied.

        # ----------------------------------------------------

        optional_fields = (
            "position",
            "temperature_fahrenheit",
            "temperature_site",
            "heart_rate",
            "heart_rhythm",
            "heart_rate_method",
            "respiratory_rate",
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
            "blood_pressure_location",
            "oxygen_saturation",
            "oxygen_delivery_method",
            "oxygen_flow_lpm",
            "pain_status",
            "pain_score",
            "pain_location",
            "pain_characteristics",
            "height_cm",
            "weight_kg",
            "blood_glucose_mg_dl",
            "notes",
        )

        for field_name in optional_fields:
            field = self.fields.get(field_name)

            if field is not None:
                field.required = False

        # ----------------------------------------------------

        # EMPTY SELECT LABELS

        # ----------------------------------------------------

        select_fields = (
            "position",
            "temperature_site",
            "heart_rhythm",
            "heart_rate_method",
            "blood_pressure_location",
            "oxygen_delivery_method",
            "pain_status",
        )

        for field_name in select_fields:
            field = self.fields.get(field_name)

            if field is not None and hasattr(field, "empty_label"):
                field.empty_label = "—"

        # ----------------------------------------------------

        # CORRECTION REASON

        # ----------------------------------------------------

        self.fields["correction_reason"].required = False

        if self.is_create:
            self.fields["correction_reason"].widget = forms.HiddenInput()

        # ----------------------------------------------------

        # ENTERED-IN-ERROR RECORDS ARE READ-ONLY

        # ----------------------------------------------------

        if (
            self.is_update
            and self.instance.status == VitalObservation.RecordStatus.ENTERED_IN_ERROR
        ):
            for field in self.fields.values():
                field.disabled = True

    # ========================================================

    # TEMPLATE DISPLAY HELPERS

    # ========================================================

    @property
    def observation_date_display(self) -> str:
        """

        Example:

            08/10/2026

        """

        return self.observation_datetime.strftime("%m/%d/%Y")

    @property
    def observation_time_display(self) -> str:
        """

        Example:

            7:42 PM

        """

        return self.observation_datetime.strftime("%-I:%M %p")

    @property
    def observation_datetime_display(self) -> str:
        """

        Example:

            08/10/2026 7:42 PM

        """

        return self.observation_datetime.strftime("%m/%d/%Y %-I:%M %p")

    # ========================================================

    # INTERNAL HELPERS

    # ========================================================

    def _changed_clinical_fields(self) -> list[str]:
        """

        Return fields representing actual clinical record changes.

        temperature_unit is a presentation/input preference and is

        intentionally excluded from correction auditing.

        """

        ignored_fields = {
            "correction_reason",
            "temperature_unit",
        }

        return [
            field_name
            for field_name in self.changed_data
            if field_name not in ignored_fields
        ]

    # ========================================================

    # VALIDATION

    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        # ----------------------------------------------------

        # PATIENT CONTEXT

        # ----------------------------------------------------

        if self.selected_patient is None:
            raise ValidationError(
                ("A patient must be selected before recording vital signs.")
            )

        # ----------------------------------------------------

        # ENCOUNTER / PATIENT CONSISTENCY

        # ----------------------------------------------------

        if self.selected_encounter is not None:
            if self.selected_encounter.patient_id != self.selected_patient.pk:
                raise ValidationError(
                    ("The active encounter does not belong to the selected patient.")
                )

        # ----------------------------------------------------

        # TEMPERATURE

        # ----------------------------------------------------

        temperature = cleaned_data.get("temperature_fahrenheit")

        temperature_unit = cleaned_data.get("temperature_unit") or "F"

        if temperature is not None:
            if temperature_unit == "C":
                if not (Decimal("25.0") <= temperature <= Decimal("45.0")):
                    self.add_error(
                        "temperature_fahrenheit",
                        ("Enter a Celsius temperature between 25.0 and 45.0."),
                    )

                else:
                    temperature = (temperature * Decimal("9")) / Decimal("5") + Decimal(
                        "32"
                    )

            else:
                if not (Decimal("77.0") <= temperature <= Decimal("113.0")):
                    self.add_error(
                        "temperature_fahrenheit",
                        ("Enter a Fahrenheit temperature between 77.0 and 113.0."),
                    )

            if "temperature_fahrenheit" not in self.errors:
                cleaned_data["temperature_fahrenheit"] = temperature.quantize(
                    Decimal("0.1"),
                    rounding=ROUND_HALF_UP,
                )

        # ----------------------------------------------------

        # REQUIRE AT LEAST ONE MEASUREMENT

        # ----------------------------------------------------

        measurement_fields = (
            "temperature_fahrenheit",
            "heart_rate",
            "respiratory_rate",
            "systolic_blood_pressure",
            "diastolic_blood_pressure",
            "oxygen_saturation",
            "pain_score",
            "height_cm",
            "weight_kg",
            "blood_glucose_mg_dl",
        )

        has_measurement = any(
            cleaned_data.get(field_name) is not None
            for field_name in measurement_fields
        )

        if not has_measurement:
            raise ValidationError(
                ("Enter at least one vital-sign measurement before saving.")
            )

        # ----------------------------------------------------

        # BLOOD PRESSURE

        # ----------------------------------------------------

        systolic = cleaned_data.get("systolic_blood_pressure")

        diastolic = cleaned_data.get("diastolic_blood_pressure")

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

        if systolic is not None and diastolic is not None and systolic <= diastolic:
            self.add_error(
                "systolic_blood_pressure",
                ("Systolic blood pressure must be greater than diastolic pressure."),
            )

        # ----------------------------------------------------

        # PAIN

        # ----------------------------------------------------

        pain_status = cleaned_data.get("pain_status")

        pain_score = cleaned_data.get("pain_score")

        pain_location = (cleaned_data.get("pain_location") or "").strip()

        pain_characteristics = (cleaned_data.get("pain_characteristics") or "").strip()

        if pain_status == VitalObservation.PainStatus.YES:
            if pain_score is None:
                self.add_error(
                    "pain_score",
                    ("Enter a pain score when pain is present."),
                )

            if not pain_location:
                self.add_error(
                    "pain_location",
                    "Select the pain location.",
                )

            if not pain_characteristics:
                self.add_error(
                    "pain_characteristics",
                    ("Describe the pain characteristics."),
                )

        elif str(pain_status) == "no":
            # Explicit absence of pain is represented as 0/10.

            cleaned_data["pain_score"] = 0

            cleaned_data["pain_location"] = ""

            cleaned_data["pain_characteristics"] = ""

        else:
            # Not assessed / blank should not imply a score.

            if pain_status and pain_score is not None:
                self.add_error(
                    "pain_score",
                    (
                        "A pain score should only be entered "
                        "when pain assessment is documented."
                    ),
                )

            cleaned_data["pain_location"] = ""

            cleaned_data["pain_characteristics"] = ""

        # ----------------------------------------------------

        # OXYGEN

        # ----------------------------------------------------

        oxygen_method = cleaned_data.get("oxygen_delivery_method")

        oxygen_flow = cleaned_data.get("oxygen_flow_lpm")

        if oxygen_flow is not None and not oxygen_method:
            self.add_error(
                "oxygen_delivery_method",
                ("Select an oxygen delivery method when documenting oxygen flow."),
            )

        if oxygen_method == VitalObservation.OxygenDeliveryMethod.ROOM_AIR:
            # Room air cannot have supplemental oxygen flow.

            # Clearing the value also protects against stale hidden

            # values after the clinician changes the selection.

            cleaned_data["oxygen_flow_lpm"] = None

        # ----------------------------------------------------

        # UPDATE / CORRECTION

        # ----------------------------------------------------

        if self.is_update:
            correction_reason = (cleaned_data.get("correction_reason") or "").strip()

            changed_clinical_fields = self._changed_clinical_fields()

            if changed_clinical_fields and not correction_reason:
                self.add_error(
                    "correction_reason",
                    (
                        "Provide a reason for changing this "
                        "previously recorded observation."
                    ),
                )

        return cleaned_data

    # ========================================================

    # SAVE

    # ========================================================

    def save(self, commit=True):

        instance = super().save(commit=False)

        # ----------------------------------------------------

        # PATIENT / ENCOUNTER

        # ----------------------------------------------------

        instance.patient = self.selected_patient

        instance.encounter = self.selected_encounter

        # ----------------------------------------------------

        # CREATE

        # ----------------------------------------------------

        if self.is_create:
            instance.recorded_at = self.observation_datetime

            instance.status = VitalObservation.RecordStatus.FINAL

        # ----------------------------------------------------

        # UPDATE / CORRECTION

        # ----------------------------------------------------

        elif self.is_update:
            if self._changed_clinical_fields():
                instance.status = VitalObservation.RecordStatus.CORRECTED

        # ----------------------------------------------------

        # AUDITED SAVE

        # ----------------------------------------------------

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
                    "Explain why this vital-sign observation was entered in error."
                ),
                "aria-label": ("Reason vital observation was entered in error"),
            }
        ),
    )

    def clean_reason(self):

        reason = self.cleaned_data["reason"].strip()

        if len(reason) < 5:
            raise forms.ValidationError(
                ("Provide a clear reason with at least five characters.")
            )

        return reason
