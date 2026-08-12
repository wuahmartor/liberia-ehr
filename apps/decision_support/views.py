from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.nursing.models import NursingFallRiskAssessment

from .forms import AlertActionForm, ClinicalRuleForm
from .models import ClinicalAlert, ClinicalRule, RiskAssessment


def context(section):
    return {"active_primary_nav": "ai-cds", "active_ai_module": section}


@login_required
def dashboard(request):
    return render(
        request,
        "decision_support/dashboard.html",
        context("assistant")
        | {
            "open_count": ClinicalAlert.objects.filter(status="open").count(),
            "critical_count": ClinicalAlert.objects.filter(
                status="open", rule__severity="critical"
            ).count(),
            "rule_count": ClinicalRule.objects.filter(is_active=True).count(),
            "recent_alerts": ClinicalAlert.objects.select_related("patient", "rule")[
                :8
            ],
        },
    )


@login_required
def alerts(request):
    qs = ClinicalAlert.objects.select_related(
        "patient", "encounter", "rule", "acted_by"
    )
    status = request.GET.get("status", "open")
    if status != "all":
        qs = qs.filter(status=status)
    template = (
        "decision_support/partials/alert_list.html"
        if request.headers.get("HX-Request") == "true"
        else "decision_support/alerts.html"
    )
    return render(
        request, template, context("alerts") | {"alerts": qs, "status": status}
    )


@login_required
def alert_detail(request, alert_id):
    alert = get_object_or_404(
        ClinicalAlert.objects.select_related(
            "patient", "encounter", "rule", "acted_by"
        ),
        pk=alert_id,
    )
    return render(
        request,
        "decision_support/alert_detail.html",
        context("alerts") | {"alert": alert, "form": AlertActionForm()},
    )


@login_required
def alert_action(request, alert_id):
    alert = get_object_or_404(ClinicalAlert, pk=alert_id)
    form = AlertActionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        alert.status = form.cleaned_data["action"]
        alert.action_note = form.cleaned_data["note"].strip()
        alert.acted_by = request.user
        alert.acted_at = timezone.now()
        alert.save(update_fields=["status", "action_note", "acted_by", "acted_at"])
        messages.success(request, "Clinical alert action recorded.")
        return redirect("decision_support:alerts")
    return render(
        request,
        "decision_support/alert_detail.html",
        context("alerts") | {"alert": alert, "form": form},
    )


@login_required
def recommendations(request):
    return render(
        request,
        "decision_support/recommendations.html",
        context("recommendations")
        | {
            "alerts": ClinicalAlert.objects.filter(
                status__in=("open", "acknowledged")
            ).select_related("patient", "rule")
        },
    )


@login_required
def risk_scores(request):
    return render(
        request,
        "decision_support/risk.html",
        context("risk")
        | {
            "scores": RiskAssessment.objects.select_related("patient", "calculated_by")[
                :100
            ],
            "fall_risk_comparisons": NursingFallRiskAssessment.objects.select_related(
                "patient", "encounter", "recorded_by"
            )[:50],
        },
    )


@login_required
def rules(request):
    return render(
        request,
        "decision_support/rules.html",
        context("rules") | {"rules": ClinicalRule.objects.all()},
    )


@login_required
@user_passes_test(lambda u: u.is_staff)
def rule_form(request, rule_id=None):
    rule = get_object_or_404(ClinicalRule, pk=rule_id) if rule_id else None
    form = ClinicalRuleForm(request.POST or None, instance=rule)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if not item.pk:
            item.created_by = request.user
        item.save()
        messages.success(request, "Clinical decision rule saved.")
        return redirect("decision_support:rules")
    return render(
        request,
        "decision_support/rule_form.html",
        context("rules") | {"form": form, "rule": rule},
    )
