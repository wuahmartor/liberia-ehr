from django.db import migrations


SITES = [
    ("left-radial", "Left Radial"), ("right-radial", "Right Radial"),
    ("left-brachial", "Left Brachial"), ("right-brachial", "Right Brachial"),
    ("left-femoral", "Left Femoral"), ("right-femoral", "Right Femoral"),
    ("left-popliteal", "Left Popliteal"), ("right-popliteal", "Right Popliteal"),
    ("left-posterior-tibial", "Left Posterior tibial"),
    ("right-posterior-tibial", "Right Posterior tibial"),
    ("left-dorsalis-pedis", "Left Dorsalis pedis (pedal)"),
    ("right-dorsalis-pedis", "Right Dorsalis pedis (pedal)"),
]


def fix_visibility(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return
    for slug, selected_value in SITES:
        Field.objects.filter(flowsheet=nursing, key=f"pulse-grade-{slug}").update(
            label=f"{selected_value} grade",
            subsection=f"{selected_value} pulse",
            show_when_value=selected_value,
        )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0017_grade_each_selected_pulse_site")]
    operations = [migrations.RunPython(fix_visibility, migrations.RunPython.noop)]
