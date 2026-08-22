from django.db import migrations


LOCATIONS = [
    ("face", "Face"), ("sacral", "Sacral"),
    ("left-arm", "Left arm"), ("right-arm", "Right arm"),
    ("left-hand", "Left hand"), ("right-hand", "Right hand"),
    ("left-leg", "Left leg"), ("right-leg", "Right leg"),
    ("left-ankle", "Left ankle"), ("right-ankle", "Right ankle"),
    ("left-foot", "Left foot"), ("right-foot", "Right foot"),
    ("generalized", "Generalized"),
]

GRADES = ["Non-pitting", "1+", "2+", "3+", "4+", "Unable to assess"]


def grade_each_location(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return

    Field.objects.filter(flowsheet=nursing, key="edema-grade").update(is_active=False)
    for order, (slug, location) in enumerate(LOCATIONS, start=340):
        Field.objects.update_or_create(
            flowsheet=nursing,
            key=f"edema-grade-{slug}",
            defaults={
                "label": f"{location} edema grade",
                "data_type": "choice",
                "choices": GRADES,
                "section": "Cardiovascular",
                "subsection": f"{location} edema",
                "show_when_field_key": "edema-location",
                "show_when_value": location,
                "display_order": order,
                "is_required": False,
                "is_active": True,
                "help_text": "Grade edema at this selected location independently.",
            },
        )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0018_fix_pulse_grade_visibility")]
    operations = [migrations.RunPython(grade_each_location, migrations.RunPython.noop)]
