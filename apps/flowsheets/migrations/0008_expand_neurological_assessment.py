from django.db import migrations


GCS_FIELDS = [
    ("gcs-interfering-factors", "Factors interfering with GCS assessment", "multi_choice", ["None", "Intubated / tracheostomy", "Sedation / paralytic", "Language barrier", "Hearing impairment", "Periorbital injury", "Spinal cord / limb injury", "Baseline cognitive impairment"], 1, False, "Check for factors that interfere with communication or ability to respond."),
    ("gcs-eye", "GCS eye opening (E)", "choice", ["4 — Spontaneous", "3 — To sound", "2 — To pressure", "1 — None", "NT — Non-testable"], 2, True, "Observe first, then stimulate if needed; record the highest response."),
    ("gcs-verbal", "GCS verbal response (V)", "choice", ["5 — Orientated", "4 — Confused", "3 — Words", "2 — Sounds", "1 — None", "NT — Non-testable"], 3, True, "Record the best observed verbal response and any interfering factor."),
    ("gcs-motor", "GCS motor response (M)", "choice", ["6 — Obeys commands", "5 — Localising", "4 — Normal flexion", "3 — Abnormal flexion", "2 — Extension", "1 — None", "NT — Non-testable"], 4, True, "Compare right and left sides; record the highest response and document asymmetry below."),
    ("gcs-total", "GCS total", "number", [], 5, False, "Automatically derived when E, V and M are all testable; report components as well as the total."),
    ("right-pupil-size", "Right pupil size", "number", [], 10, False, "Millimetres"),
    ("right-pupil-reactivity", "Right pupil reactivity", "choice", ["Brisk", "Sluggish", "Fixed", "Unable to assess"], 11, False, "Assess each pupil independently."),
    ("left-pupil-size", "Left pupil size", "number", [], 12, False, "Millimetres"),
    ("left-pupil-reactivity", "Left pupil reactivity", "choice", ["Brisk", "Sluggish", "Fixed", "Unable to assess"], 13, False, "Assess each pupil independently."),
]

LIMBS = (("rue", "RUE"), ("lue", "LUE"), ("rle", "RLE"), ("lle", "LLE"))


def expand_neurological_assessment(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    neuro = Definition.objects.filter(slug="neurological-checks").first()
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()

    if neuro:
        for key, label, data_type, choices, order, required, help_text in GCS_FIELDS:
            unit = "mm" if key.endswith("pupil-size") else ""
            Field.objects.update_or_create(
                flowsheet=neuro,
                key=key,
                defaults={"label": label, "data_type": data_type, "choices": choices, "unit": unit, "section": "Glasgow Coma Scale" if key.startswith("gcs-") else "Pupils", "subsection": "", "display_order": order, "is_required": required, "help_text": help_text},
            )
        order = 20
        for key, label in LIMBS:
            Field.objects.update_or_create(
                flowsheet=neuro, key=f"{key}-motor-strength",
                defaults={"label": f"{label} motor strength", "data_type": "choice", "choices": ["5 — Full strength", "4 — Movement against resistance", "3 — Movement against gravity", "2 — Movement without gravity", "1 — Muscle contraction only", "0 — No contraction", "Unable to assess"], "section": "Bilateral motor examination", "subsection": "", "display_order": order, "is_required": False, "help_text": "Document each extremity separately."},
            )
            order += 1
            Field.objects.update_or_create(
                flowsheet=neuro, key=f"{key}-sensation",
                defaults={"label": f"{label} sensation", "data_type": "multi_choice", "choices": ["Intact", "Decreased", "Absent", "Numbness", "Tingling / paresthesia", "Unable to assess"], "section": "Bilateral sensory examination", "subsection": "", "display_order": order, "is_required": False, "help_text": "Localizes sensory symptoms to this extremity."},
            )
            order += 1
        Field.objects.update_or_create(
            flowsheet=neuro, key="motor-asymmetry-details",
            defaults={"label": "Motor asymmetry / drift details", "data_type": "text", "choices": [], "section": "Bilateral motor examination", "subsection": "", "display_order": 29, "is_required": False, "help_text": "Describe pronator drift, unilateral response, or other asymmetry."},
        )

    if nursing:
        order = 210
        for key, label in LIMBS:
            Field.objects.update_or_create(
                flowsheet=nursing, key=f"neuro-{key}-motor",
                defaults={"label": f"{label} motor finding", "data_type": "choice", "choices": ["Moves to command", "Strong", "Weak", "Flaccid", "Spastic", "No movement", "Unable to assess"], "section": "Neurological", "subsection": "Focused abnormal assessment", "show_when_field_key": "neurological-status", "show_when_value": "Abnormal", "display_order": order, "is_required": True, "help_text": "Record each extremity independently."},
            )
            order += 1
            Field.objects.update_or_create(
                flowsheet=nursing, key=f"neuro-{key}-sensation",
                defaults={"label": f"{label} sensation", "data_type": "multi_choice", "choices": ["Intact", "Decreased", "Absent", "Numbness", "Tingling / paresthesia", "Unable to assess"], "section": "Neurological", "subsection": "Focused abnormal assessment", "show_when_field_key": "neurological-status", "show_when_value": "Abnormal", "display_order": order, "is_required": True, "help_text": "Localizes sensory findings to this extremity."},
            )
            order += 1


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0007_refine_musculoskeletal_assessment")]
    operations = [migrations.RunPython(expand_neurological_assessment, migrations.RunPython.noop)]
