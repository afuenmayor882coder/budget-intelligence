"""Comparison detector: vs previous period, vs averages."""
from datetime import datetime
from services.narrative.insight import Insight, magnitude_label


def detect_period_comparisons(conn) -> list[Insight]:
    """Detect month-over-month spending/income changes."""
    insights = []
    now = datetime.now()
    year, month = now.year, now.month

    # Previous month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1

    def get_period(y, m):
        start = f"{y:04d}-{m:02d}-01"
        end = f"{y+1:04d}-01-01" if m == 12 else f"{y:04d}-{m+1:02d}-01"
        row = conn.execute(
            """SELECT
                 SUM(CASE WHEN tipo='Gasto' THEN ABS(monto_usd) ELSE 0 END) as expenses,
                 SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd) ELSE 0 END) as income
               FROM transactions WHERE fecha >= ? AND fecha < ?""",
            (start, end),
        ).fetchone()
        return row["expenses"] or 0, row["income"] or 0

    curr_exp, curr_inc = get_period(year, month)
    prev_exp, prev_inc = get_period(prev_year, prev_month)

    # Spending comparison
    if prev_exp > 0 and curr_exp > 0:
        exp_change_pct = (curr_exp - prev_exp) / prev_exp * 100
        direction = "up" if exp_change_pct > 0 else "down"
        mag = magnitude_label(abs(exp_change_pct))
        sev = "warning" if exp_change_pct > 25 else "notice" if abs(exp_change_pct) > 10 else "info"
        i = Insight(
            id="compare_expenses_mom",
            detector="comparison",
            subject="Monthly Expenses",
            type="compare",
            direction=direction,
            magnitude=mag,
            severity=sev,
            evidence={
                "current_usd": round(curr_exp, 2),
                "previous_usd": round(prev_exp, 2),
                "change_pct": round(exp_change_pct, 1),
                "current_period": f"{year}-{month:02d}",
                "previous_period": f"{prev_year}-{prev_month:02d}",
            },
            time_window="month_over_month",
            tags=["dashboard", "spending"],
        )
        i.compute_priority(magnitude_zscore=min(1.0, abs(exp_change_pct) / 25))
        insights.append(i)

    # Income comparison
    if prev_inc > 0 and curr_inc > 0:
        inc_change_pct = (curr_inc - prev_inc) / prev_inc * 100
        direction_i = "up" if inc_change_pct > 0 else "down"
        sev_i = "warning" if inc_change_pct < -15 else "notice" if abs(inc_change_pct) > 10 else "info"
        i2 = Insight(
            id="compare_income_mom",
            detector="comparison",
            subject="Monthly Income",
            type="compare",
            direction=direction_i,
            magnitude=magnitude_label(abs(inc_change_pct)),
            severity=sev_i,
            evidence={
                "current_usd": round(curr_inc, 2),
                "previous_usd": round(prev_inc, 2),
                "change_pct": round(inc_change_pct, 1),
            },
            time_window="month_over_month",
            tags=["dashboard", "income"],
        )
        i2.compute_priority(magnitude_zscore=min(1.0, abs(inc_change_pct) / 20))
        insights.append(i2)

    # Category-level comparisons
    cat_rows = conn.execute(
        """SELECT categoria,
             SUM(CASE WHEN fecha >= ? AND fecha < ? THEN ABS(monto_usd) ELSE 0 END) as curr,
             SUM(CASE WHEN fecha >= ? AND fecha < ? THEN ABS(monto_usd) ELSE 0 END) as prev
           FROM transactions
           WHERE tipo='Gasto' AND categoria IS NOT NULL
           GROUP BY categoria""",
        (
            f"{year:04d}-{month:02d}-01",
            f"{year+1:04d}-01-01" if month == 12 else f"{year:04d}-{month+1:02d}-01",
            f"{prev_year:04d}-{prev_month:02d}-01",
            f"{prev_year+1:04d}-01-01" if prev_month == 12 else f"{prev_year:04d}-{prev_month+1:02d}-01",
        ),
    ).fetchall()

    for r in cat_rows:
        if r["prev"] > 0 and r["curr"] > 0:
            pct = (r["curr"] - r["prev"]) / r["prev"] * 100
            if abs(pct) > 20:
                direction_c = "up" if pct > 0 else "down"
                sev_c = "warning" if pct > 30 else "notice"
                cat_i = Insight(
                    id=f"compare_cat_{r['categoria'].lower().replace(' ', '_')}_mom",
                    detector="comparison",
                    subject=f"{r['categoria']} Spending",
                    type="compare",
                    direction=direction_c,
                    magnitude=magnitude_label(abs(pct)),
                    severity=sev_c,
                    evidence={
                        "category": r["categoria"],
                        "current_usd": round(r["curr"], 2),
                        "previous_usd": round(r["prev"], 2),
                        "change_pct": round(pct, 1),
                    },
                    time_window="month_over_month",
                    tags=["spending"],
                )
                cat_i.compute_priority(magnitude_zscore=min(1.0, abs(pct) / 30))
                insights.append(cat_i)

    return insights
