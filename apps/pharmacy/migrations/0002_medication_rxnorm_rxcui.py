from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="medication",
            name="rxnorm_rxcui",
            field=models.CharField(
                blank=True,
                help_text="RxNorm concept identifier for US drug directory imports.",
                max_length=20,
                null=True,
                unique=True,
            ),
        ),
    ]
