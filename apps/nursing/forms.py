from django import forms
from django.contrib.auth import get_user_model

from .models import (
    IntakeOutputRecord,
    NursingAssessment,
    NursingHandoff,
    NursingTask,
)

CONTROL = (
    "min-h-10 w-full rounded border border-slate-300 bg-white "
    "px-3 py-2 text-sm leading-5 text-slate-900"
)
TEXTAREA = (
    "min-h-20 w-full rounded border border-slate-300 bg-white "
    "p-3 text-xs leading-5 text-slate-900"
)


class CompactModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                TEXTAREA if isinstance(field.widget, forms.Textarea) else CONTROL,
            )


class NursingAssessmentForm(CompactModelForm):
    SYSTEM_FIELDS = {
        "Neurological": (
            "neurological_status",
            "consciousness",
            "orientation",
            "pupils",
            "speech",
            "motor_strength",
            "neurological",
        ),
        "Respiratory": (
            "respiratory_status",
            "respiratory_pattern",
            "respiratory_effort",
            "breath_sounds",
            "breath_sound_laterality",
            "lung_rul",
            "lung_rml",
            "lung_rll",
            "lung_lul",
            "lung_lll",
            "cough",
            "oxygen_support",
            "respiratory",
        ),
        "Cardiovascular": (
            "cardiovascular_status",
            "cardiac_rhythm",
            "heart_sounds",
            "peripheral_pulses",
            "pulse_laterality",
            "capillary_refill",
            "edema_grade",
            "edema_location",
            "cardiovascular",
        ),
        "Gastrointestinal": (
            "gastrointestinal_status",
            "abdomen",
            "bowel_sounds",
            "bowel_sounds_exception_quadrant",
            "nausea_vomiting",
            "last_bowel_movement",
            "diet_tolerance",
        ),
        "Genitourinary": (
            "genitourinary_status",
            "urinary_pattern",
            "urine_characteristics",
            "urinary_device",
        ),
        "Integumentary": (
            "integumentary_status",
            "skin_color",
            "skin_temperature",
            "skin_moisture",
            "skin_integrity",
            "wound_location",
            "pressure_injury_stage",
            "skin",
        ),
        "Musculoskeletal": (
            "musculoskeletal_status",
            "motor_strength",
            "gait",
            "assistive_device",
            "activity_tolerance",
            "mobility",
        ),
        "Psychosocial": (
            "psychosocial_status",
            "mood_affect",
            "behavior",
            "communication_needs",
        ),
    }
    SYSTEM_STATUSES = {
        "Neurological": "neurological_status",
        "Respiratory": "respiratory_status",
        "Cardiovascular": "cardiovascular_status",
        "Gastrointestinal": "gastrointestinal_status",
        "Genitourinary": "genitourinary_status",
        "Integumentary": "integumentary_status",
        "Musculoskeletal": "musculoskeletal_status",
        "Psychosocial": "psychosocial_status",
    }

    class Meta:
        model = NursingAssessment
        exclude = ("patient", "encounter", "recorded_by", "recorded_at")
        widgets = {
            "last_bowel_movement": forms.DateInput(attrs={"type": "date"}),
            "narrative": forms.Textarea(attrs={"rows": 2}),
            "respiratory": forms.Textarea(attrs={"rows": 2}),
            "cardiovascular": forms.Textarea(attrs={"rows": 2}),
            "neurological": forms.Textarea(attrs={"rows": 2}),
            "skin": forms.Textarea(attrs={"rows": 2}),
            "mobility": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assessment_type"].widget.attrs.update(
            {
                "x-model": "assessmentType",
                "class": (
                    "block min-h-11 w-full max-w-full rounded border "
                    "border-slate-300 bg-white px-3 py-2 text-sm "
                    "font-medium leading-6 text-slate-900"
                ),
                "aria-label": "Assessment type",
            }
        )
        self.fields["assessment_type"].choices = (
            ("", "Select assessment type…"),
            (NursingAssessment.AssessmentType.ADMISSION, "Admission"),
            (NursingAssessment.AssessmentType.SHIFT, "Shift"),
            (NursingAssessment.AssessmentType.FOCUSED, "Focused"),
            (NursingAssessment.AssessmentType.TRANSFER, "Transfer"),
            (NursingAssessment.AssessmentType.DISCHARGE, "Discharge"),
            (NursingAssessment.AssessmentType.POST_PROCEDURE, "Post-procedure"),
            (
                NursingAssessment.AssessmentType.CHANGE_IN_CONDITION,
                "Change in condition",
            ),
        )
        for fields in self.SYSTEM_FIELDS.values():
            for name in fields:
                self.fields[name].required = False
        choices = {
            "neurological_status": ("WNL", "Exception identified"),
            "respiratory_status": ("WNL", "Exception identified"),
            "cardiovascular_status": ("WNL", "Exception identified"),
            "gastrointestinal_status": ("WNL", "Exception identified"),
            "genitourinary_status": ("WNL", "Exception identified"),
            "integumentary_status": ("WNL", "Exception identified"),
            "musculoskeletal_status": ("WNL", "Exception identified"),
            "psychosocial_status": ("WNL", "Exception identified"),
            "consciousness": (
                "Alert",
                "Drowsy",
                "Lethargic",
                "Stuporous",
                "Unresponsive",
            ),
            "orientation": (
                "Oriented ×4",
                "Oriented ×3",
                "Oriented ×2",
                "Oriented ×1",
                "Disoriented",
            ),
            "pupils": ("PERRLA", "Equal/reactive", "Sluggish", "Unequal", "Fixed"),
            "speech": ("Clear", "Slurred", "Aphasic", "Nonverbal"),
            "motor_strength": (
                "5/5 equal",
                "4/5",
                "3/5",
                "2/5",
                "1/5",
                "0/5",
                "Unequal",
            ),
            "respiratory_pattern": (
                "Regular",
                "Tachypneic",
                "Bradypneic",
                "Apneic",
                "Irregular",
            ),
            "respiratory_effort": (
                "Unlabored",
                "Labored",
                "Accessory muscle use",
                "Retractions",
            ),
            "breath_sounds": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "breath_sound_laterality": ("Bilateral", "Left", "Right"),
            "lung_rul": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "lung_rml": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "lung_rll": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "lung_lul": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "lung_lll": (
                "Clear",
                "Diminished",
                "Crackles",
                "Wheezes",
                "Rhonchi",
                "Absent",
            ),
            "cough": ("None", "Dry", "Productive", "Weak"),
            "oxygen_support": (
                "Room air",
                "Nasal cannula",
                "Simple mask",
                "Non-rebreather",
                "High-flow",
                "Ventilator",
            ),
            "cardiac_rhythm": (
                "Regular",
                "Irregular",
                "Telemetry monitored",
                "Not monitored",
            ),
            "heart_sounds": ("S1/S2 normal", "Murmur", "Gallop", "Rub", "Distant"),
            "peripheral_pulses": (
                "3+ bounding",
                "2+ normal",
                "1+ weak",
                "Doppler only",
                "Absent",
            ),
            "pulse_laterality": (
                "Bilateral equal",
                "Left diminished",
                "Right diminished",
                "Unequal",
            ),
            "capillary_refill": ("≤2 seconds", "3 seconds", ">3 seconds"),
            "edema_grade": ("None", "Trace", "1+", "2+", "3+", "4+", "Non-pitting"),
            "skin_color": (
                "Appropriate",
                "Pale",
                "Cyanotic",
                "Jaundiced",
                "Flushed",
                "Mottled",
            ),
            "skin_temperature": ("Warm", "Cool", "Hot", "Cold"),
            "skin_moisture": ("Dry", "Diaphoretic", "Moist"),
            "skin_integrity": (
                "Intact",
                "Impaired",
                "Incision",
                "Pressure injury",
                "Rash",
            ),
            "pressure_injury_stage": (
                "None",
                "Stage 1",
                "Stage 2",
                "Stage 3",
                "Stage 4",
                "Unstageable",
                "Deep tissue injury",
            ),
            "gait": ("Steady", "Unsteady", "Unable to assess", "Bedbound"),
            "assistive_device": (
                "None",
                "Cane",
                "Walker",
                "Wheelchair",
                "Staff assistance",
            ),
            "activity_tolerance": (
                "Tolerates activity",
                "Fatigues easily",
                "Dyspnea on exertion",
                "Bedrest",
            ),
            "abdomen": ("Soft/non-tender", "Tender", "Distended", "Rigid"),
            "bowel_sounds": ("Normoactive", "Hypoactive", "Hyperactive", "Absent"),
            "bowel_sounds_exception_quadrant": (
                "No exception",
                "RUQ",
                "LUQ",
                "RLQ",
                "LLQ",
                "Multiple quadrants",
            ),
            "nausea_vomiting": ("None", "Nausea", "Vomiting", "Both"),
            "diet_tolerance": ("Tolerating", "Poor intake", "NPO", "Tube feeding"),
            "urinary_pattern": (
                "Voiding normally",
                "Frequency",
                "Urgency",
                "Retention",
                "Incontinent",
                "Anuric",
            ),
            "urine_characteristics": (
                "Clear/yellow",
                "Dark",
                "Cloudy",
                "Bloody",
                "Malodorous",
            ),
            "urinary_device": (
                "None",
                "Indwelling catheter",
                "External catheter",
                "Suprapubic catheter",
                "Urostomy",
            ),
            "mood_affect": (
                "Calm/appropriate",
                "Anxious",
                "Depressed",
                "Flat",
                "Labile",
            ),
            "behavior": (
                "Cooperative",
                "Restless",
                "Agitated",
                "Withdrawn",
                "Combative",
            ),
        }
        for name, values in choices.items():
            values = tuple(value for value in values if value != "WNL")
            self.fields[name].widget = forms.Select(
                choices=(
                    ("", "Select…"),
                    ("WNL", "WNL"),
                    *((value, value) for value in values),
                ),
                attrs={"class": CONTROL},
            )
        self.fields["bowel_sounds"].widget.attrs["x-model"] = "bowelSounds"
        for system, status_name in self.SYSTEM_STATUSES.items():
            self.fields[status_name].widget.attrs["x-model"] = (
                f"systemStatus.{system.lower()}"
            )
        self.fields["focused_system"].widget = forms.Select(
            choices=(
                ("", "Select system…"),
                *((name, name) for name in self.SYSTEM_FIELDS),
            ),
            attrs={"class": CONTROL},
        )

    def clean(self):
        cleaned = super().clean()
        assessment_type = cleaned.get("assessment_type")
        requirements = {
            NursingAssessment.AssessmentType.ADMISSION: (
                "admission_source",
                "baseline_function",
            ),
            NursingAssessment.AssessmentType.FOCUSED: (
                "focused_system",
                "focused_findings",
            ),
            NursingAssessment.AssessmentType.TRANSFER: ("transfer_destination",),
            NursingAssessment.AssessmentType.DISCHARGE: (
                "discharge_disposition",
                "education_and_readiness",
            ),
            NursingAssessment.AssessmentType.POST_PROCEDURE: (
                "procedure_and_recovery",
            ),
            NursingAssessment.AssessmentType.CHANGE_IN_CONDITION: (
                "change_in_condition",
            ),
        }
        for name in requirements.get(assessment_type, ()):
            if not cleaned.get(name):
                self.add_error(name, "Required for this assessment type.")
        comprehensive = assessment_type in (
            NursingAssessment.AssessmentType.ADMISSION,
            NursingAssessment.AssessmentType.SHIFT,
            NursingAssessment.AssessmentType.TRANSFER,
            NursingAssessment.AssessmentType.DISCHARGE,
        )
        systems = (
            self.SYSTEM_FIELDS
            if comprehensive
            else {
                cleaned.get("focused_system"): self.SYSTEM_FIELDS.get(
                    cleaned.get("focused_system"), ()
                )
            }
            if assessment_type == NursingAssessment.AssessmentType.FOCUSED
            else {}
        )
        optional_details = {
            "neurological",
            "respiratory",
            "cardiovascular",
            "skin",
            "mobility",
            "motor_strength",
            "communication_needs",
            "last_bowel_movement",
            "bowel_sounds_exception_quadrant",
            "edema_location",
            "wound_location",
        }
        for system, fields in systems.items():
            if not system:
                continue
            status_name = self.SYSTEM_STATUSES[system]
            status = cleaned.get(status_name)
            if not status:
                self.add_error(status_name, "Select WNL or Exception identified.")
                continue
            if status == "WNL":
                for name in fields:
                    if name != status_name:
                        cleaned[name] = None if name == "last_bowel_movement" else ""
                continue
            if status == "Exception identified":
                for name in fields:
                    if (
                        name != status_name
                        and name not in optional_details
                        and not cleaned.get(name)
                    ):
                        self.add_error(
                            name, f"Required for the {system.lower()} exception."
                        )
        bowel_sounds = cleaned.get("bowel_sounds")
        if (
            cleaned.get("gastrointestinal_status") == "Exception identified"
            and bowel_sounds not in (None, "", "WNL", "Normoactive")
            and not cleaned.get("bowel_sounds_exception_quadrant")
        ):
            self.add_error(
                "bowel_sounds_exception_quadrant",
                "Select the quadrant where the bowel-sound exception was found.",
            )
        return cleaned

    def clean_pain_score(self):
        score = self.cleaned_data["pain_score"]
        if score > 10:
            raise forms.ValidationError("Pain score must be between 0 and 10.")
        return score


class NursingTaskForm(CompactModelForm):
    class Meta:
        model = NursingTask
        fields = ("description", "priority", "due_at")
        widgets = {"due_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class IntakeOutputForm(CompactModelForm):
    class Meta:
        model = IntakeOutputRecord
        fields = ("kind", "source", "volume_ml", "occurred_at", "notes")
        widgets = {"occurred_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}


class NursingHandoffForm(CompactModelForm):
    class Meta:
        model = NursingHandoff
        fields = (
            "given_by",
            "received_by",
            "situation",
            "background",
            "assessment",
            "recommendation",
            "safety_concerns",
        )
        widgets = {
            "situation": forms.Textarea(attrs={"rows": 2}),
            "background": forms.Textarea(attrs={"rows": 2}),
            "assessment": forms.Textarea(attrs={"rows": 2}),
            "recommendation": forms.Textarea(attrs={"rows": 2}),
            "safety_concerns": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop("current_user", None)
        super().__init__(*args, **kwargs)
        users = (
            get_user_model()
            .objects.filter(is_active=True)
            .order_by("last_name", "first_name", "username")
        )
        self.fields["given_by"].queryset = users
        self.fields["received_by"].queryset = users
        self.fields["given_by"].required = True
        self.fields["received_by"].required = True
        if current_user and not self.is_bound:
            self.initial["given_by"] = current_user

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("given_by") == cleaned.get("received_by"):
            self.add_error("received_by", "Handoff receiver must differ from giver.")
        return cleaned
