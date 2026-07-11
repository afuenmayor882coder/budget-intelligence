"""Trend detector: rising/falling patterns using linear regression."""
import math
from datetime import datetime, timedelta
from typing import Any

from services.narrative.insight import Insight, magnitude_label


def _linear_trend(values: list[float]) -> tuple[float, float]:
    """Returns (slope_per_period, r_squared)."""
    n = len(values)
    if n < 2:
        return 0.0, 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    ss_xy = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    ss_xx = sum((i - x_mean) ** 2 for i in range(n))
    ss_yy = sum((v - y_mean) ** 2 for v in values)
    if ss_xx == 0:
        return 0.0, 0.0
    slope = ss_xy / ss_xx
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0.0
    return slope, r_squared


def detect_spending_trends(conn) -> list[Insight]:
    """Detect spending trends across all categories."""
    insights = []

    # Monthly totals, last 6 months
    rows = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total_usd
           FROM transactions
           WHERE tipo='Gasto'
           GROUP BY year, month
           ORDER BY year, month
           LIMIT 6"""
    ).fetchall()

    if len(rows) < 3:
        return insights

    totals = [r["total_usd"] for r in rows]
    slope, r2 = _linear_trend(totals)
    mean_spend = sum(totals) / len(totals)

    if mean_spend > 0 and r2 > 0.5:
        monthly_pct = slope / mean_spend * 100
        direction = "up" if slope > 0 else "down"
        mag = magnitude_label(abs(monthly_pct))
        severity = "warning" if monthly_pct > 15 else "notice" if monthly_pct > 5 else "info"

        insight = Insight(
            id="trend_total_spending",
            detector="trend",
            subject="Total Spending",
            type="trend",
            direction=direction,
            magnitude=mag,
            severity=severity,
            evidence={
                "slope_usd_per_month": round(slope, 2),
                "monthly_change_pct": round(monthly_pct, 1),
                "r_squared": round(r2, 3),
                "recent_values": [round(v, 2) for v in totals],
                "mean_spend_usd": round(mean_spend, 2),
            },
            time_window="last_6_months",
            tags=["dashboard", "spending"],
        )
        insight.compute_priority(
            magnitude_zscore=min(1.0, abs(monthly_pct) / 30),
            recency_weight=1.0,
        )
        insights.append(insight)

    # Category-level trends
    cat_rows = conn.execute(
        """SELECT categoria,
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total_usd
           FROM transactions
           WHERE tipo='Gasto' AND categoria IS NOT NULL
           GROUP BY categoria, year, month
           ORDER BY categoria, year, month"""
    ).fetchall()

    # Group by category
    cat_data: dict[str, list] = {}
    for r in cat_rows:
        cat_data.setdefault(r["categoria"], []).append(r["total_usd"])

    for cat, values in cat_data.items():
        if len(values) < 3:
            continue
        slope_c, r2_c = _linear_trend(values[-6:])
        mean_c = sum(values[-6:]) / len(values[-6:])
        if mean_c > 0 and r2_c > 0.6:
            monthly_pct_c = slope_c / mean_c * 100
            if abs(monthly_pct_c) > 10:
                direction_c = "up" if slope_c > 0 else "down"
                mag_c = magnitude_label(abs(monthly_pct_c))
                sev_c = "warning" if monthly_pct_c > 25 else "notice"
                i = Insight(
                    id=f"trend_cat_{cat.lower().replace(' ', '_')}",
                    detector="trend",
                    subject=f"{cat} Spending",
                    type="trend",
                    direction=direction_c,
                    magnitude=mag_c,
                    severity=sev_c,
                    evidence={
                        "category": cat,
                        "slope_usd_per_month": round(slope_c, 2),
                        "monthly_change_pct": round(monthly_pct_c, 1),
                        "mean_monthly_usd": round(mean_c, 2),
                    },
                    time_window="last_6_months",
                    tags=["spending", "dashboard"],
                )
                i.compute_priority(
                    magnitude_zscore=min(1.0, abs(monthly_pct_c) / 30),
                    recency_weight=0.9,
                )
                insights.append(i)

    return insights
