"""Streak detector: consecutive-period patterns."""
from services.narrative.insight import Insight


def detect_streaks(conn) -> list[Insight]:
    """Detect multi-period streaks in spending/saving behavior."""
    insights = []

    monthly = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(CASE WHEN tipo='Gasto' THEN ABS(monto_usd) ELSE 0 END) as expenses,
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd) ELSE 0 END) as income
           FROM transactions
           WHERE tipo IN ('Gasto', 'Ingreso')
           GROUP BY year, month
           ORDER BY year, month"""
    ).fetchall()

    if len(monthly) < 3:
        return insights

    # Overspending streak (expenses > income consecutively)
    overspend_streak = 0
    savings_streak = 0

    for r in reversed(monthly):
        exp = r["expenses"] or 0
        inc = r["income"] or 0
        if exp > inc and inc > 0:
            overspend_streak += 1
            savings_streak = 0
        elif inc > exp and inc > 0:
            savings_streak += 1
            overspend_streak = 0
        else:
            break

    if overspend_streak >= 3:
        i = Insight(
            id="streak_overspending",
            detector="streak",
            subject="Overspending Streak",
            type="streak",
            direction="up",
            magnitude="notable",
            severity="warning",
            evidence={
                "consecutive_months": overspend_streak,
                "streak_type": "overspending",
            },
            time_window="last_months",
            tags=["dashboard", "spending"],
        )
        i.compute_priority(
            magnitude_zscore=min(1.0, overspend_streak / 6),
            recency_weight=1.0,
        )
        insights.append(i)
    elif savings_streak >= 2:
        i2 = Insight(
            id="streak_saving",
            detector="streak",
            subject="Saving Streak",
            type="streak",
            direction="up",
            magnitude="moderate",
            severity="info",
            evidence={
                "consecutive_months": savings_streak,
                "streak_type": "positive_savings",
            },
            time_window="last_months",
            tags=["dashboard"],
        )
        i2.compute_priority(
            magnitude_zscore=min(1.0, savings_streak / 6),
            recency_weight=1.0,
        )
        insights.append(i2)

    # Spending increase streak
    expense_values = [r["expenses"] or 0 for r in monthly[-4:]]
    if len(expense_values) >= 3:
        inc_streak = 0
        for j in range(1, len(expense_values)):
            if expense_values[j] > expense_values[j-1]:
                inc_streak += 1
            else:
                break
        if inc_streak >= 3:
            i3 = Insight(
                id="streak_spending_increasing",
                detector="streak",
                subject="Spending Trend",
                type="streak",
                direction="up",
                magnitude="notable",
                severity="notice",
                evidence={
                    "consecutive_months_increasing": inc_streak,
                    "recent_values": [round(v, 2) for v in expense_values],
                },
                time_window="last_months",
                tags=["spending", "dashboard"],
            )
            i3.compute_priority(magnitude_zscore=min(1.0, inc_streak / 4), recency_weight=0.9)
            insights.append(i3)

    return insights
