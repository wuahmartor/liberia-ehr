from django.db import migrations


SITES = [
    ("left-radial", "Left radial"), ("right-radial", "Right radial"),
    ("left-brachial", "Left brachial"), ("right-brachial", "Right brachial"),
    ("left-femoral", "Left femoral"), ("right-femoral", "Right femoral"),
    ("left-popliteal", "Left popliteal"), ("right-popliteal", "Right popliteal"),
    ("left-posterior-tibial", "Left posterior tibial"),
    ("right-posterior-tibial", "Right posterior tibial"),
    ("left-dorsalis-pedis", "Left dorsalis pedis (pedal)"),
    ("right-dorsalis-pedis", "Right dorsalis pedis (pedal)"),
]

GRADES = [
    "0 — Absent", "1+ — Weak", "2+ — Normal", "3+ — Increased",
    "4+ — Bounding", "Doppler only", "Unable to assess",
]


def grade_each_site(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    Field.objects.filter(flowsheet=nursing, key="peripheral-pulse-grade").update(is_active=False)
    for order, (slug, label) in enumerate(SITES, start=318):
        Field.objects.update_or_create(
            flowsheet=nursing,
            key=f"pulse-grade-{slug}",
            defaults={
                "label": f"{label} grade",
                "data_type": "choice",
                "choices": GRADES,
                "section": "Cardiovascular",
                "subsection": f"{label} pulse",
                "show_when_field_key": "peripheral-pulse-site",
                "show_when_value": label,
                "display_order": order,
                "is_required": False,
                "is_active": True,
                "help_text": "Grade this selected pulse site independently.",
            },
        )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0016_combine_pulse_site_laterality")]
    operations = [migrations.RunPython(grade_each_site, migrations.RunPython.noop)]
