from django.db import migrations


DEFINITIONS = [
    {
        "name": "Nursing Systems Assessment",
        "slug": "nursing-systems-assessment",
        "category": "nursing",
        "description": "Focused head-to-toe nursing assessment for longitudinal charting.",
        "fields": [
            ("level-of-consciousness", "Level of consciousness", "choice", ["Alert", "Responds to voice", "Responds to pain", "Unresponsive"], ""),
            ("orientation", "Orientation", "choice", ["Oriented x4", "Person only", "Place only", "Time only", "Disoriented"], ""),
            ("respiratory-pattern", "Respiratory pattern", "choice", ["Regular", "Labored", "Shallow", "Apneic"], ""),
            ("lung-sounds", "Lung sounds", "choice", ["Clear", "Diminished", "Crackles", "Wheezes", "Rhonchi"], ""),
            ("cardiac-rhythm", "Cardiac rhythm", "choice", ["Regular", "Irregular", "Telemetry monitored"], ""),
            ("edema", "Edema", "choice", ["None", "Trace", "1+", "2+", "3+", "4+"], ""),
            ("bowel-sounds", "Bowel sounds", "choice", ["Active", "Hypoactive", "Hyperactive", "Absent"], ""),
            ("mobility", "Mobility", "choice", ["Independent", "Standby assist", "One-person assist", "Two-person assist", "Bedrest"], ""),
            ("skin-integrity", "Skin integrity", "choice", ["Intact", "At risk", "Impaired"], ""),
            ("fall-precautions", "Fall precautions in place", "boolean", [], ""),
        ],
    },
    {
        "name": "Intake and Output",
        "slug": "intake-output",
        "category": "intake_output",
        "description": "Discrete fluid intake and output measurements.",
        "fields": [
            ("oral-intake", "Oral intake", "number", [], "mL"),
            ("iv-intake", "IV intake", "number", [], "mL"),
            ("tube-feed-intake", "Tube feed intake", "number", [], "mL"),
            ("urine-output", "Urine output", "number", [], "mL"),
            ("emesis-output", "Emesis output", "number", [], "mL"),
            ("drain-output", "Drain output", "number", [], "mL"),
            ("stool-count", "Stool count", "number", [], "count"),
        ],
    },
    {
        "name": "Neurological Checks",
        "slug": "neurological-checks",
        "category": "neurological",
        "description": "Repeatable neurological observations and Glasgow Coma Scale components.",
        "fields": [
            ("gcs-eye", "GCS eye response", "number", [], "1–4"),
            ("gcs-verbal", "GCS verbal response", "number", [], "1–5"),
            ("gcs-motor", "GCS motor response", "number", [], "1–6"),
            ("pupils", "Pupil response", "choice", ["PERRLA", "Brisk", "Sluggish", "Fixed", "Unequal"], ""),
            ("left-grip", "Left hand grip", "choice", ["Strong", "Moderate", "Weak", "Absent"], ""),
            ("right-grip", "Right hand grip", "choice", ["Strong", "Moderate", "Weak", "Absent"], ""),
            ("speech", "Speech", "choice", ["Clear", "Slurred", "Expressive aphasia", "Receptive aphasia", "Nonverbal"], ""),
        ],
    },
]


def seed_flowsheets(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    for definition_data in DEFINITIONS:
        fields = definition_data["fields"]
        definition_defaults = {key: value for key, value in definition_data.items() if key != "fields"}
        definition, _ = Definition.objects.update_or_create(
            slug=definition_data["slug"], defaults={**definition_defaults, "is_system": True, "is_active": True}
        )
        for order, (key, label, data_type, choices, unit) in enumerate(fields, start=1):
            Field.objects.update_or_create(
                flowsheet=definition,
                key=key,
                defaults={"label": label, "data_type": data_type, "choices": choices, "unit": unit, "display_order": order},
            )


def unseed_flowsheets(apps, schema_editor):
    apps.get_model("flowsheets", "FlowSheetDefinition").objects.filter(slug__in=[item["slug"] for item in DEFINITIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0001_initial")]
    operations = [migrations.RunPython(seed_flowsheets, unseed_flowsheets)]
