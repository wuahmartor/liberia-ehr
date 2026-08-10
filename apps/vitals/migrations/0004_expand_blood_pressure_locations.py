from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("vitals", "0003_vital_bp_pain_assessment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vitalobservation",
            name="blood_pressure_location",
            field=models.CharField(
                blank=True,
                choices=[
                    ("left_upper_arm", "Left upper arm"),
                    ("right_upper_arm", "Right upper arm"),
                    ("left_forearm", "Left forearm"),
                    ("right_forearm", "Right forearm"),
                    ("left_thigh", "Left thigh"),
                    ("right_thigh", "Right thigh"),
                    ("left_calf", "Left calf"),
                    ("right_calf", "Right calf"),
                    ("left_wrist", "Left wrist"),
                    ("right_wrist", "Right wrist"),
                    ("left_ankle", "Left ankle"),
                    ("right_ankle", "Right ankle"),
                    ("other", "Other"),
                    ("not_recorded", "Not recorded"),
                ],
                default="not_recorded",
                max_length=20,
            ),
        ),
    ]
