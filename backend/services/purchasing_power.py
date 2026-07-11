"""Purchasing power depreciation engine — 3 lenses."""
from datetime import datetime
from typing import Any


def _get_binance_rate(conn) -> float:
    row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    return row["tasa_binance"] if row and row["tasa_binance"] else 700.0


def _get_monthly_income_usd(conn) -> float:
    binance_rate = _get_binance_rate(conn)
    cursor = conn.execute("SELECT amount, currency, frequency FROM income_sources WHERE active=1")
    total = 0.0
    for s in cursor.fetchall():
        amt = s["amount"]
        if s["frequency"] == "biweekly":
            amt *= 2.17
        elif s["frequency"] == "weekly":
            amt *= 4.33
        elif s["frequency"] == "annual":
            amt /= 12
        if s["currency"] == "VES":
            amt /= binance_rate
        total += amt
    return total


def compute_purchasing_power(conn) -> dict[str, Any]:
    """
    Three depreciation lenses:
    1. spending_depreciation  — cost of the user's actual spending basket over time
    2. subscription_depreciation — FX-driven cost growth of USD-denominated subscriptions
    3. basket_depreciation    — Cesta Basica cost vs income
    """
    binance_rate = _get_binance_rate(conn)
    monthly_income_usd = _get_monthly_income_usd(conn)

    # ── Lens 1: Personal spending depreciation ──────────────────────────────
    # Compare user's real spending cost per month over time (normalized to USD)
    spending_rows = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total_usd
           FROM transactions
           WHERE tipo='Gasto'
           GROUP BY year, month
           ORDER BY year, month
           LIMIT 24"""
    ).fetchall()

    spending_series = [
        {"year": r["year"], "month": r["month"], "total_usd": round(r["total_usd"], 2)}
        for r in spending_rows
    ]

    # Compute personal inflation: how much has the spending basket changed?
    spending_depreciation = None
    personal_inflation_6m = None
    if len(spending_series) >= 2:
        recent = spending_series[-1]["total_usd"]
        baseline = spending_series[0]["total_usd"]
        if baseline > 0:
            spending_depreciation = round((recent - baseline) / baseline * 100, 1)

    if len(spending_series) >= 6:
        recent = spending_series[-1]["total_usd"]
        six_months_ago = spending_series[-6]["total_usd"]
        if six_months_ago > 0:
            personal_inflation_6m = round((recent - six_months_ago) / six_months_ago * 100, 1)

    # ── Lens 2: Subscription FX depreciation ────────────────────────────────
    # How much more does the income need to cover USD subscriptions as FX weakens?
    subs = conn.execute(
        "SELECT name, amount, currency, frequency FROM subscriptions WHERE active=1"
    ).fetchall()

    monthly_subs_usd = 0.0
    usd_subs_count = 0
    for s in subs:
        amt = s["amount"]
        if s["frequency"] == "annual":
            amt /= 12
        elif s["frequency"] == "quarterly":
            amt /= 3
        if s["currency"] == "USD":
            monthly_subs_usd += amt
            usd_subs_count += 1
        elif s["currency"] == "VES":
            monthly_subs_usd += amt / binance_rate

    # Find historical rate to compare subscription burden
    rate_6m_ago = conn.execute(
        """SELECT tasa_binance FROM exchange_rates
           WHERE fecha <= date('now', '-6 months')
           ORDER BY fecha DESC LIMIT 1"""
    ).fetchone()

    sub_depreciation_6m = None
    if rate_6m_ago and rate_6m_ago["tasa_binance"] and monthly_income_usd > 0:
        # If income is in VES, USD subscriptions become relatively more expensive
        # as the VES weakens
        rate_now = binance_rate
        rate_then = rate_6m_ago["tasa_binance"]
        if rate_then > 0:
            fx_change_pct = (rate_now - rate_then) / rate_then * 100
            sub_depreciation_6m = round(fx_change_pct, 1)

    subs_pct_of_income = (
        round(monthly_subs_usd / monthly_income_usd * 100, 1)
        if monthly_income_usd > 0 else None
    )

    # ── Lens 3: Cesta Basica depreciation ───────────────────────────────────
    cesta_rows = conn.execute(
        "SELECT year, month, total_bs, total_usd FROM cesta_basica ORDER BY year, month"
    ).fetchall()

    cesta_series = []
    income_vs_cesta = []
    baskets_covered = None

    if cesta_rows:
        latest_cesta = dict(cesta_rows[-1])
        cesta_usd = latest_cesta.get("total_usd")
        cesta_bs = latest_cesta.get("total_bs")

        # If only BS value, convert to USD
        if cesta_usd is None and cesta_bs and binance_rate > 0:
            cesta_usd = cesta_bs / binance_rate

        if cesta_usd and monthly_income_usd > 0:
            baskets_covered = round(monthly_income_usd / cesta_usd, 2)

        for r in cesta_rows:
            cesta_usd_row = r["total_usd"]
            if not cesta_usd_row and r["total_bs"] and binance_rate > 0:
                cesta_usd_row = r["total_bs"] / binance_rate
            cesta_series.append({
                "year": r["year"],
                "month": r["month"],
                "total_usd": round(cesta_usd_row, 2) if cesta_usd_row else None,
                "total_bs": r["total_bs"],
            })
            if cesta_usd_row and monthly_income_usd > 0:
                income_vs_cesta.append({
                    "year": r["year"],
                    "month": r["month"],
                    "baskets_covered": round(monthly_income_usd / cesta_usd_row, 2),
                })

    # Cesta growth rate over tracked period
    basket_depreciation = None
    if len(cesta_series) >= 2:
        latest_v = cesta_series[-1]["total_usd"]
        first_v = cesta_series[0]["total_usd"]
        if first_v and latest_v and first_v > 0:
            basket_depreciation = round((latest_v - first_v) / first_v * 100, 1)

    # ── IPC-based real income tracker ───────────────────────────────────────
    ipc_rows = conn.execute(
        "SELECT year, month, indice, var_pct FROM macro_ipc ORDER BY year, month DESC LIMIT 24"
    ).fetchall()
    ipc_series = sorted([dict(r) for r in ipc_rows], key=lambda r: (r["year"], r["month"]))

    real_income_series = []
    if ipc_series and monthly_income_usd > 0:
        base_ipc = ipc_series[0]["indice"]
        if base_ipc:
            for r in ipc_series:
                if r["indice"]:
                    real_income = monthly_income_usd * (base_ipc / r["indice"])
                    real_income_series.append({
                        "year": r["year"],
                        "month": r["month"],
                        "nominal_income_usd": round(monthly_income_usd, 2),
                        "real_income_usd": round(real_income, 2),
                        "ipc_index": r["indice"],
                    })

    # ── Projections ──────────────────────────────────────────────────────────
    # Simple forward projection using last 3 months of IPC growth
    projected_3m = None
    projected_6m = None
    projected_12m = None

    if len(ipc_series) >= 3:
        recent_var = [r["var_pct"] for r in ipc_series[-3:] if r["var_pct"] is not None]
        if recent_var:
            avg_monthly_inflation = sum(recent_var) / len(recent_var) / 100

            if monthly_income_usd > 0 and avg_monthly_inflation > 0:
                projected_3m = round(monthly_income_usd / ((1 + avg_monthly_inflation) ** 3), 2)
                projected_6m = round(monthly_income_usd / ((1 + avg_monthly_inflation) ** 6), 2)
                projected_12m = round(monthly_income_usd / ((1 + avg_monthly_inflation) ** 12), 2)

    return {
        "monthly_income_usd": round(monthly_income_usd, 2),
        "current_binance_rate": binance_rate,

        "lens_spending": {
            "series": spending_series,
            "total_depreciation_pct": spending_depreciation,
            "depreciation_6m_pct": personal_inflation_6m,
            "description": "Your personal spending basket cost change over time",
        },

        "lens_subscriptions": {
            "monthly_subs_usd": round(monthly_subs_usd, 2),
            "usd_subs_count": usd_subs_count,
            "subs_pct_of_income": subs_pct_of_income,
            "fx_depreciation_6m_pct": sub_depreciation_6m,
            "description": "FX-driven cost growth of USD subscriptions as local currency weakens",
        },

        "lens_cesta_basica": {
            "series": cesta_series,
            "income_vs_cesta": income_vs_cesta,
            "baskets_covered": baskets_covered,
            "basket_depreciation_pct": basket_depreciation,
            "description": "Income vs official cost-of-living basket (CENDAS-FVM)",
        },

        "real_income_series": real_income_series,

        "projections": {
            "avg_monthly_inflation_pct": round(
                sum(r["var_pct"] for r in ipc_series[-3:] if r["var_pct"]) / 3, 1
            ) if len(ipc_series) >= 3 else None,
            "real_income_3m_usd": projected_3m,
            "real_income_6m_usd": projected_6m,
            "real_income_12m_usd": projected_12m,
        },
    }
