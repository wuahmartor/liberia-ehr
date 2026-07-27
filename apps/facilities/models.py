from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


phone_validator = RegexValidator(
    regex=r"^\+?[0-9()\-\s]{7,25}$",
    message=(
        "Enter a valid phone number using digits and optional spaces, "
        "parentheses, hyphens, or a leading +."
    ),
)


class TimeStampedModel(models.Model):
    """
    Abstract model that adds creation and modification timestamps.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True


class UserTrackedModel(TimeStampedModel):
    """
    Abstract model that records who created and last updated a record.
    """

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


class FacilityQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def search(self, query: str):
        query = (query or "").strip()

        if not query:
            return self.none()

        return self.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(short_name__icontains=query)
            | Q(community_or_city__icontains=query)
            | Q(district__icontains=query)
            | Q(county_or_state__icontains=query)
        )


class Facility(UserTrackedModel):
    """
    Healthcare organization or service location.

    Patient.registration_facility and PatientIdentifier.facility point
    to this model using the lazy reference "facilities.Facility".
    """

    class FacilityType(models.TextChoices):
        NATIONAL_HOSPITAL = (
            "national_hospital",
            "National Referral Hospital",
        )
        REGIONAL_HOSPITAL = (
            "regional_hospital",
            "Regional Hospital",
        )
        COUNTY_HOSPITAL = (
            "county_hospital",
            "County Hospital",
        )
        DISTRICT_HOSPITAL = (
            "district_hospital",
            "District Hospital",
        )
        PRIVATE_HOSPITAL = (
            "private_hospital",
            "Private Hospital",
        )
        CLINIC = "clinic", "Clinic"
        HEALTH_CENTER = "health_center", "Health Center"
        HEALTH_POST = "health_post", "Health Post"
        MATERNITY_CENTER = "maternity_center", "Maternity Center"
        LABORATORY = "laboratory", "Laboratory"
        PHARMACY = "pharmacy", "Pharmacy"
        IMAGING_CENTER = "imaging_center", "Imaging Center"
        REHABILITATION_CENTER = (
            "rehabilitation_center",
            "Rehabilitation Center",
        )
        MOBILE_CLINIC = "mobile_clinic", "Mobile Clinic"
        COMMUNITY_PROGRAM = (
            "community_program",
            "Community Health Program",
        )
        OTHER = "other", "Other"

    class OwnershipType(models.TextChoices):
        GOVERNMENT = "government", "Government"
        PRIVATE = "private", "Private"
        FAITH_BASED = "faith_based", "Faith-Based"
        NGO = "ngo", "Non-Governmental Organization"
        COMMUNITY = "community", "Community-Owned"
        PUBLIC_PRIVATE = (
            "public_private",
            "Public-Private Partnership",
        )
        OTHER = "other", "Other"

    class OperationalStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        TEMPORARILY_CLOSED = (
            "temporarily_closed",
            "Temporarily Closed",
        )
        PERMANENTLY_CLOSED = (
            "permanently_closed",
            "Permanently Closed",
        )
        UNDER_CONSTRUCTION = (
            "under_construction",
            "Under Construction",
        )
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=200,
        db_index=True,
    )
    short_name = models.CharField(
        max_length=100,
        blank=True,
    )
    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text=(
            "Unique facility code, such as JFK-MC, ELWA-HOSP, "
            "or MARGIBI-CLINIC-01."
        ),
    )

    facility_type = models.CharField(
        max_length=40,
        choices=FacilityType.choices,
        default=FacilityType.CLINIC,
        db_index=True,
    )
    ownership_type = models.CharField(
        max_length=30,
        choices=OwnershipType.choices,
        default=OwnershipType.GOVERNMENT,
        db_index=True,
    )
    operational_status = models.CharField(
        max_length=30,
        choices=OperationalStatus.choices,
        default=OperationalStatus.ACTIVE,
        db_index=True,
    )

    ministry_license_number = models.CharField(
        max_length=100,
        blank=True,
    )
    accreditation_number = models.CharField(
        max_length=100,
        blank=True,
    )

    phone_number = models.CharField(
        max_length=30,
        validators=[phone_validator],
        blank=True,
    )
    alternate_phone = models.CharField(
        max_length=30,
        validators=[phone_validator],
        blank=True,
    )
    emergency_phone = models.CharField(
        max_length=30,
        validators=[phone_validator],
        blank=True,
    )
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)

    address_line_1 = models.CharField(
        max_length=200,
        blank=True,
    )
    address_line_2 = models.CharField(
        max_length=200,
        blank=True,
    )
    community_or_city = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )
    district = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )
    county_or_state = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )
    postal_code = models.CharField(
        max_length=30,
        blank=True,
    )
    country = models.CharField(
        max_length=100,
        default="Liberia",
    )
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

    parent_facility = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="child_facilities",
        null=True,
        blank=True,
        help_text=(
            "Optional parent organization for satellite clinics "
            "or service locations."
        ),
    )

    bed_capacity = models.PositiveIntegerField(
        default=0,
        help_text="Configured inpatient-bed capacity.",
    )

    provides_emergency_services = models.BooleanField(default=False)
    provides_inpatient_services = models.BooleanField(default=False)
    provides_outpatient_services = models.BooleanField(default=True)
    provides_maternity_services = models.BooleanField(default=False)
    provides_surgical_services = models.BooleanField(default=False)
    provides_laboratory_services = models.BooleanField(default=False)
    provides_pharmacy_services = models.BooleanField(default=False)
    provides_imaging_services = models.BooleanField(default=False)

    timezone_name = models.CharField(
        max_length=100,
        default="Africa/Monrovia",
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    objects = FacilityQuerySet.as_manager()

    class Meta:
        ordering = ("name",)
        verbose_name = "facility"
        verbose_name_plural = "facilities"

        indexes = [
            models.Index(
                fields=("name", "is_active"),
                name="facility_name_active_idx",
            ),
            models.Index(
                fields=("county_or_state", "district"),
                name="facility_location_idx",
            ),
            models.Index(
                fields=("facility_type", "operational_status"),
                name="facility_type_status_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(latitude__isnull=True)
                    | Q(latitude__gte=-90, latitude__lte=90)
                ),
                name="facility_latitude_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(longitude__isnull=True)
                    | Q(longitude__gte=-180, longitude__lte=180)
                ),
                name="facility_longitude_valid",
            ),
            models.CheckConstraint(
                condition=~Q(id=models.F("parent_facility")),
                name="facility_not_own_parent",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    @property
    def full_address(self) -> str:
        parts = [
            self.address_line_1,
            self.address_line_2,
            self.community_or_city,
            self.district,
            self.county_or_state,
            self.country,
        ]

        return ", ".join(
            part.strip()
            for part in parts
            if part and part.strip()
        )

    def clean(self) -> None:
        errors = {}

        if self.parent_facility_id == self.id:
            errors["parent_facility"] = (
                "A facility cannot be its own parent."
            )

        if self.latitude is not None:
            if not -90 <= self.latitude <= 90:
                errors["latitude"] = (
                    "Latitude must be between -90 and 90."
                )

        if self.longitude is not None:
            if not -180 <= self.longitude <= 180:
                errors["longitude"] = (
                    "Longitude must be between -180 and 180."
                )

        if (
            self.operational_status
            == self.OperationalStatus.PERMANENTLY_CLOSED
            and self.is_active
        ):
            errors["is_active"] = (
                "A permanently closed facility cannot remain active."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.short_name = self.short_name.strip()
        self.code = self.code.strip().upper()
        self.email = self.email.strip().lower()

        self.full_clean()

        return super().save(*args, **kwargs)


class DepartmentQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class Department(UserTrackedModel):
    """
    Major administrative or clinical division within a facility.

    Examples:
    - Nursing
    - Laboratory
    - Pharmacy
    - Radiology
    - Surgery
    - Medical Records
    """

    class DepartmentType(models.TextChoices):
        CLINICAL = "clinical", "Clinical"
        NURSING = "nursing", "Nursing"
        DIAGNOSTIC = "diagnostic", "Diagnostic"
        PHARMACY = "pharmacy", "Pharmacy"
        ADMINISTRATIVE = "administrative", "Administrative"
        FINANCE = "finance", "Finance"
        SUPPORT = "support", "Support Service"
        OTHER = "other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="departments",
    )

    name = models.CharField(
        max_length=150,
        db_index=True,
    )
    code = models.CharField(
        max_length=30,
    )
    department_type = models.CharField(
        max_length=30,
        choices=DepartmentType.choices,
        default=DepartmentType.CLINICAL,
        db_index=True,
    )

    description = models.TextField(blank=True)

    phone_extension = models.CharField(
        max_length=15,
        blank=True,
    )
    email = models.EmailField(blank=True)

    is_clinical = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    objects = DepartmentQuerySet.as_manager()

    class Meta:
        ordering = ("facility__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"),
                name="department_facility_code_unique",
            ),
            models.UniqueConstraint(
                fields=("facility", "name"),
                name="department_facility_name_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("facility", "is_active"),
                name="department_facility_active_idx",
            ),
            models.Index(
                fields=("department_type", "is_active"),
                name="department_type_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.facility.code} — {self.name}"

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()
        self.email = self.email.strip().lower()

        self.full_clean()

        return super().save(*args, **kwargs)


class ClinicalUnitQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class ClinicalUnit(UserTrackedModel):
    """
    Operational service area within a department.

    Examples:
    - Emergency Department
    - Operating Room
    - Medical Ward
    - Pediatric Ward
    - Outpatient Clinic
    """

    class UnitType(models.TextChoices):
        EMERGENCY = "emergency", "Emergency"
        OUTPATIENT = "outpatient", "Outpatient"
        INPATIENT = "inpatient", "Inpatient"
        INTENSIVE_CARE = "intensive_care", "Intensive Care"
        OPERATING_ROOM = "operating_room", "Operating Room"
        RECOVERY = "recovery", "Post-Anesthesia Recovery"
        MATERNITY = "maternity", "Maternity"
        LABORATORY = "laboratory", "Laboratory"
        PHARMACY = "pharmacy", "Pharmacy"
        RADIOLOGY = "radiology", "Radiology"
        REHABILITATION = "rehabilitation", "Rehabilitation"
        COMMUNITY = "community", "Community Health"
        OTHER = "other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="clinical_units",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="clinical_units",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=150,
        db_index=True,
    )
    code = models.CharField(
        max_length=30,
    )
    unit_type = models.CharField(
        max_length=30,
        choices=UnitType.choices,
        default=UnitType.OUTPATIENT,
        db_index=True,
    )

    description = models.TextField(blank=True)
    floor_or_location = models.CharField(
        max_length=100,
        blank=True,
    )

    accepts_admissions = models.BooleanField(default=False)
    is_clinical = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    objects = ClinicalUnitQuerySet.as_manager()

    class Meta:
        ordering = ("facility__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"),
                name="clinical_unit_facility_code_unique",
            ),
            models.UniqueConstraint(
                fields=("facility", "name"),
                name="clinical_unit_facility_name_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("facility", "unit_type", "is_active"),
                name="clinical_unit_lookup_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.facility.code} — {self.name}"

    def clean(self) -> None:
        if self.department_id:
            if self.department.facility_id != self.facility_id:
                raise ValidationError(
                    {
                        "department": (
                            "The department must belong to the same "
                            "facility as the clinical unit."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()

        self.full_clean()

        return super().save(*args, **kwargs)


class Room(UserTrackedModel):
    """
    Physical room within a clinical unit.
    """

    class RoomType(models.TextChoices):
        EXAMINATION = "examination", "Examination Room"
        PATIENT_ROOM = "patient_room", "Patient Room"
        OPERATING_ROOM = "operating_room", "Operating Room"
        PROCEDURE_ROOM = "procedure_room", "Procedure Room"
        LABOR_ROOM = "labor_room", "Labor Room"
        DELIVERY_ROOM = "delivery_room", "Delivery Room"
        RECOVERY_ROOM = "recovery_room", "Recovery Room"
        ISOLATION_ROOM = "isolation_room", "Isolation Room"
        CONSULTATION = "consultation", "Consultation Room"
        LABORATORY = "laboratory", "Laboratory Room"
        STORAGE = "storage", "Storage Room"
        OTHER = "other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="rooms",
    )
    clinical_unit = models.ForeignKey(
        ClinicalUnit,
        on_delete=models.PROTECT,
        related_name="rooms",
    )

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30)

    room_type = models.CharField(
        max_length=30,
        choices=RoomType.choices,
        default=RoomType.PATIENT_ROOM,
        db_index=True,
    )

    floor = models.CharField(
        max_length=50,
        blank=True,
    )
    capacity = models.PositiveSmallIntegerField(default=1)

    is_negative_pressure = models.BooleanField(default=False)
    is_isolation_capable = models.BooleanField(default=False)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = (
            "facility__name",
            "clinical_unit__name",
            "name",
        )
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"),
                name="room_facility_code_unique",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1),
                name="room_capacity_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=("clinical_unit", "is_active"),
                name="room_unit_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.facility.code} — "
            f"{self.clinical_unit.name} — {self.name}"
        )

    def clean(self) -> None:
        if self.clinical_unit_id:
            if self.clinical_unit.facility_id != self.facility_id:
                raise ValidationError(
                    {
                        "clinical_unit": (
                            "The clinical unit must belong to the same "
                            "facility as the room."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()

        self.full_clean()

        return super().save(*args, **kwargs)


class Bed(UserTrackedModel):
    """
    Physical or operational patient bed.

    The bed model is kept in the facilities app because it describes
    facility capacity. Patient assignments and admissions should be
    handled in the encounters app.
    """

    class BedType(models.TextChoices):
        STANDARD = "standard", "Standard"
        ICU = "icu", "Intensive Care"
        PEDIATRIC = "pediatric", "Pediatric"
        MATERNITY = "maternity", "Maternity"
        NEONATAL = "neonatal", "Neonatal"
        EMERGENCY = "emergency", "Emergency"
        RECOVERY = "recovery", "Recovery"
        ISOLATION = "isolation", "Isolation"
        OBSERVATION = "observation", "Observation"
        OTHER = "other", "Other"

    class BedStatus(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        RESERVED = "reserved", "Reserved"
        CLEANING = "cleaning", "Cleaning"
        MAINTENANCE = "maintenance", "Maintenance"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT,
        related_name="beds",
    )
    clinical_unit = models.ForeignKey(
        ClinicalUnit,
        on_delete=models.PROTECT,
        related_name="beds",
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.PROTECT,
        related_name="beds",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=100,
    )
    code = models.CharField(
        max_length=30,
    )

    bed_type = models.CharField(
        max_length=30,
        choices=BedType.choices,
        default=BedType.STANDARD,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=BedStatus.choices,
        default=BedStatus.AVAILABLE,
        db_index=True,
    )

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = (
            "facility__name",
            "clinical_unit__name",
            "code",
        )
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"),
                name="bed_facility_code_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=("clinical_unit", "status", "is_active"),
                name="bed_unit_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.facility.code} — Bed {self.code}"

    def clean(self) -> None:
        errors = {}

        if self.clinical_unit_id:
            if self.clinical_unit.facility_id != self.facility_id:
                errors["clinical_unit"] = (
                    "The clinical unit must belong to the same "
                    "facility as the bed."
                )

        if self.room_id:
            if self.room.facility_id != self.facility_id:
                errors["room"] = (
                    "The room must belong to the same facility as the bed."
                )

            if self.room.clinical_unit_id != self.clinical_unit_id:
                errors["room"] = (
                    "The room must belong to the bed's clinical unit."
                )

        if (
            not self.is_active
            and self.status == self.BedStatus.AVAILABLE
        ):
            errors["status"] = (
                "An inactive bed cannot be marked available."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()

        self.full_clean()

        return super().save(*args, **kwargs)


class FacilityOperatingHour(UserTrackedModel):
    """
    Normal operating schedule for a facility.
    """

    class Weekday(models.IntegerChoices):
        MONDAY = 1, "Monday"
        TUESDAY = 2, "Tuesday"
        WEDNESDAY = 3, "Wednesday"
        THURSDAY = 4, "Thursday"
        FRIDAY = 5, "Friday"
        SATURDAY = 6, "Saturday"
        SUNDAY = 7, "Sunday"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="operating_hours",
    )
    weekday = models.PositiveSmallIntegerField(
        choices=Weekday.choices,
    )
    opens_at = models.TimeField(
        null=True,
        blank=True,
    )
    closes_at = models.TimeField(
        null=True,
        blank=True,
    )
    is_closed = models.BooleanField(default=False)
    is_24_hours = models.BooleanField(default=False)
    notes = models.CharField(
        max_length=200,
        blank=True,
    )

    class Meta:
        ordering = ("facility", "weekday")
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "weekday"),
                name="facility_weekday_hours_unique",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.facility.code} — "
            f"{self.get_weekday_display()}"
        )

    def clean(self) -> None:
        errors = {}

        if self.is_closed and self.is_24_hours:
            errors["is_24_hours"] = (
                "A facility cannot be both closed and open 24 hours."
            )

        if self.is_closed:
            if self.opens_at or self.closes_at:
                errors["is_closed"] = (
                    "Remove opening and closing times when closed."
                )

        elif self.is_24_hours:
            if self.opens_at or self.closes_at:
                errors["is_24_hours"] = (
                    "Opening and closing times are not needed for "
                    "24-hour operation."
                )

        else:
            if not self.opens_at:
                errors["opens_at"] = "Enter the opening time."

            if not self.closes_at:
                errors["closes_at"] = "Enter the closing time."

        if errors:
            raise ValidationError(errors)


class FacilityService(UserTrackedModel):
    """
    Service offered by a facility.
    """

    class ServiceCategory(models.TextChoices):
        GENERAL_MEDICINE = "general_medicine", "General Medicine"
        EMERGENCY = "emergency", "Emergency Care"
        SURGERY = "surgery", "Surgery"
        MATERNITY = "maternity", "Maternity"
        PEDIATRICS = "pediatrics", "Pediatrics"
        MENTAL_HEALTH = "mental_health", "Mental Health"
        LABORATORY = "laboratory", "Laboratory"
        PHARMACY = "pharmacy", "Pharmacy"
        IMAGING = "imaging", "Imaging"
        REHABILITATION = "rehabilitation", "Rehabilitation"
        DENTAL = "dental", "Dental"
        HIV_TB = "hiv_tb", "HIV/TB Services"
        VACCINATION = "vaccination", "Vaccination"
        COMMUNITY_HEALTH = (
            "community_health",
            "Community Health",
        )
        OTHER = "other", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.CASCADE,
        related_name="services",
    )

    name = models.CharField(
        max_length=150,
    )
    code = models.CharField(
        max_length=30,
    )
    category = models.CharField(
        max_length=40,
        choices=ServiceCategory.choices,
        default=ServiceCategory.GENERAL_MEDICINE,
        db_index=True,
    )

    description = models.TextField(blank=True)
    requires_appointment = models.BooleanField(default=False)
    accepts_walk_ins = models.BooleanField(default=True)
    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ("facility__name", "name")
        constraints = [
            models.UniqueConstraint(
                fields=("facility", "code"),
                name="facility_service_code_unique",
            ),
            models.UniqueConstraint(
                fields=("facility", "name"),
                name="facility_service_name_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.facility.code} — {self.name}"

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        self.code = self.code.strip().upper()

        self.full_clean()

        return super().save(*args, **kwargs)