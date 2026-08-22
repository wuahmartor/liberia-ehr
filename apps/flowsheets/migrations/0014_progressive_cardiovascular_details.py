from django.db import migrations


def progressive_details(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    Field.objects.filter(flowsheet=nursing, key__startswith="pulse-").update(is_active=False)
    definitions = [
        ("peripheral-pulse-site", "Abnormal pulse site", ["Radial", "Brachial", "Femoral", "Popliteal", "Posterior tibial", "Dorsalis pedis (pedal)"], "Peripheral pulse selection", "peripheral-pulses", "Abnormal", 317),
        ("peripheral-pulse-laterality", "Pulse laterality", ["Left", "Right", "Bilateral"], "Selected pulse details", "peripheral-pulse-site", "*", 318),
        ("peripheral-pulse-grade", "Pulse grade", ["0 — Absent", "1+ — Weak", "2+ — Normal", "3+ — Increased", "4+ — Bounding", "Doppler only", "Unable to assess"], "Selected pulse details", "peripheral-pulse-site", "*", 319),
    ]
    for key, label, choices, subsection, controller, trigger, order in definitions:
        Field.objects.update_or_create(
            flowsheet=nursing, key=key,
            defaults={"label": label, "data_type": "choice", "choices": choices,
                      "section": "Cardiovascular", "subsection": subsection,
                      "show_when_field_key": controller, "show_when_value": trigger,
                      "display_order": order, "is_required": False, "is_active": True,
                      "help_text": "Document only the abnormal pulse being assessed."},
        )

    for key, label, order in (
        ("edema-location", "Edema location", 324),
        ("edema-laterality", "Edema laterality", 325),
        ("edema-grade", "Edema grade", 326),
    ):
        Field.objects.filter(flowsheet=nursing, key=key).update(
            label=label, subsection="Edema details", show_when_field_key="edema",
            show_when_value="Present", display_order=order, is_required=False, is_active=True,
        )
    Field.objects.filter(flowsheet=nursing, key="edema").update(display_order=323)


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0013_gate_peripheral_pulse_details")]
    operations = [migrations.RunPython(progressive_details, migrations.RunPython.noop)]
