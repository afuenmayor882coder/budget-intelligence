"""Anomaly detector: outlier transactions and unusual spending patterns."""
import math
from datetime import datetime
from services.narrative.insight import Insight, magnitude_label


def detect_anomalies(conn) -> list[Insight]:
    """Detect anomalous transactions and spending spikes."""
    insights = []

    # Get last 90 days of transactions
    ninety_ago = (datetime.now().replace(day=1)).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT monto_usd, fecha, categoria, descripcion
           FROM transactions
           WHERE tipo='Gasto' AND fecha >= ? AND monto_usd IS NOT NULL
           ORDER BY ABS(monto_usd) DESC""",
        (ninety_ago,),
    ).fetchall()

    if len(rows) < 5:
        return insights

    amounts = [abs(r["monto_usd"]) for r in rows]
    mean = sum(amounts) / len(amounts)
    std = math.sqrt(sum((x - mean) ** 2 for x in amounts) / len(amounts))

    if std == 0:
        return insights

    # Find transactions > 3 std deviations above mean
    outliers = []
    for r in rows:
        z = (abs(r["monto_usd"]) - mean) / std
        if z > 2.5:
            outliers.append({
                "amount_usd": round(abs(r["monto_usd"]), 2),
                "fecha": r["fecha"],
                "categoria": r["categoria"],
                "descripcion": (r["descripcion"] or "")[:50],
                "z_score": round(z, 1),
            })

    if outliers:
        top_outlier = outliers[0]
        i = Insight(
            id="anomaly_large_transaction",
            detector="anomaly",
            subject="Large Transaction",
            type="anomaly",
            direction="up",
            magnitude=magnitude_label((top_outlier["amount_usd"] - mean) / mean * 100),
            severity="notice",
            evidence={
                "top_outlier": top_outlier,
                "all_outliers": outliers[:3],
                "mean_transaction_usd": round(mean, 2),
                "std_usd": round(std, 2),
            },
            time_window="last_90_days",
            tags=["spending", "dashboard"],
        )
        i.compute_priority(
            magnitude_zscore=min(1.0, top_outlier["z_score"] / 5),
            recency_weight=0.8,
        )
        insights.append(i)

    # Monthly spending spike: this month vs trailing average
    month_rows = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total
           FROM transactions
           WHERE tipo='Gasto'
           GROUP BY year, month
           ORDER BY year DESC, month DESC
           LIMIT 6"""
    ).fetchall()

    if len(month_rows) >= 3:
        this_month = month_rows[0]["total"] or 0
        prior = [r["total"] or 0 for r in month_rows[1:]]
        prior_mean = sum(prior) / len(prior)
        prior_std = math.sqrt(sum((x - prior_mean) ** 2 for x in prior) / len(prior)) if len(prior) > 1 else 0

        if prior_mean > 0 and prior_std > 0:
            z_month = (this_month - prior_mean) / prior_std
            if z_month > 1.5:
                pct_above = (this_month - prior_mean) / prior_mean * 100
                i2 = Insight(
                    id="anomaly_monthly_spike",
                    detector="anomaly",
                    subject="Monthly Spending Spike",
                    type="anomaly",
                    direction="up",
                    magnitude=magnitude_label(pct_above),
                    severity="warning" if z_month > 2.5 else "notice",
                    evidence={
                        "this_month_usd": round(this_month, 2),
                        "prior_avg_usd": round(prior_mean, 2),
                        "pct_above_avg": round(pct_above, 1),
                        "z_score": round(z_month, 1),
                    },
                    time_window="current_month",
                    tags=["spending", "dashboard"],
                )
                i2.compute_priority(magnitude_zscore=min(1.0, z_month / 3))
                insights.append(i2)

    return insights
