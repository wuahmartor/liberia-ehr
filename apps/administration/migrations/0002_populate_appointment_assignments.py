from django.conf import settings
from django.db import migrations


def populate_appointment_assignments(apps, schema_editor):
    """
    Populate missing provider, department, and clinical-unit values
    on existing Appointment records.

    Provider fallback:
    - Prefer an active physician or nurse practitioner.
    - Otherwise use any active clinical staff member.
    - Otherwise use an active staff or superuser account.

    Department and clinical-unit fallback:
    - Prefer records belonging to the appointment facility.
    - Prefer the department attached to the selected clinical unit.
    """

    Appointment = apps.get_model(
        "administration",
        "Appointment",
    )

    UserProfile = apps.get_model(
        "accounts",
        "UserProfile",
    )

    Department = apps.get_model(
        "facilities",
        "Department",
    )

    ClinicalUnit = apps.get_model(
        "facilities",
        "ClinicalUnit",
    )

    user_app_label, user_model_name = (
        settings.AUTH_USER_MODEL.split(".")
    )

    User = apps.get_model(
        user_app_label,
        user_model_name,
    )

    # ========================================================
    # FIND A DEFAULT PROVIDER
    # ========================================================
    provider_profile = (
        UserProfile.objects
        .filter(
            role__in=[
                "physician",
                "nurse_practitioner",
            ],
            is_active_staff=True,
            user__is_active=True,
        )
        .order_by(
            "user__last_name",
            "user__first_name",
            "user_id",
        )
        .first()
    )

    if provider_profile is None:
        provider_profile = (
            UserProfile.objects
            .filter(
                is_clinical_staff=True,
                is_active_staff=True,
                user__is_active=True,
            )
            .order_by(
                "user__last_name",
                "user__first_name",
                "user_id",
            )
            .first()
        )

    if provider_profile is not None:
        default_provider = User.objects.filter(
            pk=provider_profile.user_id,
        ).first()
    else:
        default_provider = (
            User.objects
            .filter(
                is_active=True,
                is_staff=True,
            )
            .order_by(
                "-is_superuser",
                "last_name",
                "first_name",
                "pk",
            )
            .first()
        )

    if default_provider is None:
        raise RuntimeError(
            "Cannot populate Appointment.provider because no active "
            "physician, nurse practitioner, clinical staff member, "
            "staff user, or superuser exists."
        )

    # ========================================================
    # POPULATE EXISTING APPOINTMENTS
    # ========================================================
    appointments = Appointment.objects.filter(
        provider__isnull=True,
    ) | Appointment.objects.filter(
        department__isnull=True,
    ) | Appointment.objects.filter(
        clinical_unit__isnull=True,
    )

    appointments = appointments.distinct()

    for appointment in appointments:
        department = None
        clinical_unit = None

        # Prefer the appointment's facility.
        if appointment.facility_id:
            clinical_unit = (
                ClinicalUnit.objects
                .filter(
                    facility_id=appointment.facility_id,
                    is_active=True,
                )
                .order_by("name", "pk")
                .first()
            )

            department = (
                Department.objects
                .filter(
                    facility_id=appointment.facility_id,
                    is_active=True,
                )
                .order_by("name", "pk")
                .first()
            )

        # Prefer the department attached to the selected unit.
        if (
            clinical_unit is not None
            and clinical_unit.department_id
        ):
            department = Department.objects.filter(
                pk=clinical_unit.department_id,
            ).first()

        # Fall back to any active clinical unit.
        if clinical_unit is None:
            clinical_unit = (
                ClinicalUnit.objects
                .filter(is_active=True)
                .order_by("name", "pk")
                .first()
            )

        # Use the fallback unit's department where available.
        if (
            clinical_unit is not None
            and clinical_unit.department_id
        ):
            department = Department.objects.filter(
                pk=clinical_unit.department_id,
            ).first()

        # Final department fallback.
        if department is None:
            department = (
                Department.objects
                .filter(is_active=True)
                .order_by("name", "pk")
                .first()
            )

        if department is None:
            raise RuntimeError(
                "Cannot populate Appointment.department because "
                "no active Department exists."
            )

        if clinical_unit is None:
            raise RuntimeError(
                "Cannot populate Appointment.clinical_unit because "
                "no active ClinicalUnit exists."
            )

        update_fields = []

        if appointment.provider_id is None:
            appointment.provider_id = default_provider.pk
            update_fields.append("provider")

        if appointment.department_id is None:
            appointment.department_id = department.pk
            update_fields.append("department")

        if appointment.clinical_unit_id is None:
            appointment.clinical_unit_id = clinical_unit.pk
            update_fields.append("clinical_unit")

        if update_fields:
            appointment.save(
                update_fields=update_fields,
            )


def reverse_population(apps, schema_editor):
    """
    Preserve populated values if this migration is reversed.
    """

    pass


class Migration(migrations.Migration):

    dependencies = [
        (
            "administration",
            "0001_initial",
        ),
        (
            "accounts",
            "0001_initial",
        ),
        (
            "facilities",
            "0001_initial",
        ),
        migrations.swappable_dependency(
            settings.AUTH_USER_MODEL
        ),
    ]

    operations = [
        migrations.RunPython(
            populate_appointment_assignments,
            reverse_population,
        ),
    ]