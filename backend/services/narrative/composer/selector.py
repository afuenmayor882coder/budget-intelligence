"""Template selector: picks the right template for each insight."""
from services.narrative.insight import Insight

TEMPLATE_MAP = {
    # (type, subject_keyword): template_path
    ("trend", "spending"): "spending/monthly_summary.j2",
    ("trend", "category"): "spending/category_analysis.j2",
    ("compare", "expenses"): "spending/monthly_summary.j2",
    ("compare", "income"): "income/income_stability.j2",
    ("compare", "category"): "spending/category_analysis.j2",
    ("threshold", "cashflow"): "runway/days_to_zero.j2",
    ("threshold", "savings"): "spending/monthly_summary.j2",
    ("threshold", "category"): "spending/category_analysis.j2",
    ("threshold", "subscription"): "subscriptions/subscription_creep.j2",
    ("anomaly", "transaction"): "spending/outlier_transaction.j2",
    ("anomaly", "spending"): "spending/monthly_summary.j2",
    ("milestone", "savings"): "spending/monthly_summary.j2",
    ("milestone", "runway"): "runway/days_to_zero.j2",
    ("milestone", "upload"): "meta/import_summary.j2",
    ("streak", "overspend"): "spending/monthly_summary.j2",
    ("streak", "saving"): "spending/monthly_summary.j2",
    ("streak", "spending"): "spending/monthly_summary.j2",
    ("risk", "runway"): "runway/days_to_zero.j2",
    ("risk", "burn"): "runway/burn_rate_analysis.j2",
    ("risk", "fx"): "macro/fx_gap_analysis.j2",
    ("risk", "income"): "income/income_stability.j2",
    ("opportunity", "subscription"): "subscriptions/cancellation_impact.j2",
    ("opportunity", "category"): "spending/category_analysis.j2",
    ("ranking", ""): "spending/category_analysis.j2",
    ("forecast", ""): "forecast/ensemble_summary.j2",
    ("diagnostic", ""): "forecast/model_winner.j2",
    ("correlation", ""): "macro/fx_gap_analysis.j2",
}

FALLBACK_TEMPLATES = {
    "trend": "spending/monthly_summary.j2",
    "compare": "spending/monthly_summary.j2",
    "threshold": "spending/monthly_summary.j2",
    "anomaly": "spending/outlier_transaction.j2",
    "milestone": "meta/import_summary.j2",
    "streak": "spending/monthly_summary.j2",
    "risk": "runway/days_to_zero.j2",
    "opportunity": "subscriptions/cancellation_impact.j2",
    "ranking": "spending/category_analysis.j2",
    "forecast": "forecast/ensemble_summary.j2",
    "diagnostic": "forecast/model_winner.j2",
    "correlation": "macro/fx_gap_analysis.j2",
}


def select_template(insight: Insight) -> str:
    """Select the most appropriate template for an insight."""
    subject_lower = insight.subject.lower()

    # Try specific subject keyword match
    for keyword in ["spending", "income", "category", "runway", "cashflow",
                    "subscription", "transaction", "burn", "fx", "upload",
                    "savings", "overspend", "saving", "salary"]:
        if keyword in subject_lower:
            key = (insight.type, keyword)
            if key in TEMPLATE_MAP:
                return TEMPLATE_MAP[key]

    # Fallback to type-only
    return FALLBACK_TEMPLATES.get(insight.type, "spending/monthly_summary.j2")
