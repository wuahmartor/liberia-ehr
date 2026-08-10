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
            name="MedicationOrder",
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
                ("dose", models.CharField(max_length=100)),
                ("route", models.CharField(max_length=100)),
                ("frequency", models.CharField(max_length=100)),
                (
                    "quantity",
                    models.DecimalField(
                        blank=True,
                        decimal_places=3,
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("instructions", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("on_hold", "On hold"),
                            ("discontinued", "Discontinued"),
                            ("completed", "Completed"),
                        ],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                ("ordered_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "encounter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_orders",
                        to="encounters.encounter",
                    ),
                ),
                (
                    "medication",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_orders",
                        to="pharmacy.medication",
                    ),
                ),
                (
                    "ordered_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_orders",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="medication_orders",
                        to="patients.patient",
                    ),
                ),
            ],
            options={
                "ordering": ("-ordered_at",),
            },
        ),
        migrations.AddIndex(
            model_name="medicationorder",
            index=models.Index(
                fields=["encounter", "status"],
                name="order_med_enc_status_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="medicationorder",
            index=models.Index(
                fields=["patient", "status"],
                name="order_med_patient_status_idx",
            ),
        ),
    ]
