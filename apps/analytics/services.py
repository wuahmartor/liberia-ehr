


"""
Analytics Services

File:
apps/analytics/services.py

Purpose:
- Parse Analytics filters.
- Format selector results.
- Build dashboard context for full and HTMX requests.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.utils import timezone

from apps.encounters.models import Encounter

from .selectors import (
    encounter_daily_trend,
    encounter_metrics,
    encounter_status_breakdown,
    patient_metrics,
    recent_encounters,
)

from .models import MeasureDefinition, MeasureResult


def quality_analytics_context(request) -> dict:
    """
    Build context for the Quality Analytics workspace.
    """

    context = analytics_dashboard_context(request)

    context.update(
        {
            "measure_definitions": (
                MeasureDefinition.objects
                .filter(is_active=True)
                .order_by(
                    "category",
                    "name",
                )
            ),
            "latest_measure_results": (
                MeasureResult.objects
                .select_related(
                    "measure",
                    "facility",
                )
                .order_by(
                    "-period_end",
                    "-calculated_at",
                )[:25]
            ),
        }
    )

    return context

def parse_date(
    value: str,
    *,
    default: date,
) -> date:
    """
    Parse an ISO date value safely.
    """

    if not value:
        return default

    try:
        return date.fromisoformat(value)
    except ValueError:
        return default


def analytics_filters(request) -> dict:
    """
    Read and normalize Analytics filters from query parameters.
    """

    today = timezone.localdate()
    default_start = today - timedelta(days=29)

    start_date = parse_date(
        request.GET.get("start_date", ""),
        default=default_start,
    )

    end_date = parse_date(
        request.GET.get("end_date", ""),
        default=today,
    )

    if start_date > end_date:
        start_date, end_date = end_date, start_date

    return {
        "start_date": start_date,
        "end_date": end_date,
        "encounter_type": request.GET.get(
            "encounter_type",
            "",
        ).strip(),
        "status": request.GET.get(
            "status",
            "",
        ).strip(),
    }


def format_duration(duration) -> str:
    """
    Format a timedelta into a readable dashboard value.
    """

    if duration is None:
        return "No data"

    total_minutes = int(
        duration.total_seconds() // 60
    )

    hours, minutes = divmod(
        total_minutes,
        60,
    )

    if hours:
        return f"{hours}h {minutes}m"

    return f"{minutes}m"


def analytics_dashboard_context(request) -> dict:
    """
    Build the main HTMX Analytics dashboard context.
    """

    filters = analytics_filters(
        request,
    )

    patient_summary = patient_metrics()

    encounter_summary = encounter_metrics(
        **filters,
    )

    average_duration = encounter_summary.get(
        "average_visit_duration",
    )

    trend = encounter_daily_trend(
        **filters,
    )

    status_breakdown = encounter_status_breakdown(
        start_date=filters["start_date"],
        end_date=filters["end_date"],
        encounter_type=filters["encounter_type"],
    )

    return {
        "filters": filters,

        "patient_summary": patient_summary,
        "encounter_summary": encounter_summary,

        "average_visit_duration_display": format_duration(
            average_duration,
        ),

        "encounter_trend": trend,
        "encounter_status_breakdown": status_breakdown,

        "recent_encounters": recent_encounters(
            **filters,
        ),

        "encounter_type_choices": (
            Encounter.EncounterType.choices
        ),

        "encounter_status_choices": (
            Encounter.EncounterStatus.choices
        ),
    }