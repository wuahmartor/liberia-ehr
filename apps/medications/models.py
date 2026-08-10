from __future__ import annotations

import uuid

from django.conf import settings

from django.core.exceptions import ValidationError

from django.db import models

from django.db.models import Q

# ============================================================

# QUERYSET

# ============================================================

class MedicationAdministrationQuerySet(models.QuerySet):

    def for_patient(self, patient):

        return self.filter(patient=patient)

    def for_encounter(self, encounter):

        return self.filter(encounter=encounter)

    def administered(self):

        return self.filter(

            status=MedicationAdministration.Status.ADMINISTERED

        )

    def exceptions(self):

        return self.exclude(

            status=MedicationAdministration.Status.ADMINISTERED

        )

    def recent(self):

        return self.order_by("-administered_at")

# ============================================================

# MEDICATION ADMINISTRATION

# ============================================================

class MedicationAdministration(models.Model):

    """

    Clinical medication administration record.

    This model documents what occurred at the bedside.

    The medication itself originates from the pharmacy formulary,

    but administration should normally be linked to a provider

    MedicationOrder.

    Pharmacy formulary:

        pharmacy.Medication

    Provider order:

        orders.MedicationOrder

    Bedside administration:

        medications.MedicationAdministration

    """

    class Status(models.TextChoices):

        ADMINISTERED = (

            "administered",

            "Administered",

        )

        HELD = (

            "held",

            "Held",

        )

        REFUSED = (

            "refused",

            "Refused",

        )

        NOT_GIVEN = (

            "not_given",

            "Not Given",

        )

        OMITTED = (

            "omitted",

            "Omitted",

        )

    # ========================================================

    # IDENTITY

    # ========================================================

    id = models.UUIDField(

        primary_key=True,

        default=uuid.uuid4,

        editable=False,

    )

    # ========================================================

    # ORDER

    # ========================================================

    medication_order = models.ForeignKey(

        "orders.MedicationOrder",

        on_delete=models.PROTECT,

        related_name="administrations",

        null=True,

        blank=True,

        help_text=(

            "Medication order associated with this administration. "

            "New routine administrations should normally have an order."

        ),

    )

    # ========================================================

    # PATIENT / ENCOUNTER

    # ========================================================

    patient = models.ForeignKey(

        "patients.Patient",

        on_delete=models.PROTECT,

        related_name="medication_administrations",

    )

    encounter = models.ForeignKey(

        "encounters.Encounter",

        on_delete=models.PROTECT,

        related_name="medication_administrations",

    )

    # ========================================================

    # FORMULARY MEDICATION

    # ========================================================

    medication = models.ForeignKey(

        "pharmacy.Medication",

        on_delete=models.PROTECT,

        related_name="administrations",

    )

    # ========================================================

    # ADMINISTRATION DETAILS

    # ========================================================

    dose_administered = models.CharField(

        max_length=100,

        blank=True,

        help_text=(

            "Actual administered dose, for example 500 mg or 10 mL."

        ),

    )

    route = models.CharField(

        max_length=100,

        blank=True,

        help_text=(

            "Actual route used for this administration."

        ),

    )

    administration_site = models.CharField(

        max_length=100,

        blank=True,

        help_text=(

            "Optional site, for example left deltoid or right abdomen."

        ),

    )

    status = models.CharField(

        max_length=20,

        choices=Status.choices,

        default=Status.ADMINISTERED,

        db_index=True,

    )

    # ========================================================

    # TIME

    # ========================================================

    scheduled_at = models.DateTimeField(

        null=True,

        blank=True,

        db_index=True,

        help_text=(

            "Scheduled administration time when available."

        ),

    )

    administered_at = models.DateTimeField(

        db_index=True,

        help_text=(

            "Time the medication was administered or the administration "

            "event was documented as held/refused/not given."

        ),

    )

    # ========================================================

    # EXCEPTION / CLINICAL DOCUMENTATION

    # ========================================================

    reason = models.TextField(

        blank=True,

        help_text=(

            "Required when a medication is held, refused, omitted, "

            "or otherwise not administered."

        ),

    )

    notes = models.TextField(

        blank=True,

        help_text=(

            "Additional administration documentation."

        ),

    )

    # ========================================================

    # CLINICIAN

    # ========================================================

    administered_by = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,

        related_name="medication_administrations",

    )

    witnessed_by = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,

        related_name="witnessed_medication_administrations",

        null=True,

        blank=True,

        help_text=(

            "Optional second clinician witness when required by policy."

        ),

    )

    # ========================================================

    # AUDIT

    # ========================================================

    created_at = models.DateTimeField(

        auto_now_add=True,

    )

    updated_at = models.DateTimeField(

        auto_now=True,

    )

    objects = MedicationAdministrationQuerySet.as_manager()

    # ========================================================

    # META

    # ========================================================

    class Meta:

        ordering = (

            "-administered_at",

            "-created_at",

        )

        verbose_name = "Medication Administration"

        verbose_name_plural = "Medication Administrations"

        indexes = [

            models.Index(

                fields=(

                    "encounter",

                    "administered_at",

                ),

                name="med_admin_enc_time_idx",

            ),

            models.Index(

                fields=(

                    "patient",

                    "status",

                ),

                name="med_admin_patient_status_idx",

            ),

            models.Index(

                fields=(

                    "medication",

                    "administered_at",

                ),

                name="med_admin_med_time_idx",

            ),

            models.Index(

                fields=(

                    "status",

                    "scheduled_at",

                ),

                name="med_admin_status_sched_idx",

            ),

        ]

        constraints = [

            models.CheckConstraint(

                condition=(

                    Q(status="administered")

                    | ~Q(reason="")

                ),

                name="med_admin_reason_if_not_given",

            ),

        ]

    # ========================================================

    # VALIDATION

    # ========================================================

    def clean(self):

        super().clean()

        errors = {}

        # ----------------------------------------------------

        # ENCOUNTER MUST BELONG TO PATIENT

        # ----------------------------------------------------

        if self.encounter_id and self.patient_id:

            if self.encounter.patient_id != self.patient_id:

                errors["encounter"] = (

                    "The selected encounter does not belong to this patient."

                )

        # ----------------------------------------------------

        # MEDICATION ORDER VALIDATION

        # ----------------------------------------------------

        if self.medication_order_id:

            order = self.medication_order

            if self.patient_id and order.patient_id != self.patient_id:

                errors["medication_order"] = (

                    "The medication order does not belong to this patient."

                )

            if (

                self.encounter_id

                and order.encounter_id != self.encounter_id

            ):

                errors["medication_order"] = (

                    "The medication order does not belong to this encounter."

                )

            if (

                self.medication_id

                and order.medication_id != self.medication_id

            ):

                errors["medication"] = (

                    "The administered medication must match "

                    "the medication order."

                )

        # ----------------------------------------------------

        # ADMINISTERED MEDICATION

        # ----------------------------------------------------

        if self.status == self.Status.ADMINISTERED:

            if not self.dose_administered.strip():

                errors["dose_administered"] = (

                    "Enter the actual dose administered."

                )

            if not self.route.strip():

                errors["route"] = (

                    "Enter the actual administration route."

                )

        # ----------------------------------------------------

        # NON-ADMINISTRATION REASON

        # ----------------------------------------------------

        if self.status != self.Status.ADMINISTERED:

            if not self.reason.strip():

                errors["reason"] = (

                    "Document why the medication was not administered."

                )

        if (

            self.witnessed_by_id

            and self.administered_by_id

            and self.witnessed_by_id == self.administered_by_id

        ):

            errors["witnessed_by"] = (

                "The witness must be a different clinician."

            )

        if errors:

            raise ValidationError(errors)

    # ========================================================

    # STRING

    # ========================================================

    def __str__(self) -> str:

        return (

            f"{self.medication.display_name} — "

            f"{self.get_status_display()} — "

            f"{self.patient}"

        )