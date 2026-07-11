"""Prioritizer: selects and orders insights for composition."""
from services.narrative.insight import Insight

SEVERITY_ORDER = {"critical": 4, "warning": 3, "notice": 2, "info": 1}


def prioritize(
    insights: list[Insight],
    context: str = "dashboard",
    max_count: int = 5,
    density: str = "normal",
) -> list[Insight]:
    """
    Filter and rank insights for a given context.

    density: concise (2-3) | normal (4-5) | detailed (6-8)
    """
    density_limits = {"concise": 3, "normal": 5, "detailed": 8}
    effective_limit = min(max_count, density_limits.get(density, 5))

    now_str = None
    try:
        from datetime import datetime
        now_str = datetime.now().isoformat()
    except Exception:
        pass

    # Filter: context relevance and not expired
    relevant = []
    for i in insights:
        if context in i.tags or "global" in i.tags:
            if not i.expires_at or (now_str and i.expires_at.isoformat() > now_str):
                relevant.append(i)

    # Sort: priority score (primary) then severity (secondary)
    relevant.sort(
        key=lambda x: (x.priority_score, SEVERITY_ORDER.get(x.severity, 0)),
        reverse=True,
    )

    # Diversity: don't stack same type
    selected = []
    type_counts: dict[str, int] = {}
    max_per_type = {"trend": 2, "compare": 2, "threshold": 2, "anomaly": 1,
                    "milestone": 1, "streak": 1, "risk": 3, "opportunity": 2,
                    "ranking": 1}

    for insight in relevant:
        if len(selected) >= effective_limit:
            break
        t = insight.type
        count = type_counts.get(t, 0)
        if count < max_per_type.get(t, 2):
            selected.append(insight)
            type_counts[t] = count + 1

    return selected
