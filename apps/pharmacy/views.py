from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def pharmacy_context(section: str) -> dict:
    return {
        "active_primary_nav": "clinical",
        "active_clinical_module": "pharmacy",
        "active_clinical_section": section,
    }


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/dashboard.html",
        pharmacy_context("dashboard"),
    )


@login_required
def queue(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/queue.html",
        pharmacy_context("queue"),
    )


@login_required
def pending_review(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/pending_review.html",
        pharmacy_context("pending-review"),
    )


@login_required
def verified(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/verified.html",
        pharmacy_context("verified"),
    )


@login_required
def dispensing(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/dispensing.html",
        pharmacy_context("dispensing"),
    )


@login_required
def inventory(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/inventory.html",
        pharmacy_context("inventory"),
    )


@login_required
def medication_catalog(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/medication_catalog.html",
        pharmacy_context("medication-catalog"),
    )


@login_required
def interactions(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/interactions.html",
        pharmacy_context("interactions"),
    )


@login_required
def rejected(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "pharmacy/rejected.html",
        pharmacy_context("rejected"),
    )