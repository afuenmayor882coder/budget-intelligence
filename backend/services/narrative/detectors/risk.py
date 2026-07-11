"""Risk detector: identifies concerning patterns."""
from datetime import datetime, timedelta
from services.narrative.insight import Insight


def detect_risks(conn) -> list[Insight]:
    """Detect financial risk patterns."""
    insights = []

    # Risk 1: runway < 30 days
    from services.calculations import compute_runway
    runway = compute_runway(conn)
    days = runway.get("days_no_income")
    if days is not None and days < 30:
        sev = "critical" if days < 14 else "warning"
        i = Insight(
            id="risk_low_runway",
            detector="risk",
            subject="Cash Runway",
            type="risk",
            direction="down",
            magnitude="extreme" if days < 7 else "large",
            severity=sev,
            evidence={
                "runway_days": days,
                "daily_burn_usd": runway.get("daily_burn_usd"),
                "balance_usd": runway.get("current_balance_usd"),
            },
            time_window="current",
            tags=["dashboard", "global"],
        )
        i.compute_priority(
            magnitude_zscore=1.0 - days / 30,
            recency_weight=1.0,
        )
        insights.append(i)

    # Risk 2: accelerating burn rate (last month > month before by > 20%)
    monthly = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total
           FROM transactions
           WHERE tipo='Gasto'
           GROUP BY year, month
           ORDER BY year DESC, month DESC
           LIMIT 3"""
    ).fetchall()

    if len(monthly) >= 2:
        m1 = monthly[0]["total"] or 0
        m2 = monthly[1]["total"] or 0
        if m2 > 0 and m1 > m2 * 1.2:
            pct = (m1 - m2) / m2 * 100
            i2 = Insight(
                id="risk_accelerating_burn",
                detector="risk",
                subject="Burn Rate",
                type="risk",
                direction="up",
                magnitude="notable",
                severity="warning",
                evidence={
                    "current_month_usd": round(m1, 2),
                    "prev_month_usd": round(m2, 2),
                    "increase_pct": round(pct, 1),
                },
                time_window="last_2_months",
                tags=["dashboard", "spending"],
            )
            i2.compute_priority(magnitude_zscore=min(1.0, pct / 40))
            insights.append(i2)

    # Risk 3: FX rate staleness
    rate_row = conn.execute(
        "SELECT fecha, tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    if rate_row:
        try:
            rate_date = datetime.strptime(rate_row["fecha"], "%Y-%m-%d")
            age_days = (datetime.now() - rate_date).days
            if age_days > 3:
                sev_fx = "warning" if age_days > 7 else "notice"
                i3 = Insight(
                    id="risk_stale_fx_data",
                    detector="risk",
                    subject="Exchange Rate Data",
                    type="risk",
                    direction="steady",
                    magnitude="moderate",
                    severity=sev_fx,
                    evidence={
                        "last_rate_date": rate_row["fecha"],
                        "age_days": age_days,
                        "last_binance_rate": rate_row["tasa_binance"],
                    },
                    time_window="current",
                    tags=["rates", "global"],
                )
                i3.compute_priority(magnitude_zscore=min(1.0, age_days / 14))
                insights.append(i3)
        except Exception:
            pass

    # Risk 4: Income concentration (only one income source)
    income_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM income_sources WHERE active=1"
    ).fetchone()["cnt"]
    if income_count == 1:
        i4 = Insight(
            id="risk_income_concentration",
            detector="risk",
            subject="Income Sources",
            type="risk",
            direction="steady",
            magnitude="moderate",
            severity="notice",
            evidence={"income_source_count": 1},
            time_window="current",
            tags=["income"],
        )
        i4.compute_priority(magnitude_zscore=0.3, recency_weight=0.5)
        insights.append(i4)

    return insights
