"""
Analytics Views

File:
apps/analytics/views.py

Purpose:
- Render complete Analytics pages for standard requests.
- Render workspace partials for HTMX requests.
- Maintain active primary and Analytics navigation state.
"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from apps.core.htmx import is_htmx

from .services import (
    analytics_dashboard_context,
    quality_analytics_context,
)


# ============================================================
# SHARED NAVIGATION CONTEXT
# ============================================================

def analytics_navigation_context(
    *,
    module: str,
) -> dict:
    """
    Return navigation state shared by Analytics pages.
    """

    return {
        "active_primary_nav": "analytics",
        "active_secondary_nav": "analytics",
        "active_analytics_module": module,
    }


# ============================================================
# SHARED ANALYTICS RENDERER
# ============================================================

def render_analytics_page(
    request: HttpRequest,
    *,
    module: str,
    full_template: str,
    partial_template: str,
    context_builder=analytics_dashboard_context,
) -> HttpResponse:
    """
    Render a complete page or an HTMX workspace partial.

    Normal request:
        Render the complete page and application shell.

    HTMX request:
        Render only the Analytics workspace content.
    """

    context = {
        **analytics_navigation_context(
            module=module,
        ),
        **context_builder(
            request,
        ),
    }

    template_name = (
        partial_template
        if is_htmx(request)
        else full_template
    )

    response = render(
        request,
        template_name,
        context,
    )

    response["Vary"] = "HX-Request"

    return response


# ============================================================
# ANALYTICS DASHBOARD
# ============================================================

@login_required
def analytics_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="dashboard",
        full_template="analytics/index.html",
        partial_template=(
            "analytics/partials/dashboard_content.html"
        ),
    )


# ============================================================
# CLINICAL ANALYTICS
# ============================================================

@login_required
def clinical_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="clinical",
        full_template="analytics/clinical_dashboard.html",
        partial_template=(
            "analytics/partials/clinical_content.html"
        ),
    )


# ============================================================
# NURSING ANALYTICS
# ============================================================

@login_required
def nursing_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="nursing",
        full_template="analytics/nursing_dashboard.html",
        partial_template=(
            "analytics/partials/nursing_content.html"
        ),
    )


# ============================================================
# OPERATIONAL ANALYTICS
# ============================================================

@login_required
def operations_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="operations",
        full_template="analytics/operations_dashboard.html",
        partial_template=(
            "analytics/partials/operations_content.html"
        ),
    )


# ============================================================
# QUALITY ANALYTICS
# ============================================================

@login_required
def quality_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="quality",
        full_template="analytics/quality_dashboard.html",
        partial_template=(
            "analytics/partials/quality_content.html"
        ),
        context_builder=quality_analytics_context,
    )


# ============================================================
# POPULATION HEALTH
# ============================================================

@login_required
def surveillance_dashboard(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="population",
        full_template="analytics/surveillance_dashboard.html",
        partial_template=(
            "analytics/partials/surveillance_content.html"
        ),
    )


# ============================================================
# PATIENT OUTCOMES
# ============================================================

@login_required
def patient_outcomes(
    request: HttpRequest,
) -> HttpResponse:
    return render_analytics_page(
        request,
        module="patient-outcomes",
        full_template="analytics/patient_outcomes.html",
        partial_template=(
            "analytics/partials/outcomes_content.html"
        ),
    )