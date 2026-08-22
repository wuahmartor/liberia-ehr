from django.db import migrations


SITES = [
    "Radial",
    "Brachial",
    "Femoral",
    "Popliteal",
    "Posterior tibial",
    "Dorsalis pedis (pedal)",
]


def combine_site_and_laterality(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    choices = [f"{side} {site}" for site in SITES for side in ("Left", "Right")]
    Field.objects.filter(flowsheet=nursing, key="peripheral-pulse-site").update(
        label="Abnormal pulse site and laterality",
        choices=choices,
        help_text="Select every abnormal pulse site with its laterality.",
    )
    Field.objects.filter(flowsheet=nursing, key="peripheral-pulse-laterality").update(
        is_active=False,
    )
    Field.objects.filter(flowsheet=nursing, key="peripheral-pulse-grade").update(
        display_order=318,
    )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0015_multiple_pulse_sites_remove_edema_laterality")]
    operations = [migrations.RunPython(combine_site_and_laterality, migrations.RunPython.noop)]
