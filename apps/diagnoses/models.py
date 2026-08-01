from django.db import models



"""
Liberia EHR Diagnosis Models

File:
apps/diagnoses/models.py

Purpose:
- Store WHO ICD-10 and ICD-11 terminology locally.
- Store symptoms, signs, disorders, diseases, injuries, and related concepts.
- Record patient diagnoses independently from terminology-source records.
- Preserve WHO API identifiers and metadata for future synchronization.
- Support licensed procedure terminology such as CPT without bundling CPT data.

Design principles:
- Terminology records are reference data.
- PatientDiagnosis records are clinical records.
- A terminology record can be updated without rewriting the patient's
  historical diagnosis text.
- ICD-10 and ICD-11 can coexist during migration and interoperability.
"""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# =====================================================================
# ABSTRACT BASE MODEL
# =====================================================================


class TimeStampedModel(models.Model):
    """
    Abstract base model that records creation and modification times.
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


# =====================================================================
# TERMINOLOGY SOURCE
# =====================================================================


class TerminologySource(TimeStampedModel):
    """
    Identifies an external or locally maintained terminology source.

    Examples:
    - WHO ICD-11 MMS
    - WHO ICD-10
    - AMA CPT
    - Liberia Ministry of Health local terminology
    """

    class SourceType(models.TextChoices):
        ICD_11 = "ICD_11", "WHO ICD-11"
        ICD_10 = "ICD_10", "WHO ICD-10"
        CPT = "CPT", "CPT"
        LOCAL = "LOCAL", "Local terminology"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
        unique=True,
    )

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        db_index=True,
    )

    organization = models.CharField(
        max_length=150,
        blank=True,
    )

    release_version = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Examples: 2026-01, ICD-10 2019, CPT 2026.",
    )

    canonical_url = models.URLField(
        max_length=500,
        blank=True,
    )

    api_base_url = models.URLField(
        max_length=500,
        blank=True,
    )

    language = models.CharField(
        max_length=20,
        default="en",
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    requires_license = models.BooleanField(
        default=False,
        help_text=(
            "True for terminology whose content requires a separate license, "
            "such as CPT."
        ),
    )

    last_synchronized_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["source_type", "name", "-release_version"]
        verbose_name = "terminology source"
        verbose_name_plural = "terminology sources"

    def __str__(self):
        version = f" {self.release_version}" if self.release_version else ""
        return f"{self.name}{version}"


# =====================================================================
# TERMINOLOGY CONCEPT
# =====================================================================


class ClinicalConcept(TimeStampedModel):
    """
    A locally stored clinical terminology concept.

    A concept may represent:
    - Disease
    - Disorder
    - Injury
    - Sign
    - Symptom
    - External cause
    - Encounter reason
    - Procedure, when licensed terminology is available

    For ICD-11:
    - foundation_uri identifies the Foundation entity.
    - linearization_uri identifies the MMS linearization entity.
    - code stores the ICD-11 MMS code where available.

    For ICD-10:
    - code stores the ICD-10 category or subcategory code.
    """

    class ConceptKind(models.TextChoices):
        DISEASE = "DISEASE", "Disease"
        DISORDER = "DISORDER", "Disorder"
        INJURY = "INJURY", "Injury"
        SIGN = "SIGN", "Sign"
        SYMPTOM = "SYMPTOM", "Symptom"
        FINDING = "FINDING", "Clinical finding"
        EXTERNAL_CAUSE = "EXTERNAL_CAUSE", "External cause"
        ENCOUNTER_REASON = "ENCOUNTER_REASON", "Reason for encounter"
        PROCEDURE = "PROCEDURE", "Procedure"
        EXTENSION_CODE = "EXTENSION_CODE", "Extension code"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    source = models.ForeignKey(
        TerminologySource,
        on_delete=models.PROTECT,
        related_name="concepts",
    )

    code = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
        help_text=(
            "Classification code such as ICD-10 A00.0 or ICD-11 1A00."
        ),
    )

    title = models.CharField(
        max_length=500,
        db_index=True,
    )

    fully_specified_name = models.CharField(
        max_length=700,
        blank=True,
    )

    short_description = models.TextField(
        blank=True,
    )

    definition = models.TextField(
        blank=True,
    )

    concept_kind = models.CharField(
        max_length=30,
        choices=ConceptKind.choices,
        default=ConceptKind.OTHER,
        db_index=True,
    )

    foundation_uri = models.URLField(
        max_length=700,
        blank=True,
        db_index=True,
        help_text="WHO ICD-11 Foundation entity URI.",
    )

    linearization_uri = models.URLField(
        max_length=700,
        blank=True,
        db_index=True,
        help_text="WHO ICD-11 MMS linearization URI.",
    )

    external_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Identifier supplied by the terminology provider.",
    )

    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    chapter_code = models.CharField(
        max_length=40,
        blank=True,
        db_index=True,
    )

    chapter_title = models.CharField(
        max_length=300,
        blank=True,
    )

    browser_url = models.URLField(
        max_length=700,
        blank=True,
    )

    is_leaf = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Indicates whether the concept has no narrower children.",
    )

    is_billable = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "Indicates that the source considers this code usable at the "
            "lowest reportable level. This does not establish local billing."
        ),
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    imported_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    source_payload = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Selected original API data retained for synchronization and "
            "troubleshooting."
        ),
    )

    class Meta:
        ordering = ["code", "title"]
        verbose_name = "clinical concept"
        verbose_name_plural = "clinical concepts"

        constraints = [
            models.UniqueConstraint(
                fields=["source", "code"],
                condition=~Q(code=""),
                name="unique_clinical_concept_source_code",
            ),
            models.UniqueConstraint(
                fields=["source", "foundation_uri"],
                condition=~Q(foundation_uri=""),
                name="unique_concept_source_foundation_uri",
            ),
            models.UniqueConstraint(
                fields=["source", "linearization_uri"],
                condition=~Q(linearization_uri=""),
                name="unique_concept_source_linearization_uri",
            ),
        ]

        indexes = [
            models.Index(
                fields=["source", "concept_kind", "is_active"],
                name="dx_concept_source_kind_idx",
            ),
            models.Index(
                fields=["source", "chapter_code"],
                name="dx_concept_source_chapter_idx",
            ),
            models.Index(
                fields=["title", "is_active"],
                name="dx_concept_title_active_idx",
            ),
        ]

    def __str__(self):
        if self.code:
            return f"{self.code} — {self.title}"
        return self.title

    def clean(self):
        """
        Validate concept identifiers and date ranges.
        """

        errors = {}

        if not self.code and not self.external_id:
            if not self.foundation_uri and not self.linearization_uri:
                errors["code"] = (
                    "Provide a code, external ID, Foundation URI, "
                    "or linearization URI."
                )

        if (
            self.effective_from
            and self.effective_to
            and self.effective_to < self.effective_from
        ):
            errors["effective_to"] = (
                "The effective end date cannot precede the start date."
            )

        if errors:
            raise ValidationError(errors)


# =====================================================================
# SYNONYMS AND SEARCH TERMS
# =====================================================================


class ClinicalConceptTerm(TimeStampedModel):
    """
    Stores synonyms, inclusion terms, abbreviations, and common phrases.

    This table supports:
    - Patient-friendly search
    - Clinician terminology
    - Common Liberian wording
    - WHO inclusion terms
    - Alternate spellings
    """

    class TermType(models.TextChoices):
        SYNONYM = "SYNONYM", "Synonym"
        INCLUSION = "INCLUSION", "Inclusion term"
        ABBREVIATION = "ABBREVIATION", "Abbreviation"
        COMMON_NAME = "COMMON_NAME", "Common name"
        LOCAL_TERM = "LOCAL_TERM", "Local term"
        SEARCH_TERM = "SEARCH_TERM", "Search term"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    concept = models.ForeignKey(
        ClinicalConcept,
        on_delete=models.CASCADE,
        related_name="terms",
    )

    term = models.CharField(
        max_length=500,
        db_index=True,
    )

    term_type = models.CharField(
        max_length=30,
        choices=TermType.choices,
        default=TermType.SYNONYM,
        db_index=True,
    )

    language = models.CharField(
        max_length=20,
        default="en",
        db_index=True,
    )

    is_preferred = models.BooleanField(
        default=False,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    source_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["term"]
        verbose_name = "clinical concept term"
        verbose_name_plural = "clinical concept terms"

        constraints = [
            models.UniqueConstraint(
                fields=["concept", "term", "language"],
                name="unique_concept_term_language",
            ),
        ]

        indexes = [
            models.Index(
                fields=["term", "language", "is_active"],
                name="dx_term_language_active_idx",
            ),
        ]

    def __str__(self):
        return self.term


# =====================================================================
# CONCEPT RELATIONSHIPS
# =====================================================================


class ClinicalConceptRelationship(TimeStampedModel):
    """
    Stores relationships between clinical concepts.

    Examples:
    - Symptom associated with diagnosis
    - ICD-10 concept mapped to ICD-11 concept
    - Broader or narrower concept
    - Exclusion or differential diagnosis relationship
    """

    class RelationshipType(models.TextChoices):
        MAPS_TO = "MAPS_TO", "Maps to"
        EQUIVALENT_TO = "EQUIVALENT_TO", "Equivalent to"
        BROADER_THAN = "BROADER_THAN", "Broader than"
        NARROWER_THAN = "NARROWER_THAN", "Narrower than"
        ASSOCIATED_SYMPTOM = "ASSOCIATED_SYMPTOM", "Associated symptom"
        ASSOCIATED_SIGN = "ASSOCIATED_SIGN", "Associated sign"
        DIFFERENTIAL = "DIFFERENTIAL", "Differential diagnosis"
        EXCLUDES = "EXCLUDES", "Excludes"
        CAUSED_BY = "CAUSED_BY", "Caused by"
        COMPLICATION_OF = "COMPLICATION_OF", "Complication of"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    source_concept = models.ForeignKey(
        ClinicalConcept,
        on_delete=models.CASCADE,
        related_name="outgoing_relationships",
    )

    target_concept = models.ForeignKey(
        ClinicalConcept,
        on_delete=models.CASCADE,
        related_name="incoming_relationships",
    )

    relationship_type = models.CharField(
        max_length=40,
        choices=RelationshipType.choices,
        db_index=True,
    )

    description = models.CharField(
        max_length=500,
        blank=True,
    )

    mapping_equivalence = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Optional mapping quality such as exact, broader, narrower, "
            "or approximate."
        ),
    )

    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = [
            "source_concept",
            "relationship_type",
            "target_concept",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "source_concept",
                    "target_concept",
                    "relationship_type",
                ],
                name="unique_clinical_concept_relationship",
            ),
            models.CheckConstraint(
                condition=~Q(source_concept=models.F("target_concept")),
                name="prevent_self_concept_relationship",
            ),
            models.CheckConstraint(
                condition=(
                    Q(confidence_score__isnull=True)
                    | (
                        Q(confidence_score__gte=0)
                        & Q(confidence_score__lte=1)
                    )
                ),
                name="concept_relationship_confidence_range",
            ),
        ]

    def __str__(self):
        return (
            f"{self.source_concept} "
            f"{self.get_relationship_type_display()} "
            f"{self.target_concept}"
        )


# =====================================================================
# PATIENT DIAGNOSIS
# =====================================================================


class PatientDiagnosis(TimeStampedModel):
    """
    Records a diagnosis assigned to a patient.

    Important:
    The original diagnosis text and code are copied into snapshot fields.
    This preserves the clinical record even if terminology data changes
    during a future WHO release.
    """

    class DiagnosisStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        RESOLVED = "RESOLVED", "Resolved"
        IN_REMISSION = "IN_REMISSION", "In remission"
        RECURRENCE = "RECURRENCE", "Recurrence"
        ENTERED_IN_ERROR = "ENTERED_IN_ERROR", "Entered in error"

    class VerificationStatus(models.TextChoices):
        PROVISIONAL = "PROVISIONAL", "Provisional"
        DIFFERENTIAL = "DIFFERENTIAL", "Differential"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REFUTED = "REFUTED", "Refuted"
        UNCONFIRMED = "UNCONFIRMED", "Unconfirmed"

    class DiagnosisType(models.TextChoices):
        PRINCIPAL = "PRINCIPAL", "Principal diagnosis"
        PRIMARY = "PRIMARY", "Primary diagnosis"
        SECONDARY = "SECONDARY", "Secondary diagnosis"
        COMORBIDITY = "COMORBIDITY", "Comorbidity"
        COMPLICATION = "COMPLICATION", "Complication"
        DIFFERENTIAL = "DIFFERENTIAL", "Differential diagnosis"
        ADMISSION = "ADMISSION", "Admission diagnosis"
        DISCHARGE = "DISCHARGE", "Discharge diagnosis"
        CHRONIC_PROBLEM = "CHRONIC_PROBLEM", "Chronic problem"
        OTHER = "OTHER", "Other"

    class Severity(models.TextChoices):
        MILD = "MILD", "Mild"
        MODERATE = "MODERATE", "Moderate"
        SEVERE = "SEVERE", "Severe"
        CRITICAL = "CRITICAL", "Critical"
        UNSPECIFIED = "UNSPECIFIED", "Unspecified"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="diagnoses",
    )

    encounter = models.ForeignKey(
        "encounters.Encounter",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="diagnoses",
    )

    concept = models.ForeignKey(
        ClinicalConcept,
        on_delete=models.PROTECT,
        related_name="patient_diagnoses",
    )

    diagnosis_type = models.CharField(
        max_length=30,
        choices=DiagnosisType.choices,
        default=DiagnosisType.PRIMARY,
        db_index=True,
    )

    clinical_status = models.CharField(
        max_length=30,
        choices=DiagnosisStatus.choices,
        default=DiagnosisStatus.ACTIVE,
        db_index=True,
    )

    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        default=VerificationStatus.CONFIRMED,
        db_index=True,
    )

    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        default=Severity.UNSPECIFIED,
        db_index=True,
    )

    diagnosed_on = models.DateField(
        default=timezone.localdate,
        db_index=True,
    )

    onset_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    resolved_on = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    code_snapshot = models.CharField(
        max_length=40,
        blank=True,
    )

    display_snapshot = models.CharField(
        max_length=500,
    )

    source_snapshot = models.CharField(
        max_length=150,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_patient_diagnoses",
    )

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_patient_diagnoses",
    )

    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_current_problem = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_sensitive = models.BooleanField(
        default=False,
        db_index=True,
    )

    class Meta:
        ordering = ["-diagnosed_on", "-created_at"]
        verbose_name = "patient diagnosis"
        verbose_name_plural = "patient diagnoses"

        indexes = [
            models.Index(
                fields=["patient", "clinical_status"],
                name="dx_patient_status_idx",
            ),
            models.Index(
                fields=["patient", "is_current_problem"],
                name="dx_patient_current_idx",
            ),
            models.Index(
                fields=["encounter", "diagnosis_type"],
                name="dx_encounter_type_idx",
            ),
            models.Index(
                fields=["concept", "diagnosed_on"],
                name="dx_concept_date_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(resolved_on__isnull=True)
                    | Q(resolved_on__gte=models.F("diagnosed_on"))
                ),
                name="diagnosis_resolved_after_diagnosed",
            ),
            models.CheckConstraint(
                condition=(
                    Q(onset_date__isnull=True)
                    | Q(onset_date__lte=models.F("diagnosed_on"))
                ),
                name="diagnosis_onset_before_diagnosed",
            ),
        ]

    def __str__(self):
        return f"{self.patient}: {self.display_snapshot}"

    def save(self, *args, **kwargs):
        """
        Populate immutable terminology snapshots when first recorded.
        """

        if self.concept_id:
            if not self.code_snapshot:
                self.code_snapshot = self.concept.code

            if not self.display_snapshot:
                self.display_snapshot = self.concept.title

            if not self.source_snapshot:
                self.source_snapshot = self.concept.source.name

        super().save(*args, **kwargs)

    def clean(self):
        """
        Validate dates and encounter ownership.
        """

        errors = {}

        if (
            self.onset_date
            and self.diagnosed_on
            and self.onset_date > self.diagnosed_on
        ):
            errors["onset_date"] = (
                "The onset date cannot be after the diagnosis date."
            )

        if (
            self.resolved_on
            and self.diagnosed_on
            and self.resolved_on < self.diagnosed_on
        ):
            errors["resolved_on"] = (
                "The resolved date cannot be before the diagnosis date."
            )

        if self.encounter_id:
            encounter_patient_id = getattr(
                self.encounter,
                "patient_id",
                None,
            )

            if (
                encounter_patient_id
                and encounter_patient_id != self.patient_id
            ):
                errors["encounter"] = (
                    "The selected encounter belongs to another patient."
                )

        if errors:
            raise ValidationError(errors)


# =====================================================================
# PATIENT DIAGNOSIS SYMPTOMS
# =====================================================================


class PatientDiagnosisManifestation(TimeStampedModel):
    """
    Associates signs or symptoms with an individual patient diagnosis.

    This records what the patient actually experienced; it is different
    from the general terminology relationship between a disease and its
    commonly associated symptoms.
    """

    class ManifestationType(models.TextChoices):
        SYMPTOM = "SYMPTOM", "Symptom"
        SIGN = "SIGN", "Sign"
        FINDING = "FINDING", "Clinical finding"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    diagnosis = models.ForeignKey(
        PatientDiagnosis,
        on_delete=models.CASCADE,
        related_name="manifestations",
    )

    concept = models.ForeignKey(
        ClinicalConcept,
        on_delete=models.PROTECT,
        related_name="patient_manifestations",
    )

    manifestation_type = models.CharField(
        max_length=20,
        choices=ManifestationType.choices,
        default=ManifestationType.SYMPTOM,
        db_index=True,
    )

    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Patient-specific description or wording.",
    )

    onset_date = models.DateField(
        null=True,
        blank=True,
    )

    resolved_on = models.DateField(
        null=True,
        blank=True,
    )

    severity = models.CharField(
        max_length=20,
        choices=PatientDiagnosis.Severity.choices,
        default=PatientDiagnosis.Severity.UNSPECIFIED,
    )

    is_present = models.BooleanField(
        default=True,
        db_index=True,
        help_text="False can represent a pertinent negative.",
    )

    notes = models.TextField(
        blank=True,
    )

    class Meta:
        ordering = ["manifestation_type", "concept__title"]

        constraints = [
            models.UniqueConstraint(
                fields=["diagnosis", "concept"],
                name="unique_manifestation_per_diagnosis",
            ),
            models.CheckConstraint(
                condition=(
                    Q(resolved_on__isnull=True)
                    | Q(onset_date__isnull=True)
                    | Q(resolved_on__gte=models.F("onset_date"))
                ),
                name="manifestation_resolution_after_onset",
            ),
        ]

    def __str__(self):
        return f"{self.diagnosis}: {self.concept}"


# =====================================================================
# PROCEDURE TERMINOLOGY PLACEHOLDER
# =====================================================================


class ProcedureCode(TimeStampedModel):
    """
    Stores procedure codes from authorized terminology sources.

    This model can hold:
    - Licensed CPT data
    - Future WHO ICHI data
    - Liberia-specific procedure codes

    Do not populate CPT descriptions from unauthorized public datasets.
    """

    class CodeSystem(models.TextChoices):
        CPT = "CPT", "CPT"
        ICHI = "ICHI", "WHO ICHI"
        LOCAL = "LOCAL", "Local procedure code"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    source = models.ForeignKey(
        TerminologySource,
        on_delete=models.PROTECT,
        related_name="procedure_codes",
    )

    code_system = models.CharField(
        max_length=20,
        choices=CodeSystem.choices,
        db_index=True,
    )

    code = models.CharField(
        max_length=30,
        db_index=True,
    )

    title = models.CharField(
        max_length=500,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    category = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    effective_from = models.DateField(
        null=True,
        blank=True,
    )

    effective_to = models.DateField(
        null=True,
        blank=True,
    )

    source_payload = models.JSONField(
        default=dict,
        blank=True,
    )

    class Meta:
        ordering = ["code_system", "code"]

        constraints = [
            models.UniqueConstraint(
                fields=["source", "code"],
                name="unique_procedure_source_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.title}"