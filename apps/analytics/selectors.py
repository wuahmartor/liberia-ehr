

"""
Analytics Selectors

File:
apps/analytics/selectors.py

Purpose:
- Read source data from clinical and operational apps.
- Keep complex queryset logic outside views.
- Return database-level aggregations whenever possible.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Q,
)
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.encounters.models import Encounter
from apps.patients.models import Patient


OPEN_ENCOUNTER_STATUSES = [
    Encounter.EncounterStatus.ARRIVED,
    Encounter.EncounterStatus.TRIAGED,
    Encounter.EncounterStatus.IN_PROGRESS,
    Encounter.EncounterStatus.ON_HOLD,
]


def normalized_date_range(
    *,
    start_date: date | None,
    end_date: date | None,
) -> tuple[datetime, datetime]:
    """
    Convert date filters into timezone-aware datetime boundaries.
    """

    today = timezone.localdate()

    if end_date is None:
        end_date = today

    if start_date is None:
        start_date = end_date - timedelta(days=29)

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min,
        )
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date,
            time.max,
        )
    )

    return start_datetime, end_datetime


def encounter_queryset(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    encounter_type: str = "",
    status: str = "",
):
    """
    Return encounters matching Analytics dashboard filters.
    """

    start_datetime, end_datetime = normalized_date_range(
        start_date=start_date,
        end_date=end_date,
    )

    queryset = (
        Encounter.objects
        .select_related(
            "patient",
            "attending_provider",
        )
        .filter(
            start_datetime__range=(
                start_datetime,
                end_datetime,
            ),
        )
    )

    if encounter_type:
        queryset = queryset.filter(
            encounter_type=encounter_type,
        )

    if status:
        queryset = queryset.filter(
            status=status,
        )

    return queryset


def patient_metrics():
    """
    Return basic patient-registry metrics.
    """

    return Patient.objects.aggregate(
        total_patients=Count("pk"),
        active_patients=Count(
            "pk",
            filter=Q(
                is_active=True,
            ),
        ),
        deceased_patients=Count(
            "pk",
            filter=Q(
                is_deceased=True,
            ),
        ),
    )


def encounter_metrics(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    encounter_type: str = "",
    status: str = "",
):
    """
    Return summary encounter metrics.
    """

    queryset = encounter_queryset(
        start_date=start_date,
        end_date=end_date,
        encounter_type=encounter_type,
        status=status,
    )

    completed_status = Encounter.EncounterStatus.COMPLETED

    metrics = queryset.aggregate(
        total_encounters=Count("pk"),
        active_encounters=Count(
            "pk",
            filter=Q(
                is_active=True,
                status__in=OPEN_ENCOUNTER_STATUSES,
            ),
        ),
        completed_encounters=Count(
            "pk",
            filter=Q(
                status=completed_status,
            ),
        ),
        cancelled_encounters=Count(
            "pk",
            filter=Q(
                status=Encounter.EncounterStatus.CANCELLED,
            ),
        ),
    )

    completed_queryset = queryset.filter(
        status=completed_status,
        arrived_at__isnull=False,
        completed_at__isnull=False,
    )

    duration_expression = ExpressionWrapper(
        F("completed_at") - F("arrived_at"),
        output_field=DurationField(),
    )

    duration_metrics = completed_queryset.aggregate(
        average_visit_duration=Avg(
            duration_expression,
        ),
    )

    metrics.update(
        duration_metrics,
    )

    return metrics


def encounter_daily_trend(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    encounter_type: str = "",
    status: str = "",
):
    """
    Return daily encounter totals for charts.
    """

    return list(
        encounter_queryset(
            start_date=start_date,
            end_date=end_date,
            encounter_type=encounter_type,
            status=status,
        )
        .annotate(
            encounter_date=TruncDate(
                "start_datetime",
            ),
        )
        .values(
            "encounter_date",
        )
        .annotate(
            total=Count("pk"),
            completed=Count(
                "pk",
                filter=Q(
                    status=Encounter.EncounterStatus.COMPLETED,
                ),
            ),
        )
        .order_by(
            "encounter_date",
        )
    )


def encounter_status_breakdown(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    encounter_type: str = "",
):
    """
    Return encounter totals grouped by status.
    """

    return list(
        encounter_queryset(
            start_date=start_date,
            end_date=end_date,
            encounter_type=encounter_type,
        )
        .values(
            "status",
        )
        .annotate(
            total=Count("pk"),
        )
        .order_by(
            "-total",
        )
    )


def recent_encounters(
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    encounter_type: str = "",
    status: str = "",
    limit: int = 15,
):
    """
    Return recent filtered encounters for the dashboard table.
    """

    return encounter_queryset(
        start_date=start_date,
        end_date=end_date,
        encounter_type=encounter_type,
        status=status,
    ).order_by(
        "-start_datetime",
    )[:limit]