from django.db import migrations


PULSE_CHOICES = [
    "0 — Absent",
    "1+ — Weak",
    "2+ — Normal",
    "3+ — Increased",
    "4+ — Bounding",
    "Doppler only",
    "Unable to assess",
]

PULSE_FIELDS = [
    ("pulse-left-radial", "Left radial pulse", 316),
    ("pulse-right-radial", "Right radial pulse", 317),
    ("pulse-left-dorsalis-pedis", "Left dorsalis pedis pulse", 318),
    ("pulse-right-dorsalis-pedis", "Right dorsalis pedis pulse", 319),
    ("pulse-left-posterior-tibial", "Left posterior tibial pulse", 320),
    ("pulse-right-posterior-tibial", "Right posterior tibial pulse", 321),
]


def structure_cardiovascular(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    Field.objects.filter(flowsheet=nursing, key="peripheral-pulses").update(is_active=False)
    for key, label, order in PULSE_FIELDS:
        Field.objects.update_or_create(
            flowsheet=nursing,
            key=key,
            defaults={
                "label": label,
                "data_type": "choice",
                "choices": PULSE_CHOICES,
                "section": "Cardiovascular",
                "subsection": "Focused abnormal assessment",
                "show_when_field_key": "cardiovascular-status",
                "show_when_value": "Abnormal",
                "display_order": order,
                "is_required": False,
                "is_active": True,
                "help_text": "Document this pulse independently.",
            },
        )

    ordering = {
        "capillary-refill": 322,
        "edema": 323,
        "edema-location": 324,
        "edema-laterality": 325,
        "edema-grade": 326,
        "cardiovascular-symptoms": 327,
    }
    for key, order in ordering.items():
        updates = {"display_order": order}
        if key.startswith("edema-"):
            updates.update({
                "label": "Edema — " + key.removeprefix("edema-").replace("-", " "),
                "subsection": "Focused abnormal assessment",
                "show_when_field_key": "cardiovascular-status",
                "show_when_value": "Abnormal",
                "is_required": False,
            })
        Field.objects.filter(flowsheet=nursing, key=key).update(**updates)


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0011_compact_extremity_findings")]
    operations = [migrations.RunPython(structure_cardiovascular, migrations.RunPython.noop)]
