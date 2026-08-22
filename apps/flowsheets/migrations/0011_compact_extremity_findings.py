from django.db import migrations, models


EXTREMITY_FINDINGS = [
    "WNL", "Weakness", "Flaccid", "Spastic", "No movement", "Pronator drift",
    "Numbness", "Tingling / paresthesia", "Decreased sensation", "Absent sensation",
    "Pain", "Unable to assess",
]

EXTREMITIES = [
    ("neuro-lue-findings", "LUE", 210),
    ("neuro-rue-findings", "RUE", 211),
    ("neuro-lle-findings", "LLE", 212),
    ("neuro-rle-findings", "RLE", 213),
]

RETIRED_KEYS = [
    "neuro-motor", "neuro-sensation",
    "neuro-lue-motor", "neuro-rue-motor", "neuro-lle-motor", "neuro-rle-motor",
    "neuro-lue-sensation", "neuro-rue-sensation", "neuro-lle-sensation", "neuro-rle-sensation",
    "lung-sounds", "lung-location",
]


def create_compact_findings(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return
    Field.objects.filter(flowsheet=nursing, key__in=RETIRED_KEYS).update(is_active=False)
    for key, label, order in EXTREMITIES:
        Field.objects.update_or_create(
            flowsheet=nursing,
            key=key,
            defaults={
                "label": label,
                "data_type": "multi_choice",
                "choices": EXTREMITY_FINDINGS,
                "section": "Neurological",
                "subsection": "Extremity findings",
                "show_when_field_key": "neurological-status",
                "show_when_value": "Abnormal",
                "display_order": order,
                "is_required": True,
                "is_active": True,
                "help_text": "Select WNL or all abnormal motor and sensory findings for this extremity.",
            },
        )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0010_structure_motor_and_lung_lobes")]
    operations = [
        migrations.AddField(
            model_name="flowsheetfielddefinition",
            name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.RunPython(create_compact_findings, migrations.RunPython.noop),
    ]
