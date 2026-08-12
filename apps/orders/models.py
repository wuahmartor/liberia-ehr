from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class MedicationOrder(models.Model):

    class OrderMethod(models.TextChoices):
        ELECTRONIC = "electronic", "Electronic"
        WRITTEN = "written", "Written"
        VERBAL = "verbal", "Verbal"
        TELEPHONE = "telephone", "Telephone"

    class OrderType(models.TextChoices):
        NEW = "new", "New therapy"
        CONTINUATION = "continuation", "Continuation"
        RENEWAL = "renewal", "Renewal"
        DOSE_CHANGE = "dose_change", "Dose or frequency change"
        FORMULARY_SUBSTITUTION = "formulary_substitution", "Formulary substitution"
        DISCHARGE = "discharge", "Discharge medication"

    # ========================================================
    # STATUS
    # ========================================================

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        DISCONTINUED = "discontinued", "Discontinued"
        COMPLETED = "completed", "Completed"


    # ========================================================
    # DOSE UNITS
    # ========================================================

    class DoseUnit(models.TextChoices):
        MCG = "mcg", "mcg"
        MG = "mg", "mg"
        G = "g", "g"
        KG = "kg", "kg"

        ML = "mL", "mL"
        L = "L", "L"

        UNIT = "unit", "unit"
        UNITS = "units", "units"

        TABLET = "tablet", "tablet"
        TABLETS = "tablets", "tablets"

        CAPSULE = "capsule", "capsule"
        CAPSULES = "capsules", "capsules"

        DROP = "drop", "drop"
        DROPS = "drops", "drops"

        PUFF = "puff", "puff"
        PUFFS = "puffs", "puffs"

        SPRAY = "spray", "spray"
        SPRAYS = "sprays", "sprays"

        PATCH = "patch", "patch"
        PATCHES = "patches", "patches"

        SUPPOSITORY = "suppository", "suppository"

        VIAL = "vial", "vial"
        AMPULE = "ampule", "ampule"

        APPLICATION = "application", "application"

        OTHER = "other", "Other"


    # ========================================================
    # ROUTES
    # ========================================================

    class Route(models.TextChoices):
        ORAL = "oral", "Oral"

        IV = "intravenous", "Intravenous (IV)"
        IM = "intramuscular", "Intramuscular (IM)"
        SC = "subcutaneous", "Subcutaneous (SC)"

        SL = "sublingual", "Sublingual"
        BUCCAL = "buccal", "Buccal"

        TOPICAL = "topical", "Topical"
        TRANSDERMAL = "transdermal", "Transdermal"

        INHALATION = "inhalation", "Inhalation"

        NASAL = "nasal", "Nasal"

        OPHTHALMIC = "ophthalmic", "Ophthalmic"
        OTIC = "otic", "Otic"

        RECTAL = "rectal", "Rectal"
        VAGINAL = "vaginal", "Vaginal"

        INTRADERMAL = "intradermal", "Intradermal"

        ENTERAL = "enteral", "Enteral / Feeding Tube"

        OTHER = "other", "Other"


    # ========================================================
    # FREQUENCY
    # ========================================================

    class Frequency(models.TextChoices):
        ONCE = "once", "Once"

        DAILY = "daily", "Daily"
        BID = "bid", "Twice daily (BID)"
        TID = "tid", "Three times daily (TID)"
        QID = "qid", "Four times daily (QID)"

        Q4H = "q4h", "Every 4 hours"
        Q6H = "q6h", "Every 6 hours"
        Q8H = "q8h", "Every 8 hours"
        Q12H = "q12h", "Every 12 hours"
        Q24H = "q24h", "Every 24 hours"

        QAM = "qam", "Every morning"
        QPM = "qpm", "Every evening"
        QHS = "qhs", "At bedtime"

        AC = "ac", "Before meals"
        PC = "pc", "After meals"

        AC_HS = (
            "ac_hs",
            "Before meals and at bedtime",
        )

        WEEKLY = "weekly", "Weekly"

        PRN = "prn", "As needed (PRN)"

        STAT = "stat", "STAT"

        OTHER = "other", "Other"


    # ========================================================
    # IDENTITY
    # ========================================================

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )


    # ========================================================
    # PATIENT / ENCOUNTER
    # ========================================================

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )


    # ========================================================
    # MEDICATION
    # ========================================================

    medication = models.ForeignKey(
        "pharmacy.Medication",
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )


    # ========================================================
    # DOSING
    # ========================================================

    dose = models.CharField(
        max_length=50,
        help_text="Enter the ordered dose amount.",
    )

    dose_unit = models.CharField(
        max_length=30,
        choices=DoseUnit.choices,
        blank=True,
        default="",
    )

    route = models.CharField(
        max_length=30,
        choices=Route.choices,
    )

    frequency = models.CharField(
        max_length=30,
        choices=Frequency.choices,
    )


    # ========================================================
    # QUANTITY
    # ========================================================

    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        null=True,
        blank=True,
    )


    # ========================================================
    # ORDER TIMING
    # ========================================================

    start_datetime = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Date and time when the medication order "
            "should begin."
        ),
    )

    stop_date = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Date when the medication order should stop."
        ),
    )


    # ========================================================
    # INSTRUCTIONS
    # ========================================================

    instructions = models.TextField(
        blank=True,
    )


    # ========================================================
    # STATUS
    # ========================================================

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )

    order_method = models.CharField(
        max_length=20,
        choices=OrderMethod.choices,
        default=OrderMethod.ELECTRONIC,
    )

    order_type = models.CharField(
        max_length=30,
        choices=OrderType.choices,
        default=OrderType.NEW,
        db_index=True,
    )

    clinical_indication = models.CharField(
        max_length=300,
        default="",
        help_text="Clinical reason or indication for this medication order.",
    )

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_medication_orders",
        null=True,
        blank=True,
    )

    discontinued_at = models.DateTimeField(null=True, blank=True, db_index=True)
    discontinued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="discontinued_medication_orders",
        null=True,
        blank=True,
    )
    discontinuation_ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="ordered_medication_discontinuations",
        null=True,
        blank=True,
    )
    discontinuation_order_method = models.CharField(
        max_length=20,
        choices=OrderMethod.choices,
        blank=True,
    )
    discontinuation_received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="received_medication_discontinuations",
        null=True,
        blank=True,
    )
    discontinuation_reason = models.TextField(blank=True)


    # ========================================================
    # AUDIT
    # ========================================================

    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="medication_orders",
    )

    ordered_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    # ========================================================
    # META
    # ========================================================

    class Meta:
        ordering = (
            "-ordered_at",
        )

        indexes = [
            models.Index(
                fields=(
                    "encounter",
                    "status",
                ),
                name="order_med_enc_status_idx",
            ),

            models.Index(
                fields=(
                    "patient",
                    "status",
                ),
                name="order_med_patient_status_idx",
            ),
        ]


    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        super().clean()


        if (
            self.encounter_id
            and self.patient_id
            and self.encounter.patient_id
            != self.patient_id
        ):
            raise ValidationError(
                {
                    "encounter": (
                        "The encounter must belong "
                        "to this patient."
                    )
                }
            )


        if (
            self.start_datetime
            and self.stop_date
            and self.stop_date
            < self.start_datetime.date()
        ):
            raise ValidationError(
                {
                    "stop_date": (
                        "Stop date cannot occur before "
                        "the medication start date."
                    )
                }
            )


    # ========================================================
    # DISPLAY
    # ========================================================

    def __str__(self):

        return (
            f"{self.medication.display_name} "
            f"for {self.patient}"
        )
