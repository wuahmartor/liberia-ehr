# from django.db import models


# apps/analytics/models.py

# These models store analytics configuration and generated results. They do not duplicate patient or encounter data.

"""
Analytics Models

File:
apps/analytics/models.py

Purpose:
- Store reusable report definitions.
- Store configurable quality measures.
- Store calculated measure results.
- Store dashboard snapshots.
- Track analytics export jobs.

Clinical and operational data remain in their original apps.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract timestamp model used by Analytics records.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        abstract = True


class SavedReport(TimeStampedModel):
    """
    Store a reusable Analytics report configuration.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    report_type = models.CharField(
        max_length=100,
        db_index=True,
    )

    filters = models.JSONField(
        default=dict,
        blank=True,
    )

    columns = models.JSONField(
        default=list,
        blank=True,
    )

    sort_configuration = models.JSONField(
        default=dict,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_analytics_reports",
    )

    is_shared = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = [
            "name",
        ]

        indexes = [
            models.Index(
                fields=[
                    "report_type",
                    "is_active",
                ],
                name="an_report_type_active_idx",
            ),
        ]

        def __str__(self):
            return self.name


class MeasureDefinition(TimeStampedModel):
    """
    Define a quality, clinical, operational, or nursing measure.
    """

    class MeasureCategory(models.TextChoices):
        CLINICAL = "clinical", "Clinical"
        NURSING = "nursing", "Nursing"
        QUALITY = "quality", "Quality"
        OPERATIONS = "operations", "Operations"
        POPULATION = "population", "Population Health"
        FINANCIAL = "financial", "Financial"

    class ValueType(models.TextChoices):
        COUNT = "count", "Count"
        PERCENTAGE = "percentage", "Percentage"
        RATE = "rate", "Rate"
        DURATION = "duration", "Duration"
        CURRENCY = "currency", "Currency"
        DECIMAL = "decimal", "Decimal"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    code = models.CharField(
        max_length=100,
        unique=True,
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    category = models.CharField(
        max_length=30,
        choices=MeasureCategory.choices,
        db_index=True,
    )

    value_type = models.CharField(
        max_length=30,
        choices=ValueType.choices,
        default=ValueType.PERCENTAGE,
    )

    numerator_definition = models.JSONField(
        default=dict,
        blank=True,
    )

    denominator_definition = models.JSONField(
        default=dict,
        blank=True,
    )

    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    warning_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_measure_definitions",
    )

    class Meta:
        ordering = [
            "category",
            "name",
        ]

    def __str__(self):
        return f"{self.code} — {self.name}"


class MeasureResult(TimeStampedModel):
    """
    Store a calculated measure result for a reporting period.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    measure = models.ForeignKey(
        MeasureDefinition,
        on_delete=models.CASCADE,
        related_name="results",
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="analytics_measure_results",
        null=True,
        blank=True,
    )

    period_start = models.DateField(
        db_index=True,
    )

    period_end = models.DateField(
        db_index=True,
    )

    numerator = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    denominator = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    result_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
    )

    calculated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-period_end",
            "measure__name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "measure",
                    "facility",
                    "period_start",
                    "period_end",
                ],
                name="an_unique_measure_period",
            ),
        ]

    def __str__(self):
        return (
            f"{self.measure.code}: "
            f"{self.period_start} to {self.period_end}"
        )


class AnalyticsSnapshot(TimeStampedModel):
    """
    Store precomputed dashboard data for expensive reports.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    snapshot_type = models.CharField(
        max_length=100,
        db_index=True,
    )

    facility = models.ForeignKey(
        "facilities.Facility",
        on_delete=models.PROTECT,
        related_name="analytics_snapshots",
        null=True,
        blank=True,
    )

    period_start = models.DateTimeField()
    period_end = models.DateTimeField()

    data = models.JSONField(
        default=dict,
    )

    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="generated_analytics_snapshots",
        null=True,
        blank=True,
    )

    generated_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-generated_at",
        ]

        indexes = [
            models.Index(
                fields=[
                    "snapshot_type",
                    "generated_at",
                ],
                name="an_snapshot_type_date_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.snapshot_type} "
            f"({self.period_start} – {self.period_end})"
        )


class DataExportJob(TimeStampedModel):
    """
    Track asynchronous or manually generated data exports.
    """

    class ExportStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class ExportFormat(models.TextChoices):
        CSV = "csv", "CSV"
        XLSX = "xlsx", "Excel"
        PDF = "pdf", "PDF"
        JSON = "json", "JSON"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="analytics_export_jobs",
    )

    export_type = models.CharField(
        max_length=100,
        db_index=True,
    )

    export_format = models.CharField(
        max_length=20,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
    )

    filters = models.JSONField(
        default=dict,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=ExportStatus.choices,
        default=ExportStatus.PENDING,
        db_index=True,
    )

    file = models.FileField(
        upload_to="analytics/exports/%Y/%m/",
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

    started_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = [
            "-created_at",
        ]

    def __str__(self):
        return f"{self.export_type} — {self.get_status_display()}"