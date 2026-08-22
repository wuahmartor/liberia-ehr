from django.db import migrations


FIELD_LAYOUT = {
    "gcs-interfering-factors": ("Glasgow Coma Scale", 100),
    "gcs-eye": ("Glasgow Coma Scale", 110),
    "gcs-verbal": ("Glasgow Coma Scale", 120),
    "gcs-motor": ("Glasgow Coma Scale", 130),
    "gcs-total": ("Glasgow Coma Scale", 140),
    "left-pupil-size": ("Pupil assessment", 200),
    "left-pupil-reactivity": ("Pupil assessment", 210),
    "right-pupil-size": ("Pupil assessment", 220),
    "right-pupil-reactivity": ("Pupil assessment", 230),
    "lue-motor-strength": ("Motor response", 300),
    "rue-motor-strength": ("Motor response", 310),
    "lle-motor-strength": ("Motor response", 320),
    "rle-motor-strength": ("Motor response", 330),
    "motor-asymmetry-details": ("Motor response", 340),
    "lue-sensation": ("Sensory response", 400),
    "rue-sensation": ("Sensory response", 410),
    "lle-sensation": ("Sensory response", 420),
    "rle-sensation": ("Sensory response", 430),
    "speech": ("Speech and communication", 500),
}


def order_neurological_rows(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    neurological = Definition.objects.filter(slug="neurological-checks").first()
    if not neurological:
        return
    neurological.description = (
        "Structured neurological assessment with complete Glasgow Coma Scale, "
        "bilateral pupils, and separately documented LUE, RUE, LLE and RLE findings."
    )
    neurological.save(update_fields=["description"])
    for key, (section, order) in FIELD_LAYOUT.items():
        Field.objects.filter(flowsheet=neurological, key=key).update(
            section=section,
            subsection="",
            display_order=order,
        )
    # Superseded summary rows remain available for historical records but are
    # placed after the structured bilateral assessment.
    Field.objects.filter(flowsheet=neurological, key="pupils").update(
        label="Legacy pupil summary", section="Legacy summary fields", display_order=900
    )
    Field.objects.filter(flowsheet=neurological, key="left-grip").update(
        label="Legacy left grip summary", section="Legacy summary fields", display_order=910
    )
    Field.objects.filter(flowsheet=neurological, key="right-grip").update(
        label="Legacy right grip summary", section="Legacy summary fields", display_order=920
    )


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0008_expand_neurological_assessment")]
    operations = [migrations.RunPython(order_neurological_rows, migrations.RunPython.noop)]
