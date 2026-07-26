from django.shortcuts import render


TIME_RANGE_LABELS = {
    "24h": "Last 24 Hours",
    "48h": "Last 48 Hours",
    "7d": "Last 7 Days",
    "encounter": "Current Encounter",
}


def get_clinical_dashboard_context(request):
    time_range = request.GET.get("time_range", "24h")

    if time_range not in TIME_RANGE_LABELS:
        time_range = "24h"

    return {
        "time_range": time_range,
        "time_range_label": TIME_RANGE_LABELS[time_range],
        "vitals_status": "Stable",
        "lab_status": "2 Abnormal",
        "medication_status": "8 Active",
        "io_balance": "+250 mL",
        "pain_score": "3 / 10",
        "clinical_alerts": [
            {
                "icon": "▲",
                "icon_class": "text-amber-500",
                "title": "Possible Drug Interaction",
                "message": (
                    "Lisinopril may increase potassium levels when "
                    "combined with spironolactone."
                ),
                "action_label": "Review",
            },
            {
                "icon": "△",
                "icon_class": "text-red-500",
                "title": "Sepsis Risk Alert",
                "message": (
                    "Medium risk score. Monitor vital signs and "
                    "laboratory results."
                ),
                "action_label": "",
            },
        ],
    }


def clinical_overview(request):
    context = get_clinical_dashboard_context(request)

    context.update(
        {
            "active_primary_nav": "clinical",
            "active_secondary_nav": "patients",
        }
    )

    return render(
        request,
        "core/clinical_overview.html",
        context,
    )


def clinical_dashboard_partial(request):
    context = get_clinical_dashboard_context(request)

    return render(
        request,
        "core/partials/clinical_dashboard.html",
        context,
    )