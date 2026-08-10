from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models
import django.core.validators


def populate_fahrenheit(apps, schema_editor):
    VitalObservation = apps.get_model("vitals", "VitalObservation")
    for observation in VitalObservation.objects.filter(
        temperature_celsius__isnull=False,
        temperature_fahrenheit__isnull=True,
    ).iterator():
        observation.temperature_fahrenheit = (
            observation.temperature_celsius * Decimal("9") / Decimal("5")
            + Decimal("32")
        ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        observation.save(update_fields=["temperature_fahrenheit"])


class Migration(migrations.Migration):
    dependencies = [
        ("vitals", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="vitalobservation",
            name="temperature_fahrenheit",
            field=models.DecimalField(
                blank=True,
                decimal_places=1,
                help_text="Canonical stored temperature in degrees Fahrenheit.",
                max_digits=5,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(Decimal("77.0")),
                    django.core.validators.MaxValueValidator(Decimal("113.0")),
                ],
            ),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="heart_rhythm",
            field=models.CharField(
                blank=True,
                choices=[
                    ("regular", "Regular"),
                    ("irregular", "Irregular"),
                    ("irregularly_irregular", "Irregularly irregular"),
                    ("not_assessed", "Not assessed"),
                ],
                default="not_assessed",
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="heart_rate_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("radial", "Radial pulse"),
                    ("apical", "Apical"),
                    ("monitor", "Cardiac monitor"),
                    ("pulse_oximeter", "Pulse oximeter"),
                    ("other", "Other"),
                    ("not_recorded", "Not recorded"),
                ],
                default="not_recorded",
                max_length=30,
            ),
        ),
        migrations.RunPython(populate_fahrenheit, migrations.RunPython.noop),
    ]
