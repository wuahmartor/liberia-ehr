from django.db import migrations


LUNG_SOUNDS = [
    "Clear / vesicular",
    "Diminished",
    "Absent",
    "Fine crackles",
    "Coarse crackles",
    "Wheeze",
    "Rhonchi",
    "Bronchial",
    "Pleural friction rub",
    "Unable to assess",
]

LOBE_FIELDS = [
    ("lung-sounds-rul", "Right upper lobe (RUL)", 310),
    ("lung-sounds-rml", "Right middle lobe (RML)", 311),
    ("lung-sounds-rll", "Right lower lobe (RLL)", 312),
    ("lung-sounds-lul", "Left upper lobe (LUL)", 313),
    ("lung-sounds-lll", "Left lower lobe (LLL)", 314),
]

MOTOR_ORDER = [
    ("neuro-lue-motor", 210),
    ("neuro-rue-motor", 211),
    ("neuro-lle-motor", 212),
    ("neuro-rle-motor", 213),
]

SENSORY_ORDER = [
    ("neuro-lue-sensation", 220),
    ("neuro-rue-sensation", 221),
    ("neuro-lle-sensation", 222),
    ("neuro-rle-sensation", 223),
]


def structure_assessment(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    for key, order in MOTOR_ORDER:
        Field.objects.filter(flowsheet=nursing, key=key).update(
            label=key.replace("neuro-", "").replace("-motor", "").upper(),
            subsection="Motor response",
            display_order=order,
        )
    for key, order in SENSORY_ORDER:
        Field.objects.filter(flowsheet=nursing, key=key).update(
            label=key.replace("neuro-", "").replace("-sensation", "").upper(),
            subsection="Sensory response",
            display_order=order,
        )

    for key, label, order in LOBE_FIELDS:
        Field.objects.update_or_create(
            flowsheet=nursing,
            key=key,
            defaults={
                "label": label,
                "data_type": "multi_choice",
                "choices": LUNG_SOUNDS,
                "section": "Respiratory",
                "subsection": "Breath sounds by lobe",
                "show_when_field_key": "respiratory-status",
                "show_when_value": "Abnormal",
                "display_order": order,
                "is_required": True,
                "help_text": "Select every sound heard in this lobe; choose Unable to assess when appropriate.",
            },
        )

    Field.objects.filter(flowsheet=nursing, key="lung-sounds").update(
        label="Additional breath-sound summary (legacy)",
        subsection="Additional respiratory details",
        display_order=390,
        is_required=False,
    )
    Field.objects.filter(flowsheet=nursing, key="lung-location").update(
        label="Additional affected fields (legacy)",
        subsection="Additional respiratory details",
        display_order=391,
        is_required=False,
    )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0009_order_neurological_rows")]
    operations = [migrations.RunPython(structure_assessment, migrations.RunPython.noop)]
