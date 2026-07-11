"""Correlation detector: personal spending vs macro variables."""
import hashlib

import numpy as np

from services.narrative.insight import Insight


def detect_correlations(conn) -> list[Insight]:
    """Find statistically meaningful personal-macro correlations."""
    from services.macro_impact import compute_macro_impact

    result = compute_macro_impact(conn)
    if "error" in result:
        return []

    insights = []
    for corr in result.get("correlations", []):
        r = corr.get("correlation", 0)
        if abs(r) < 0.5:
            continue

        strength = corr.get("strength", "moderate")
        insights.append(Insight(
            id=hashlib.md5(
                f"corr_{corr['category']}_{corr['macro_variable']}_{r}".encode()
            ).hexdigest()[:12],
            detector="correlation",
            subject=f"{corr['category']} vs {corr['macro_variable']}",
            type="correlation",
            direction="up" if r > 0 else "down",
            magnitude="large" if abs(r) > 0.7 else "notable",
            severity="notice" if abs(r) > 0.7 else "info",
            evidence={
                "category": corr["category"],
                "macro_variable": corr["macro_variable"],
                "correlation": round(r, 3),
                "strength": strength,
            },
            tags=["correlation", "macro", corr["category"].lower() if corr.get("category") else "spending"],
        ))

    for el in result.get("elasticities", []):
        e = el.get("ipc_elasticity", 0)
        if abs(e) < 0.3:
            continue
        insights.append(Insight(
            id=hashlib.md5(f"elast_{el['category']}_{e}".encode()).hexdigest()[:12],
            detector="correlation",
            subject=f"{el['category']} IPC exposure",
            type="correlation",
            direction="up" if e > 0 else "down",
            magnitude="large" if abs(e) > 0.8 else "notable",
            severity="warning" if abs(e) > 1.0 else "notice",
            evidence={
                "category": el["category"],
                "ipc_elasticity": round(e, 3),
                "interpretation": el.get("interpretation", ""),
            },
            tags=["correlation", "macro", "ipc", el["category"].lower()],
        ))

    return insights
