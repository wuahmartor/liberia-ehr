from django.db import migrations


BODY_SYSTEMS = [
    {
        "section": "Neurological",
        "status": "neurological-status",
        "details": [
            ("level-of-consciousness", "Level of consciousness", "choice", ["Alert", "Responds to voice", "Responds to pain", "Unresponsive"]),
            ("orientation", "Orientation", "choice", ["Oriented x4", "Person only", "Place only", "Time only", "Disoriented"]),
            ("neuro-pupils", "Pupils", "choice", ["PERRLA", "Brisk", "Sluggish", "Fixed", "Unequal"]),
            ("neuro-speech", "Speech", "choice", ["Clear", "Slurred", "Aphasic", "Nonverbal"]),
        ],
    },
    {
        "section": "Respiratory",
        "status": "respiratory-status",
        "details": [
            ("respiratory-pattern", "Respiratory pattern", "choice", ["Regular", "Labored", "Shallow", "Apneic"]),
            ("lung-sounds", "Lung sounds", "choice", ["Clear", "Diminished", "Crackles", "Wheezes", "Rhonchi"]),
            ("oxygen-device", "Oxygen device", "choice", ["Room air", "Nasal cannula", "Simple mask", "Non-rebreather", "Other"]),
            ("respiratory-secretions", "Cough / secretions", "text", []),
        ],
    },
    {
        "section": "Cardiovascular",
        "status": "cardiovascular-status",
        "details": [
            ("cardiac-rhythm", "Cardiac rhythm", "choice", ["Regular", "Irregular", "Telemetry monitored"]),
            ("edema", "Edema", "choice", ["None", "Trace", "1+", "2+", "3+", "4+"]),
            ("peripheral-pulses", "Peripheral pulses", "choice", ["Strong", "Moderate", "Weak", "Absent", "Unequal"]),
            ("cardiovascular-symptoms", "Chest pain / symptoms", "text", []),
        ],
    },
    {
        "section": "Gastrointestinal",
        "status": "gastrointestinal-status",
        "details": [
            ("bowel-sounds", "Bowel sounds", "choice", ["Active", "Hypoactive", "Hyperactive", "Absent"]),
            ("abdomen", "Abdomen", "choice", ["Soft", "Firm", "Distended", "Tender", "Rigid"]),
            ("gi-symptoms", "Nausea / vomiting / stool", "text", []),
        ],
    },
    {
        "section": "Genitourinary",
        "status": "genitourinary-status",
        "details": [
            ("urinary-method", "Urinary method", "choice", ["Voiding", "Indwelling catheter", "External catheter", "Anuric", "Other"]),
            ("urine-characteristics", "Urine characteristics", "text", []),
            ("gu-symptoms", "Genitourinary symptoms", "text", []),
        ],
    },
    {
        "section": "Musculoskeletal and Mobility",
        "status": "musculoskeletal-status",
        "details": [
            ("mobility", "Mobility", "choice", ["Independent", "Standby assist", "One-person assist", "Two-person assist", "Bedrest"]),
            ("gait", "Gait", "choice", ["Steady", "Unsteady", "Unable to assess"]),
            ("range-of-motion", "Range of motion", "choice", ["Full", "Limited", "Contracture", "Unable to assess"]),
        ],
    },
    {
        "section": "Integumentary",
        "status": "integumentary-status",
        "details": [
            ("skin-integrity", "Skin integrity", "choice", ["Intact", "At risk", "Impaired"]),
            ("skin-color", "Skin color / temperature", "text", []),
            ("wound-details", "Wound / pressure injury details", "text", []),
        ],
    },
    {
        "section": "Pain",
        "status": "pain-status",
        "details": [
            ("pain-score", "Pain score", "number", []),
            ("pain-location", "Pain location", "text", []),
            ("pain-quality", "Pain quality", "text", []),
            ("pain-intervention", "Intervention", "text", []),
        ],
    },
    {
        "section": "Safety",
        "status": "safety-status",
        "details": [
            ("fall-precautions", "Fall precautions in place", "boolean", []),
            ("safety-concerns", "Safety concerns", "text", []),
            ("restraints", "Restraints", "choice", ["None", "In use per order", "Alternatives attempted"]),
        ],
    },
]


def organize(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if nursing:
        order = 0
        for system in BODY_SYSTEMS:
            order += 10
            Field.objects.update_or_create(
                flowsheet=nursing,
                key=system["status"],
                defaults={
                    "label": "System assessment",
                    "data_type": "choice",
                    "choices": ["WNL", "Abnormal", "Unable to assess"],
                    "section": system["section"],
                    "subsection": "",
                    "display_order": order,
                    "is_required": True,
                },
            )
            for key, label, data_type, choices in system["details"]:
                order += 1
                defaults = {
                    "label": label,
                    "data_type": data_type,
                    "choices": choices,
                    "section": system["section"],
                    "subsection": "Focused abnormal assessment",
                    "show_when_field_key": system["status"],
                    "show_when_value": "Abnormal",
                    "display_order": order,
                }
                if key == "pain-score":
                    defaults.update({"unit": "/10", "normal_min": 0, "normal_max": 3, "critical_max": 8})
                Field.objects.update_or_create(flowsheet=nursing, key=key, defaults=defaults)

    io = Definition.objects.filter(slug="intake-output").first()
    if io:
        for field in io.fields.all():
            field.section = "Intake" if "intake" in field.key else "Output"
            field.save(update_fields=["section"])

    neuro = Definition.objects.filter(slug="neurological-checks").first()
    if neuro:
        section_by_key = {
            "gcs-eye": "Glasgow Coma Scale", "gcs-verbal": "Glasgow Coma Scale", "gcs-motor": "Glasgow Coma Scale",
            "pupils": "Pupils", "left-grip": "Motor response", "right-grip": "Motor response", "speech": "Speech",
        }
        for field in neuro.fields.all():
            field.section = section_by_key.get(field.key, "Neurological assessment")
            field.save(update_fields=["section"])


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0003_flowsheetfielddefinition_section_and_more")]
    operations = [migrations.RunPython(organize, migrations.RunPython.noop)]
