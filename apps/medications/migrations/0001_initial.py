import django.db.models.deletion
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("encounters", "0003_encounter_cancelled_at_encounter_check_in_user_and_more"),
        ("pharmacy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicationAdministration",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("dose_administered", models.CharField(max_length=100)),
                ("route", models.CharField(max_length=100)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("administered", "Administered"),
                            ("held", "Held"),
                            ("refused", "Refused"),
                        ],
                        db_index=True,
                        default="administered",
                        max_length=20,
                    ),
                ),
                ("reason", models.TextField(blank=True)),
                ("administered_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "administered_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_administrations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "encounter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_administrations",
                        to="encounters.encounter",
                    ),
                ),
                (
                    "medication",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="administrations",
                        to="pharmacy.medication",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_administrations",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "ordering": ("-administered_at",),
            },
        ),
        migrations.AddIndex(
            model_name="medicationadministration",
            index=models.Index(
                fields=["encounter", "administered_at"],
                name="med_admin_enc_time_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="medicationadministration",
            index=models.Index(
                fields=["patient", "status"],
                name="med_admin_patient_status_idx",
            ),
        ),
    ]
