"""
============================================================
CLINICAL NOTES FORMS

File:
apps/clinical_notes/forms.py

Purpose:
- Provide compact Tailwind-styled clinical note forms.
- Restrict encounter choices to the selected patient.
- Keep system-generated authorship/signature fields outside
  normal clinician input.
============================================================
"""

from django import forms

from apps.encounters.models import Encounter

from .models import ClinicalNote


# ============================================================
# SHARED TAILWIND CLASSES
# ============================================================

INPUT_CLASS = """
block h-8 w-full rounded-md border border-slate-300 bg-white
px-2 text-xs text-slate-800 shadow-sm outline-none
placeholder:text-slate-400
focus:border-ehr-500 focus:ring-1 focus:ring-ehr-500
""".strip()


TEXTAREA_CLASS = """
block min-h-[86px] w-full resize-y rounded-md
border border-slate-300 bg-white
px-2.5 py-2 text-xs leading-5 text-slate-800
shadow-sm outline-none
placeholder:text-slate-400
focus:border-emerald-500
focus:ring-1 focus:ring-emerald-500
""".strip()


class ClinicalNoteForm(forms.ModelForm):
    """
    Clinical documentation form.

    System-managed fields such as author, created_by, signed_by,
    and timestamps are intentionally excluded.
    """

    class Meta:
        model = ClinicalNote

        fields = [
            "note_type",
            "encounter",
            "chief_complaint",
            "title",
            "subjective",
            "objective",
            "assessment",
            "plan",
            "content",
        ]

        widgets = {
            "note_type": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "encounter": forms.Select(
                attrs={
                    "class": INPUT_CLASS,
                }
            ),

            "chief_complaint": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": (
                        "e.g. Chest pain, medication follow-up, "
                        "post-operative wound check"
                    ),
                    "autocomplete": "off",
                }
            ),

            "title": forms.TextInput(
                attrs={
                    "class": INPUT_CLASS,
                    "placeholder": "Optional note title",
                    "autocomplete": "off",
                }
            ),

            "subjective": forms.Textarea(

    attrs={

        "class": TEXTAREA_CLASS,

        "rows": 3,

        "placeholder": "Enter relevant clinical information...",

    }

),

    "objective": forms.Textarea(

        attrs={

            "class": TEXTAREA_CLASS,

            "rows": 3,

            "placeholder": "Enter relevant clinical findings...",

        }

    ),

    "assessment": forms.Textarea(

        attrs={

            "class": TEXTAREA_CLASS,

            "rows": 3,

            "placeholder": "Enter clinical assessment...",

        }

    ),

    "plan": forms.Textarea(

        attrs={

            "class": TEXTAREA_CLASS,

            "rows": 3,

            "placeholder": "Enter interventions, recommendations or follow-up...",

        }

    ),

    "content": forms.Textarea(

        attrs={

            "class": TEXTAREA_CLASS,

            "rows": 4,

            "placeholder": "Enter additional clinical documentation...",

        }

    ),
        }

    def __init__(
        self,
        *args,
        patient=None,
        active_encounter=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.patient = patient
        self.active_encounter = active_encounter
       
        # ----------------------------------------------------
        # ENCOUNTER CHOICES
        # ----------------------------------------------------

        if patient is not None:
            self.fields["encounter"].queryset = (
                Encounter.objects
                .filter(patient=patient)
                .order_by("-start_datetime")
            )
        else:
            self.fields["encounter"].queryset = Encounter.objects.none()

        # ----------------------------------------------------
        # DEFAULT ACTIVE ENCOUNTER
        # ----------------------------------------------------

        if (
            not self.is_bound
            and not self.instance.pk
            and active_encounter is not None
        ):
            self.initial["encounter"] = active_encounter

        # ----------------------------------------------------
        # LABELS
        # ----------------------------------------------------

        self.fields["note_type"].label = "Note Type"
        self.fields["encounter"].label = "Encounter"
        self.fields["chief_complaint"].label = "Chief Complaint"
        self.fields["title"].label = "Note Title"
        self.fields["subjective"].label = "Subjective"
        self.fields["objective"].label = "Objective"
        self.fields["assessment"].label = "Assessment"
        self.fields["plan"].label = "Plan"
        self.fields["content"].label = "Additional Documentation"

        self.fields["chief_complaint"].required = True
        self.fields["encounter"].required = False
        self.fields["title"].required = False

    def clean_encounter(self):
        encounter = self.cleaned_data.get("encounter")

        if encounter and self.patient:
            if encounter.patient_id != self.patient.pk:
                raise forms.ValidationError(
                    "The selected encounter does not belong to this patient."
                )

        return encounter

    def clean(self):
        cleaned_data = super().clean()

        clinical_fields = [
            "subjective",
            "objective",
            "assessment",
            "plan",
            "content",
        ]

        has_content = any(
            (
                cleaned_data.get(field_name)
                and cleaned_data.get(field_name).strip()
            )
            for field_name in clinical_fields
        )

        if not has_content:
            raise forms.ValidationError(
                "Enter documentation in at least one clinical section."
            )

        return cleaned_data
