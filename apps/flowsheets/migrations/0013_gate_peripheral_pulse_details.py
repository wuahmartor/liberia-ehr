from django.db import migrations


PULSE_CHOICES = [
    "0 — Absent", "1+ — Weak", "2+ — Normal", "3+ — Increased",
    "4+ — Bounding", "Doppler only", "Unable to assess",
]

SITES = [
    ("radial", "Radial"),
    ("brachial", "Brachial"),
    ("femoral", "Femoral"),
    ("popliteal", "Popliteal"),
    ("posterior-tibial", "Posterior tibial"),
    ("dorsalis-pedis", "Dorsalis pedis (pedal)"),
]


def gate_pulse_details(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    Field.objects.update_or_create(
        flowsheet=nursing,
        key="peripheral-pulses",
        defaults={
            "label": "Peripheral pulses",
            "data_type": "choice",
            "choices": ["WNL", "Abnormal"],
            "section": "Cardiovascular",
            "subsection": "Focused abnormal assessment",
            "show_when_field_key": "cardiovascular-status",
            "show_when_value": "Abnormal",
            "display_order": 316,
            "is_required": False,
            "is_active": True,
            "help_text": "Select Abnormal to document pulse site, laterality, and grade.",
        },
    )

    order = 317
    active_keys = []
    for site_key, site_label in SITES:
        for side_key, side_label in (("left", "Left"), ("right", "Right")):
            key = f"pulse-{side_key}-{site_key}"
            active_keys.append(key)
            Field.objects.update_or_create(
                flowsheet=nursing,
                key=key,
                defaults={
                    "label": f"{side_label} {site_label}",
                    "data_type": "choice",
                    "choices": PULSE_CHOICES,
                    "section": "Cardiovascular",
                    "subsection": "Peripheral pulse details",
                    "show_when_field_key": "peripheral-pulses",
                    "show_when_value": "Abnormal",
                    "display_order": order,
                    "is_required": False,
                    "is_active": True,
                    "help_text": "Document only when assessed or abnormal.",
                },
            )
            order += 1

    Field.objects.filter(
        flowsheet=nursing, key__startswith="pulse-"
    ).exclude(key__in=active_keys).update(is_active=False)

    for offset, key in enumerate(
        ("capillary-refill", "edema", "edema-location", "edema-laterality", "edema-grade", "cardiovascular-symptoms")
    ):
        Field.objects.filter(flowsheet=nursing, key=key).update(display_order=order + offset)


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0012_structure_cardiovascular_assessment")]
    operations = [migrations.RunPython(gate_pulse_details, migrations.RunPython.noop)]
