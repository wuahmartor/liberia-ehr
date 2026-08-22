from django.db import migrations


def retire_redundant_definitions(apps, schema_editor):
    Definition = apps.get_model("flowsheets", "FlowSheetDefinition")
    Definition.objects.filter(
        slug__in=("neurological-checks", "nursing-systems-assessment")
    ).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [("flowsheets", "0019_grade_each_edema_location")]
    operations = [migrations.RunPython(retire_redundant_definitions, migrations.RunPython.noop)]
