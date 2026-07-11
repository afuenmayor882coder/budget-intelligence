"""Milestone detector: positive events, achievements."""
from datetime import datetime
from services.narrative.insight import Insight


def detect_milestones(conn) -> list[Insight]:
    """Detect positive financial milestones."""
    insights = []
    now = datetime.now()
    year, month = now.year, now.month

    start = f"{year:04d}-{month:02d}-01"
    end = f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01"

    row = conn.execute(
        """SELECT
             SUM(CASE WHEN tipo='Gasto' THEN ABS(monto_usd) ELSE 0 END) as expenses,
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd) ELSE 0 END) as income
           FROM transactions WHERE fecha >= ? AND fecha < ?""",
        (start, end),
    ).fetchone()

    expenses = row["expenses"] or 0
    income = row["income"] or 0
    savings = income - expenses

    # Milestone: positive savings this month
    if savings > 0:
        savings_rate = savings / income * 100 if income > 0 else 0
        severity = "info"
        if savings_rate > 20:
            severity = "info"
            label = f"Strong {savings_rate:.0f}% savings rate this month"
        else:
            label = f"Positive savings this month"

        i = Insight(
            id="milestone_positive_savings",
            detector="milestone",
            subject="Monthly Savings",
            type="milestone",
            direction="up",
            magnitude="moderate",
            severity=severity,
            evidence={
                "savings_usd": round(savings, 2),
                "savings_rate_pct": round(savings_rate, 1),
                "income_usd": round(income, 2),
                "label": label,
            },
            time_window="current_month",
            tags=["dashboard"],
        )
        i.compute_priority(magnitude_zscore=min(1.0, savings_rate / 25), recency_weight=1.0)
        insights.append(i)

    # Milestone: runway > 90 days
    from services.calculations import compute_runway
    runway = compute_runway(conn)
    runway_days = runway.get("days_no_income", 0)

    if runway_days and runway_days > 90:
        level = "critical" if runway_days < 30 else "info"
        i2 = Insight(
            id="milestone_runway_healthy",
            detector="milestone",
            subject="Cash Runway",
            type="milestone",
            direction="up",
            magnitude="notable",
            severity="info",
            evidence={
                "runway_days": runway_days,
                "milestone_threshold": 90,
            },
            time_window="current",
            tags=["dashboard"],
        )
        i2.compute_priority(magnitude_zscore=min(1.0, runway_days / 365), recency_weight=0.7)
        insights.append(i2)

    # Milestone: first time uploading data
    txn_count = conn.execute("SELECT COUNT(*) as cnt FROM transactions").fetchone()["cnt"]
    if txn_count > 0 and txn_count <= 50:
        i3 = Insight(
            id="milestone_first_upload",
            detector="milestone",
            subject="First Data Upload",
            type="milestone",
            direction="up",
            magnitude="small",
            severity="info",
            evidence={"txn_count": txn_count},
            time_window="all_time",
            tags=["global", "upload"],
        )
        i3.compute_priority(magnitude_zscore=0.1, recency_weight=1.0)
        insights.append(i3)

    return insights
