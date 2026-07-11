"""Threshold breach detector."""
from datetime import datetime
from services.narrative.insight import Insight


def detect_thresholds(conn) -> list[Insight]:
    """Detect when key metrics cross important thresholds."""
    insights = []
    now = datetime.now()
    year, month = now.year, now.month
    start = f"{year:04d}-{month:02d}-01"
    end = f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01"

    # Get current month totals
    row = conn.execute(
        """SELECT
             SUM(CASE WHEN tipo='Gasto' THEN ABS(monto_usd) ELSE 0 END) as expenses,
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd) ELSE 0 END) as income
           FROM transactions WHERE fecha >= ? AND fecha < ?""",
        (start, end),
    ).fetchone()
    expenses = row["expenses"] or 0
    income = row["income"] or 0

    # Threshold 1: expenses > income (negative cash flow)
    if expenses > income and income > 0:
        savings_rate = (income - expenses) / income * 100
        i = Insight(
            id="threshold_negative_cashflow",
            detector="threshold",
            subject="Monthly Cash Flow",
            type="threshold",
            direction="down",
            magnitude="notable",
            severity="warning",
            evidence={
                "expenses_usd": round(expenses, 2),
                "income_usd": round(income, 2),
                "deficit_usd": round(expenses - income, 2),
                "savings_rate_pct": round(savings_rate, 1),
            },
            time_window="current_month",
            tags=["dashboard", "spending", "income"],
        )
        i.compute_priority(magnitude_zscore=min(1.0, (expenses - income) / max(income, 1)),
                          recency_weight=1.0)
        insights.append(i)

    # Threshold 2: savings rate < 10%
    elif income > 0:
        savings_rate = (income - expenses) / income * 100
        if 0 < savings_rate < 10:
            i2 = Insight(
                id="threshold_low_savings_rate",
                detector="threshold",
                subject="Savings Rate",
                type="threshold",
                direction="down",
                magnitude="moderate",
                severity="notice",
                evidence={
                    "savings_rate_pct": round(savings_rate, 1),
                    "threshold_pct": 10,
                },
                time_window="current_month",
                tags=["dashboard"],
            )
            i2.compute_priority(magnitude_zscore=0.4, recency_weight=0.9)
            insights.append(i2)

    # Threshold 3: Any category > 30% of total expenses
    if expenses > 0:
        cat_rows = conn.execute(
            """SELECT categoria, SUM(ABS(monto_usd)) as total
               FROM transactions
               WHERE tipo='Gasto' AND fecha >= ? AND fecha < ? AND categoria IS NOT NULL
               GROUP BY categoria
               HAVING total > ?""",
            (start, end, expenses * 0.3),
        ).fetchall()

        for r in cat_rows:
            pct = r["total"] / expenses * 100
            i3 = Insight(
                id=f"threshold_cat_dominance_{r['categoria'].lower().replace(' ', '_')}",
                detector="threshold",
                subject=f"{r['categoria']} Dominance",
                type="threshold",
                direction="up",
                magnitude="notable",
                severity="notice",
                evidence={
                    "category": r["categoria"],
                    "amount_usd": round(r["total"], 2),
                    "pct_of_expenses": round(pct, 1),
                    "threshold_pct": 30,
                },
                time_window="current_month",
                tags=["spending"],
            )
            i3.compute_priority(magnitude_zscore=min(1.0, (pct - 30) / 20), recency_weight=0.8)
            insights.append(i3)

    # Threshold 4: subscription creep > $50/month
    binance_rate_row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    binance_rate = binance_rate_row["tasa_binance"] if binance_rate_row else 700.0

    subs = conn.execute(
        "SELECT amount, currency, frequency FROM subscriptions WHERE active=1"
    ).fetchall()
    monthly_subs = 0.0
    for s in subs:
        amt = s["amount"]
        if s["frequency"] == "annual":
            amt /= 12
        elif s["frequency"] == "quarterly":
            amt /= 3
        if s["currency"] == "VES":
            amt /= binance_rate
        monthly_subs += amt

    if monthly_subs > 50:
        i4 = Insight(
            id="threshold_subscription_bloat",
            detector="threshold",
            subject="Subscription Total",
            type="threshold",
            direction="up",
            magnitude="notable",
            severity="notice",
            evidence={
                "monthly_subs_usd": round(monthly_subs, 2),
                "threshold_usd": 50,
            },
            time_window="current",
            tags=["subscriptions", "dashboard"],
        )
        i4.compute_priority(magnitude_zscore=min(1.0, (monthly_subs - 50) / 50))
        insights.append(i4)

    return insights
