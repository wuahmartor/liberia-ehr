

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


phone_validator = RegexValidator(
    regex=r"^\+?[0-9()\-\s]{7,25}$",
    message=(
        "Enter a valid phone number using digits and optional spaces, "
        "parentheses, hyphens, or a leading +."
    ),
)


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UserTrackedModel(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_updated",
        null=True,
        blank=True,
    )

    class Meta:
        abstract = True


class PatientQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            is_active=True,
            record_status=Patient.RecordStatus.ACTIVE,
            is_deceased=False,
        )

    def inactive(self):
        return self.filter(
            Q(is_active=False)
            | Q(record_status=Patient.RecordStatus.INACTIVE)
        )

    def deceased(self):
        return self.filter(is_deceased=True)

    def merged(self):
        return self.filter(record_status=Patient.RecordStatus.MERGED)

    def entered_in_error(self):
        return self.filter(
            record_status=Patient.RecordStatus.ENTERED_IN_ERROR
        )

    def search(self, query: str):
        query = (query or "").strip()

        if not query:
            return self.none()

        return self.filter(
            Q(mrn__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(previous_last_name__icontains=query)
            | Q(preferred_name__icontains=query)
            | Q(aliases__first_name__icontains=query)
            | Q(aliases__middle_name__icontains=query)
            | Q(aliases__last_name__icontains=query)
            | Q(identifiers__value__icontains=query)
            | Q(contact_points__value__icontains=query)
        ).distinct()


class Patient(UserTrackedModel):
    class RecordStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        MERGED = "merged", "Merged"
        ENTERED_IN_ERROR = "error", "Entered in error"

    class SexAtBirth(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        INTERSEX = "intersex", "Intersex"
        UNKNOWN = "unknown", "Unknown"
        NOT_RECORDED = "not_recorded", "Not recorded"

    class GenderIdentity(models.TextChoices):
        WOMAN = "woman", "Woman"
        MAN = "man", "Man"
        NON_BINARY = "non_binary", "Non-binary"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"
        NOT_DISCLOSED = "not_disclosed", "Not disclosed"

    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        DIVORCED = "divorced", "Divorced"
        SEPARATED = "separated", "Separated"
        WIDOWED = "widowed", "Widowed"
        OTHER = "other", "Other"
        UNKNOWN = "unknown", "Unknown"

    class BloodType(models.TextChoices):
        A_POSITIVE = "A+", "A+"
        A_NEGATIVE = "A-", "A-"
        B_POSITIVE = "B+", "B+"
        B_NEGATIVE = "B-", "B-"
        AB_POSITIVE = "AB+", "AB+"
        AB_NEGATIVE = "AB-", "AB-"
        O_POSITIVE = "O+", "O+"
        O_NEGATIVE = "O-", "O-"
        UNKNOWN = "unknown", "Unknown"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    mrn = models.CharField(
        "medical record number",
        max_length=30,
        unique=True,
        db_index=True,
    )

    prefix = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=100, db_index=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, db_index=True)
    previous_last_name = models.CharField(max_length=100, blank=True)
    preferred_name = models.CharField(max_length=100, blank=True)
    suffix = models.CharField(max_length=20, blank=True)

    date_of_birth = models.DateField(db_index=True)
    date_of_birth_estimated = models.BooleanField(default=False)
    sex_at_birth = models.CharField(
        max_length=20,
        choices=SexAtBirth.choices,
        default=SexAtBirth.NOT_RECORDED,
        db_index=True,
    )
    gender_identity = models.CharField(
        max_length=20,
        choices=GenderIdentity.choices,
        blank=True,
    )
    gender_identity_description = models.CharField(max_length=100, blank=True)
    marital_status = models.CharField(
        max_length=20,
        choices=MaritalStatus.choices,
        blank=True,
    )
    blood_type = models.CharField(
        max_length=10,
        choices=BloodType.choices,
        default=BloodType.UNKNOWN,
        blank=True,
    )

    nationality = models.CharField(max_length=100, blank=True)
    preferred_language = models.CharField(
        max_length=100,
        default="English",
        blank=True,
    )
    interpreter_required = models.BooleanField(default=False)
    occupation = models.CharField(max_length=150, blank=True)
    employer = models.CharField(max_length=150, blank=True)
    education_level = models.CharField(max_length=100, blank=True)
    religion = models.CharField(max_length=100, blank=True)

    registration_facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="registered_patients",
        null=True,
        blank=True,
    )

    record_status = models.CharField(
        max_length=20,
        choices=RecordStatus.choices,
        default=RecordStatus.ACTIVE,
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_deceased = models.BooleanField(default=False, db_index=True)
    deceased_at = models.DateTimeField(null=True, blank=True)
    deceased_status_verified = models.BooleanField(default=False)

    confidential_record = models.BooleanField(default=False)
    restricted_access_reason = models.TextField(blank=True)
    registration_notes = models.TextField(blank=True)

    objects = PatientQuerySet.as_manager()

    class Meta:
        ordering = ("last_name", "first_name", "date_of_birth")
        indexes = [
            models.Index(
                fields=("last_name", "first_name"),
                name="patient_name_idx",
            ),
            models.Index(
                fields=("date_of_birth", "sex_at_birth"),
                name="patient_dob_sex_idx",
            ),
            models.Index(
                fields=("record_status", "is_active"),
                name="patient_status_idx",
            ),
            models.Index(
                fields=("registration_facility", "is_active"),
                name="patient_facility_idx",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.mrn})"

    @property
    def full_name(self):
        parts = (
            self.prefix,
            self.first_name,
            self.middle_name,
            self.last_name,
            self.suffix,
        )
        return " ".join(part.strip() for part in parts if part and part.strip())

    @property
    def display_name(self):
        if self.preferred_name:
            return f"{self.preferred_name} {self.last_name}".strip()
        return self.full_name

    @property
    def initials(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper()

    @property
    def age(self):
        today = timezone.localdate()
        years = today.year - self.date_of_birth.year
        before_birthday = (today.month, today.day) < (
            self.date_of_birth.month,
            self.date_of_birth.day,
        )
        return years - int(before_birthday)

    @property
    def primary_phone(self):
        contact = (
            self.contact_points.filter(
                contact_type=PatientContactPoint.ContactType.PHONE,
                is_active=True,
            )
            .order_by("-is_primary", "sort_order")
            .first()
        )
        return contact.value if contact else ""

    @property
    def primary_email(self):
        contact = (
            self.contact_points.filter(
                contact_type=PatientContactPoint.ContactType.EMAIL,
                is_active=True,
            )
            .order_by("-is_primary", "sort_order")
            .first()
        )
        return contact.value if contact else ""

    def get_full_name(self):
        return self.full_name


    def get_short_name(self):
        return self.preferred_name or self.first_name


    @property
    def age_display(self):
        if self.date_of_birth_estimated:
            return f"Approximately {self.age}"
        return str(self.age)


    @property
    def primary_emergency_contact(self):
        return (
            self.emergency_contacts.filter(is_active=True)
            .order_by("-is_primary", "-is_next_of_kin", "full_name")
            .first()
        )


    @property
    def active_flags(self):
        now = timezone.now()

        return self.flags.filter(
            is_active=True,
            starts_at__lte=now,
        ).filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        )



    @property
    def primary_address(self):
        return (
            self.addresses.filter(is_active=True)
            .order_by("-is_primary", "created_at")
            .first()
        )

    def clean(self):
        errors = {}
        today = timezone.localdate()

        if self.date_of_birth and self.date_of_birth > today:
            errors["date_of_birth"] = (
                "Date of birth cannot be in the future."
            )

        if self.deceased_at and self.date_of_birth:
            if self.deceased_at.date() < self.date_of_birth:
                errors["deceased_at"] = (
                    "The deceased date cannot be before the date of birth."
                )

        if self.is_deceased and not self.deceased_at:
            errors["deceased_at"] = (
                "A deceased date is required when the patient is deceased."
            )

        if not self.is_deceased and self.deceased_at:
            errors["is_deceased"] = (
                "Mark the patient as deceased or remove the deceased date."
            )

        if self.is_deceased and self.is_active:
            errors["is_active"] = (
                "A deceased patient cannot remain active."
            )

        if self.is_deceased and self.record_status == self.RecordStatus.ACTIVE:
            errors["record_status"] = (
                "A deceased patient cannot have an active record status."
            )

        if (
            self.record_status == self.RecordStatus.ACTIVE
            and not self.is_active
        ):
            errors["is_active"] = (
                "An active patient record must have is_active enabled."
            )

        if self.record_status in {
            self.RecordStatus.INACTIVE,
            self.RecordStatus.MERGED,
            self.RecordStatus.ENTERED_IN_ERROR,
        } and self.is_active:
            errors["is_active"] = (
                "Inactive, merged, and entered-in-error records "
                "cannot remain active."
            )

        if self.gender_identity == self.GenderIdentity.OTHER:
            if not self.gender_identity_description.strip():
                errors["gender_identity_description"] = (
                    "Describe the gender identity when Other is selected."
                )

        if (
            self.gender_identity != self.GenderIdentity.OTHER
            and self.gender_identity_description.strip()
        ):
            errors["gender_identity_description"] = (
                "A gender identity description is only needed "
                "when Other is selected."
            )

        if (
            self.confidential_record
            and not self.restricted_access_reason.strip()
        ):
            errors["restricted_access_reason"] = (
                "Provide a reason for restricting access to this record."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.mrn = (self.mrn or "").strip().upper()
        self.prefix = (self.prefix or "").strip()
        self.first_name = (self.first_name or "").strip()
        self.middle_name = (self.middle_name or "").strip()
        self.last_name = (self.last_name or "").strip()
        self.previous_last_name = (
            self.previous_last_name or ""
        ).strip()
        self.preferred_name = (self.preferred_name or "").strip()
        self.suffix = (self.suffix or "").strip()

        if self.is_deceased:
            self.is_active = False

            if self.record_status == self.RecordStatus.ACTIVE:
                self.record_status = self.RecordStatus.INACTIVE

        if self.record_status == self.RecordStatus.ACTIVE:
            self.is_active = True
        else:
            self.is_active = False

        self.full_clean()

        return super().save(*args, **kwargs)


class PatientIdentifier(UserTrackedModel):
    class IdentifierType(models.TextChoices):
        NATIONAL_ID = "national_id", "National identification"
        PASSPORT = "passport", "Passport"
        DRIVER_LICENSE = "driver_license", "Driver license"
        BIRTH_CERTIFICATE = "birth_certificate", "Birth certificate"
        INSURANCE_MEMBER = "insurance_member", "Insurance member number"
        FACILITY_ID = "facility_id", "Facility identifier"
        OTHER = "other", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="identifiers",
    )
    identifier_type = models.CharField(
        max_length=30,
        choices=IdentifierType.choices,
        db_index=True,
    )
    value = models.CharField(max_length=100, db_index=True)
    issuing_authority = models.CharField(max_length=150, blank=True)
    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="patient_identifiers",
        null=True,
        blank=True,
    )
    issued_on = models.DateField(null=True, blank=True)
    expires_on = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-is_primary", "identifier_type", "value")
        constraints = [
            models.UniqueConstraint(
                fields=("identifier_type", "value", "issuing_authority"),
                name="patient_identifier_unique_authority",
            ),
            models.UniqueConstraint(
                fields=("patient", "identifier_type"),
                condition=Q(is_primary=True, is_active=True),
                name="patient_one_primary_identifier_type",
            ),
        ]
        indexes = [
            models.Index(
                fields=("value", "identifier_type"),
                name="patient_identifier_lookup_idx",
            ),
        ]

    def __str__(self):
        return f"{self.get_identifier_type_display()}: {self.value}"

    def clean(self):
        if self.issued_on and self.expires_on and self.expires_on < self.issued_on:
            raise ValidationError(
                {"expires_on": "Expiration cannot be before issue date."}
            )

    def save(self, *args, **kwargs):
        self.value = self.value.strip()
        self.issuing_authority = self.issuing_authority.strip()
        self.full_clean()
        return super().save(*args, **kwargs)


class PatientAlias(UserTrackedModel):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="aliases",
    )
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    reason = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [
            models.Index(
                fields=("last_name", "first_name"),
                name="patient_alias_name_idx",
            ),
        ]

    def __str__(self):
        return " ".join(
            part.strip()
            for part in (self.first_name, self.middle_name, self.last_name)
            if part and part.strip()
        )


class PatientAddress(UserTrackedModel):
    class AddressType(models.TextChoices):
        HOME = "home", "Home"
        MAILING = "mailing", "Mailing"
        TEMPORARY = "temporary", "Temporary"
        WORK = "work", "Work"
        OTHER = "other", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    address_type = models.CharField(
        max_length=20,
        choices=AddressType.choices,
        default=AddressType.HOME,
    )
    line_1 = models.CharField(max_length=200)
    line_2 = models.CharField(max_length=200, blank=True)
    community_or_town = models.CharField(max_length=150, db_index=True)
    district = models.CharField(max_length=150, blank=True, db_index=True)
    county_or_state = models.CharField(max_length=150, db_index=True)
    postal_code = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, default="Liberia")
    directions_or_landmark = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-is_primary", "-is_active", "address_type")
        constraints = [
            models.UniqueConstraint(
                fields=("patient",),
                condition=Q(is_primary=True, is_active=True),
                name="patient_one_primary_address",
            ),
        ]
        indexes = [
            models.Index(
                fields=("county_or_state", "district", "community_or_town"),
                name="patient_address_location_idx",
            ),
        ]

    def __str__(self):
        parts = (
            self.line_1,
            self.line_2,
            self.community_or_town,
            self.district,
            self.county_or_state,
            self.country,
        )
        return ", ".join(part.strip() for part in parts if part and part.strip())

    def clean(self):
        errors = {}

        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            errors["valid_to"] = "The end date cannot be before the start date."

        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            errors["latitude"] = "Latitude must be between -90 and 90."

        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            errors["longitude"] = "Longitude must be between -180 and 180."

        if errors:
            raise ValidationError(errors)


class PatientContactPoint(UserTrackedModel):
    class ContactType(models.TextChoices):
        PHONE = "phone", "Phone"
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        OTHER = "other", "Other"

    class UseType(models.TextChoices):
        MOBILE = "mobile", "Mobile"
        HOME = "home", "Home"
        WORK = "work", "Work"
        TEMPORARY = "temporary", "Temporary"
        OTHER = "other", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="contact_points",
    )
    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        db_index=True,
    )
    use_type = models.CharField(
        max_length=20,
        choices=UseType.choices,
        blank=True,
    )
    value = models.CharField(max_length=254, db_index=True)
    extension = models.CharField(max_length=10, blank=True)
    notes = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("-is_primary", "sort_order", "contact_type")
        constraints = [
            models.UniqueConstraint(
                fields=("patient", "contact_type", "value"),
                name="patient_contact_unique_value",
            ),
            models.UniqueConstraint(
                fields=("patient", "contact_type"),
                condition=Q(is_primary=True, is_active=True),
                name="patient_one_primary_contact_type",
            ),
        ]

    def __str__(self):
        return f"{self.get_contact_type_display()}: {self.value}"

    def clean(self):
        if self.contact_type in {
            self.ContactType.PHONE,
            self.ContactType.WHATSAPP,
        }:
            phone_validator(self.value)

    def save(self, *args, **kwargs):
        self.value = self.value.strip()
        if self.contact_type == self.ContactType.EMAIL:
            self.value = self.value.lower()
        self.full_clean()
        return super().save(*args, **kwargs)


class EmergencyContact(UserTrackedModel):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    full_name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=30,
        validators=[phone_validator],
    )
    alternate_phone = models.CharField(
        max_length=30,
        validators=[phone_validator],
        blank=True,
    )
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_next_of_kin = models.BooleanField(default=False)
    is_legal_guardian = models.BooleanField(default=False)
    may_receive_information = models.BooleanField(default=False)
    may_make_decisions = models.BooleanField(default=False)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("-is_primary", "full_name")
        constraints = [
            models.UniqueConstraint(
                fields=("patient",),
                condition=Q(is_primary=True, is_active=True),
                name="patient_one_primary_emergency_contact",
            ),
        ]

    def __str__(self):
        return f"{self.full_name} — {self.relationship}"


class PatientConsent(UserTrackedModel):
    class ConsentType(models.TextChoices):
        GENERAL_TREATMENT = "general_treatment", "General treatment"
        DATA_SHARING = "data_sharing", "Data sharing"
        RESEARCH = "research", "Research participation"
        TELEHEALTH = "telehealth", "Telehealth"
        PHOTOGRAPHY = "photography", "Clinical photography"
        SMS = "sms", "SMS communication"
        EMAIL = "email", "Email communication"
        PORTAL = "portal", "Patient portal"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        GRANTED = "granted", "Granted"
        DECLINED = "declined", "Declined"
        WITHDRAWN = "withdrawn", "Withdrawn"
        EXPIRED = "expired", "Expired"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="consents",
    )
    consent_type = models.CharField(
        max_length=30,
        choices=ConsentType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        db_index=True,
    )
    effective_from = models.DateTimeField(default=timezone.now)
    effective_until = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    granted_by_patient = models.BooleanField(default=True)
    representative_name = models.CharField(max_length=200, blank=True)
    representative_relationship = models.CharField(max_length=100, blank=True)
    scope = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    document_reference = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("-effective_from",)
        indexes = [
            models.Index(
                fields=("patient", "consent_type", "status"),
                name="patient_consent_status_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.patient} — {self.get_consent_type_display()} "
            f"({self.get_status_display()})"
        )

    def clean(self):
        errors = {}

        if self.effective_until and self.effective_until < self.effective_from:
            errors["effective_until"] = (
                "Consent expiration cannot be before its effective date."
            )

        if not self.granted_by_patient and not self.representative_name.strip():
            errors["representative_name"] = (
                "Enter the representative who granted or declined consent."
            )

        if self.status == self.Status.WITHDRAWN and not self.withdrawn_at:
            errors["withdrawn_at"] = "Enter when the consent was withdrawn."

        if errors:
            raise ValidationError(errors)


class InsuranceCoverage(UserTrackedModel):
    class CoverageStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        EXPIRED = "expired", "Expired"
        PENDING = "pending", "Pending verification"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="insurance_coverages",
    )
    payer_name = models.CharField(max_length=200, db_index=True)
    plan_name = models.CharField(max_length=200, blank=True)
    member_number = models.CharField(max_length=100, db_index=True)
    group_number = models.CharField(max_length=100, blank=True)
    policy_holder_name = models.CharField(max_length=200, blank=True)
    relationship_to_policy_holder = models.CharField(max_length=100, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=CoverageStatus.choices,
        default=CoverageStatus.PENDING,
        db_index=True,
    )
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-is_primary", "payer_name")
        constraints = [
            models.UniqueConstraint(
                fields=("payer_name", "member_number"),
                name="patient_insurance_member_unique",
            ),
            models.UniqueConstraint(
                fields=("patient",),
                condition=Q(is_primary=True, status="active"),
                name="patient_one_primary_active_coverage",
            ),
        ]

    def __str__(self):
        return f"{self.payer_name} — {self.member_number}"

    def clean(self):
        if (
            self.effective_from
            and self.effective_until
            and self.effective_until < self.effective_from
        ):
            raise ValidationError(
                {"effective_until": "Coverage end cannot be before start."}
            )


class PatientFlag(UserTrackedModel):
    class Severity(models.TextChoices):
        INFORMATION = "information", "Information"
        CAUTION = "caution", "Caution"
        WARNING = "warning", "Warning"
        CRITICAL = "critical", "Critical"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="flags",
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.INFORMATION,
        db_index=True,
    )
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    requires_acknowledgment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ("-severity", "-starts_at")
        indexes = [
            models.Index(
                fields=("patient", "is_active", "severity"),
                name="patient_flag_active_idx",
            ),
        ]

    def __str__(self):
        return f"{self.patient}: {self.title}"

    @property
    def currently_active(self):
        now = timezone.now()
        return self.is_active and self.starts_at <= now and (
            self.ends_at is None or self.ends_at >= now
        )

    def clean(self):
        if self.ends_at and self.ends_at < self.starts_at:
            raise ValidationError(
                {"ends_at": "The flag end cannot be before its start."}
            )


class PatientFlagAcknowledgment(TimeStampedModel):
    flag = models.ForeignKey(
        PatientFlag,
        on_delete=models.CASCADE,
        related_name="acknowledgments",
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_flag_acknowledgments",
    )
    acknowledged_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=250, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("flag", "acknowledged_by"),
                name="patient_flag_acknowledgment_unique",
            ),
        ]

    def __str__(self):
        return f"{self.flag} acknowledged by {self.acknowledged_by}"


class PatientMergeRecord(UserTrackedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        COMPLETED = "completed", "Completed"
        REVERSED = "reversed", "Reversed"

    surviving_patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="merge_records_as_survivor",
    )
    duplicate_patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="merge_records_as_duplicate",
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="patient_merges_reviewed",
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("surviving_patient", "duplicate_patient"),
                name="patient_merge_pair_unique",
            ),
        ]

    def __str__(self):
        return (
            f"Merge {self.duplicate_patient.mrn} into "
            f"{self.surviving_patient.mrn}"
        )

    def clean(self):
        if self.surviving_patient_id == self.duplicate_patient_id:
            raise ValidationError(
                "A patient record cannot be merged into itself."
            )

class PatientRelationship(UserTrackedModel):
    class RelationshipType(models.TextChoices):
        PARENT = "parent", "Parent"
        CHILD = "child", "Child"
        SPOUSE = "spouse", "Spouse"
        SIBLING = "sibling", "Sibling"
        GUARDIAN = "guardian", "Guardian"
        DEPENDENT = "dependent", "Dependent"
        OTHER = "other", "Other"

    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="relationships_from",
    )

    related_patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="relationships_to",
    )

    relationship_type = models.CharField(
        max_length=20,
        choices=RelationshipType.choices,
    )

    notes = models.CharField(
        max_length=250,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=(
                    "patient",
                    "related_patient",
                    "relationship_type",
                ),
                name="patient_relationship_unique",
            ),
            models.CheckConstraint(
                condition=~models.Q(
                    patient=models.F("related_patient")
                ),
                name="patient_relationship_not_self",
            ),
        ]

    def __str__(self):
        return (
            f"{self.patient} — "
            f"{self.get_relationship_type_display()} — "
            f"{self.related_patient}"
        )

    def clean(self):
        if self.patient_id == self.related_patient_id:
            raise ValidationError(
                "A patient cannot have a relationship with themselves."
            )