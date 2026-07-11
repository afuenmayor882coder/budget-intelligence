"""Opportunity detector: savings and optimization chances."""
from services.narrative.insight import Insight


def detect_opportunities(conn) -> list[Insight]:
    """Detect optimization opportunities."""
    insights = []

    binance_row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    binance_rate = binance_row["tasa_binance"] if binance_row else 700.0

    # Opportunity 1: non-essential high-cost subscriptions
    subs = conn.execute(
        "SELECT id, name, amount, currency, frequency, essential FROM subscriptions WHERE active=1"
    ).fetchall()

    non_essential_usd = 0.0
    top_cancel = []
    for s in subs:
        amt = s["amount"]
        if s["frequency"] == "annual":
            amt /= 12
        elif s["frequency"] == "quarterly":
            amt /= 3
        if s["currency"] == "VES":
            amt /= binance_rate

        if not s["essential"] and amt > 10:
            non_essential_usd += amt
            top_cancel.append({"name": s["name"], "monthly_usd": round(amt, 2)})

    top_cancel.sort(key=lambda x: x["monthly_usd"], reverse=True)

    if non_essential_usd > 20:
        i = Insight(
            id="opportunity_cancel_subscriptions",
            detector="opportunity",
            subject="Non-Essential Subscriptions",
            type="opportunity",
            direction="down",
            magnitude="moderate",
            severity="notice",
            evidence={
                "non_essential_monthly_usd": round(non_essential_usd, 2),
                "annual_savings_usd": round(non_essential_usd * 12, 2),
                "top_candidates": top_cancel[:3],
            },
            time_window="current",
            tags=["subscriptions", "dashboard"],
        )
        i.compute_priority(magnitude_zscore=min(1.0, non_essential_usd / 60))
        insights.append(i)

    # Opportunity 2: spending reduction targets
    cat_rows = conn.execute(
        """SELECT categoria, AVG(ABS(monto_usd)) as avg_monthly
           FROM (
             SELECT categoria,
                    CAST(strftime('%Y', fecha) AS INTEGER) as year,
                    CAST(strftime('%m', fecha) AS INTEGER) as month,
                    SUM(ABS(monto_usd)) as monto_usd
             FROM transactions
             WHERE tipo='Gasto' AND categoria IS NOT NULL
             GROUP BY categoria, year, month
           ) GROUP BY categoria
           ORDER BY avg_monthly DESC
           LIMIT 5"""
    ).fetchall()

    if cat_rows:
        top_cat = dict(cat_rows[0])
        potential_10pct = top_cat["avg_monthly"] * 0.1
        i2 = Insight(
            id="opportunity_reduce_top_category",
            detector="opportunity",
            subject=f"Reduce {top_cat['categoria']}",
            type="opportunity",
            direction="down",
            magnitude="small",
            severity="info",
            evidence={
                "category": top_cat["categoria"],
                "avg_monthly_usd": round(top_cat["avg_monthly"], 2),
                "potential_savings_10pct": round(potential_10pct, 2),
                "annual_savings": round(potential_10pct * 12, 2),
            },
            time_window="trailing_average",
            tags=["spending"],
        )
        i2.compute_priority(magnitude_zscore=0.3, recency_weight=0.6)
        insights.append(i2)

    return insights
