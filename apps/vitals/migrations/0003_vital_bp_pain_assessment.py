from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vitals", "0002_vital_fahrenheit_pulse_assessment"),
    ]

    operations = [
        migrations.AddField(
            model_name="vitalobservation",
            name="blood_pressure_location",
            field=models.CharField(
                blank=True,
                choices=[
                    ("left_arm", "Left arm"),
                    ("right_arm", "Right arm"),
                    ("left_thigh", "Left thigh"),
                    ("right_thigh", "Right thigh"),
                    ("other", "Other"),
                    ("not_recorded", "Not recorded"),
                ],
                default="not_recorded",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="pain_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("yes", "Yes"),
                    ("no", "No / denies pain"),
                    ("not_assessed", "Not assessed"),
                ],
                default="not_assessed",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="pain_location",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="vitalobservation",
            name="pain_characteristics",
            field=models.TextField(blank=True),
        ),
    ]
