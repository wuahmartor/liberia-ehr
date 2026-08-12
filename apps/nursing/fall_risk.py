"""Transparent fall-risk comparison logic for nursing decision support.

The comparison models are development models and are not clinically validated.
They must be replaced by locally trained, independently validated artifacts before
clinical production use. Morse scoring remains directly inspectable.
"""

from __future__ import annotations

import math
from decimal import Decimal

from .models import NursingFallRiskAssessment

MORSE_VERSION = "Morse Fall Scale"
LOGISTIC_VERSION = "Liberia-EHR logistic comparison 0.1-unvalidated"
XGBOOST_VERSION = "Liberia-EHR boosted-tree comparison 0.1-unvalidated"


def risk_level(value: float, *, morse: bool = False) -> str:
    if morse:
        if value >= 45:
            return NursingFallRiskAssessment.RiskLevel.HIGH
        if value >= 25:
            return NursingFallRiskAssessment.RiskLevel.MODERATE
        return NursingFallRiskAssessment.RiskLevel.LOW
    if value >= 0.65:
        return NursingFallRiskAssessment.RiskLevel.HIGH
    if value >= 0.35:
        return NursingFallRiskAssessment.RiskLevel.MODERATE
    return NursingFallRiskAssessment.RiskLevel.LOW


def calculate_morse(data: dict) -> int:
    aid = {"none": 0, "crutches": 15, "furniture": 30}
    gait = {"normal": 0, "weak": 10, "impaired": 20}
    return (
        (25 if data.get("history_of_falling") else 0)
        + (15 if data.get("secondary_diagnosis") else 0)
        + aid[data.get("ambulatory_aid", "none")]
        + (20 if data.get("iv_or_heparin_lock") else 0)
        + gait[data.get("gait", "normal")]
        + (15 if data.get("mental_status") == "overconfident" else 0)
    )


def logistic_probability(data: dict) -> float:
    """Versioned local comparison equation; not a validated clinical model."""
    logit = -3.15
    logit += 1.05 if data.get("history_of_falling") else 0
    logit += 0.45 if data.get("secondary_diagnosis") else 0
    logit += {"none": 0, "crutches": 0.55, "furniture": 1.0}.get(
        data.get("ambulatory_aid"), 0
    )
    logit += 0.4 if data.get("iv_or_heparin_lock") else 0
    logit += {"normal": 0, "weak": 0.65, "impaired": 1.2}.get(data.get("gait"), 0)
    logit += 0.85 if data.get("mental_status") == "overconfident" else 0
    logit += 0.55 if data.get("sedating_medication") else 0
    logit += 0.55 if data.get("dizziness_or_hypotension") else 0
    logit += 0.45 if data.get("toileting_assistance") else 0
    return 1 / (1 + math.exp(-logit))


def boosted_tree_probability(data: dict) -> float:
    """Small transparent boosted-tree comparator; development use only."""
    score = -1.65
    if data.get("history_of_falling"):
        score += 0.85
    if data.get("gait") == "impaired":
        score += 1.0
    elif data.get("gait") == "weak":
        score += 0.45
    if data.get("mental_status") == "overconfident":
        score += 0.75
    if data.get("ambulatory_aid") == "furniture":
        score += 0.7
    if data.get("sedating_medication") and data.get("dizziness_or_hypotension"):
        score += 0.9
    elif data.get("sedating_medication") or data.get("dizziness_or_hypotension"):
        score += 0.4
    if data.get("toileting_assistance") and data.get("iv_or_heparin_lock"):
        score += 0.55
    if data.get("secondary_diagnosis"):
        score += 0.25
    return 1 / (1 + math.exp(-score))


def score_assessment(cleaned_data: dict) -> dict:
    morse = calculate_morse(cleaned_data)
    logistic = logistic_probability(cleaned_data)
    boosted = boosted_tree_probability(cleaned_data)
    levels = [
        risk_level(morse, morse=True),
        risk_level(logistic),
        risk_level(boosted),
    ]
    rank = {"low": 0, "moderate": 1, "high": 2}
    overall = max(levels, key=rank.get)
    return {
        "morse_score": morse,
        "morse_level": levels[0],
        "logistic_probability": Decimal(f"{logistic:.4f}"),
        "logistic_level": levels[1],
        "xgboost_probability": Decimal(f"{boosted:.4f}"),
        "xgboost_level": levels[2],
        "overall_level": overall,
        "model_comparison": {
            "morse": {"version": MORSE_VERSION, "score": morse, "level": levels[0]},
            "logistic": {
                "version": LOGISTIC_VERSION,
                "probability": round(logistic, 4),
                "level": levels[1],
                "validated": False,
            },
            "xgboost": {
                "version": XGBOOST_VERSION,
                "probability": round(boosted, 4),
                "level": levels[2],
                "validated": False,
            },
            "disagreement": len(set(levels)) > 1,
        },
    }
