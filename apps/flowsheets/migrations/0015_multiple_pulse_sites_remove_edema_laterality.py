from django.db import migrations


def revise_cardiovascular(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Field = apps.get_model("flowsheets", "FlowSheetFieldDefinition")
    nursing = Definition.objects.filter(slug="nursing-systems-assessment").first()
    if not nursing:
        return
    Field.objects.filter(flowsheet=nursing, key="peripheral-pulse-site").update(
        data_type="multi_choice",
        help_text="Select every abnormal pulse site assessed.",
    )
    Field.objects.filter(flowsheet=nursing, key="edema-laterality").update(is_active=False)
    Field.objects.filter(flowsheet=nursing, key="edema-grade").update(display_order=325)


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0014_progressive_cardiovascular_details")]
    operations = [migrations.RunPython(revise_cardiovascular, migrations.RunPython.noop)]
