"""Structured what-if scenario simulation engine (no LLM)."""
from datetime import datetime, timedelta
from typing import Any

from services.saving_planner import calculate_saving_plan
from services.calculations import compute_runway


def _get_binance_rate(conn) -> float:
    row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    return row["tasa_binance"] if row and row["tasa_binance"] else 700.0


def simulate_subscription_toggle(conn, toggled_sub_ids: list[int],
                                  toggle_state: bool = False) -> dict[str, Any]:
    """
    Simulate turning subscriptions on/off.
    toggle_state=False means cancel, True means re-activate.
    Returns impact on runway and monthly savings.
    """
    binance_rate = _get_binance_rate(conn)

    # Get all active subs and the toggled ones
    all_subs = conn.execute(
        "SELECT id, name, amount, currency, frequency, essential FROM subscriptions WHERE active=1"
    ).fetchall()
    toggled_subs = conn.execute(
        f"SELECT id, name, amount, currency, frequency FROM subscriptions WHERE id IN ({','.join(['?']*len(toggled_sub_ids))})",
        toggled_sub_ids,
    ).fetchall() if toggled_sub_ids else []

    def monthly_usd(s):
        amt = s["amount"]
        freq = s["frequency"] if hasattr(s, "__getitem__") else s.get("frequency", "monthly")
        cur = s["currency"] if hasattr(s, "__getitem__") else s.get("currency", "USD")
        if freq == "annual":
            amt /= 12
        elif freq == "quarterly":
            amt /= 3
        if cur == "VES":
            amt /= binance_rate
        return amt

    current_monthly_subs = sum(monthly_usd(s) for s in all_subs)

    # Impact of toggling
    toggled_monthly = sum(monthly_usd(s) for s in toggled_subs)
    new_monthly_subs = current_monthly_subs - toggled_monthly if not toggle_state else current_monthly_subs + toggled_monthly

    # Recompute runway with modified subs
    base_runway = compute_runway(conn)
    balance = base_runway.get("current_balance_usd", 0)
    daily_burn_base = base_runway.get("daily_burn_usd", 0)
    daily_income = base_runway.get("daily_income_usd", 0)

    # Adjusted daily burn
    daily_subs_change = (current_monthly_subs - new_monthly_subs) / 30
    new_daily_burn = max(0, daily_burn_base - daily_subs_change)

    new_runway_days = int(balance / new_daily_burn) if new_daily_burn > 0 else 9999
    runway_gain_days = new_runway_days - (base_runway.get("days_no_income") or 0)

    return {
        "base": {
            "monthly_subs_usd": round(current_monthly_subs, 2),
            "runway_days_no_income": base_runway.get("days_no_income"),
            "daily_burn_usd": round(daily_burn_base, 2),
        },
        "after_toggle": {
            "monthly_subs_usd": round(new_monthly_subs, 2),
            "runway_days_no_income": new_runway_days,
            "daily_burn_usd": round(new_daily_burn, 2),
        },
        "impact": {
            "monthly_savings_usd": round(current_monthly_subs - new_monthly_subs, 2),
            "annual_savings_usd": round((current_monthly_subs - new_monthly_subs) * 12, 2),
            "runway_gain_days": runway_gain_days,
        },
        "toggled_subs": [dict(s) for s in toggled_subs],
    }


def simulate_macro_shock(
    conn,
    ipc_monthly_change_pct: float = 0.0,
    fx_devaluation_pct: float = 0.0,
    income_change_pct: float = 0.0,
    horizon_months: int = 12,
) -> dict[str, Any]:
    """
    Simulate macro shocks on personal finances.
    - ipc_monthly_change_pct: additional monthly inflation (e.g. 5.0 = 5% extra per month)
    - fx_devaluation_pct: immediate FX devaluation (e.g. 20.0 = 20% overnight)
    - income_change_pct: income change (e.g. -10.0 = 10% pay cut)
    - horizon_months: simulation horizon
    """
    binance_rate = _get_binance_rate(conn)

    # Get current IPC
    latest_ipc = conn.execute(
        "SELECT var_pct FROM macro_ipc ORDER BY year DESC, month DESC LIMIT 1"
    ).fetchone()
    base_monthly_inflation = (latest_ipc["var_pct"] / 100) if latest_ipc and latest_ipc["var_pct"] else 0.06

    # Get income
    income_sources = conn.execute(
        "SELECT amount, currency, frequency FROM income_sources WHERE active=1"
    ).fetchall()
    monthly_income_usd = 0.0
    for s in income_sources:
        amt = s["amount"]
        freq = s.get("frequency", "monthly")
        if freq == "biweekly":
            amt *= 2.17
        elif freq == "weekly":
            amt *= 4.33
        elif freq == "annual":
            amt /= 12
        if s["currency"] == "VES":
            amt /= binance_rate
        monthly_income_usd += amt

    # Apply income shock
    shocked_income = monthly_income_usd * (1 + income_change_pct / 100)

    # Apply FX shock
    shocked_rate = binance_rate * (1 + fx_devaluation_pct / 100)

    # Get current spending
    thirty_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    expenses_row = conn.execute(
        "SELECT COALESCE(SUM(ABS(monto_usd)), 0) as total FROM transactions WHERE tipo='Gasto' AND fecha >= ?",
        (thirty_ago,),
    ).fetchone()
    monthly_expenses = expenses_row["total"] or 0.0

    # Total monthly inflation
    total_monthly_inflation = base_monthly_inflation + ipc_monthly_change_pct / 100

    # Simulate month by month
    simulation = []
    balance = max(0, (monthly_income_usd - monthly_expenses) * 3)  # Start with 3 month buffer estimate
    cum_income = 0.0
    cum_expenses = 0.0

    for m in range(1, horizon_months + 1):
        # Income in USD (if paid in VES, income erodes with inflation)
        income_this_month = shocked_income
        # Expenses grow with inflation
        expenses_this_month = monthly_expenses * ((1 + total_monthly_inflation) ** m)

        net = income_this_month - expenses_this_month
        balance += net
        cum_income += income_this_month
        cum_expenses += expenses_this_month

        # FX compounds monthly
        fx_this_month = shocked_rate * ((1 + total_monthly_inflation * 0.8) ** m)

        simulation.append({
            "month": m,
            "income_usd": round(income_this_month, 2),
            "expenses_usd": round(expenses_this_month, 2),
            "net_usd": round(net, 2),
            "cumulative_balance_usd": round(balance, 2),
            "projected_fx_rate": round(fx_this_month, 0),
        })

    # Summarize
    base_annual_net = (monthly_income_usd - monthly_expenses) * 12
    shocked_annual_net = cum_income - cum_expenses

    return {
        "scenario_params": {
            "ipc_additional_monthly_pct": ipc_monthly_change_pct,
            "fx_devaluation_pct": fx_devaluation_pct,
            "income_change_pct": income_change_pct,
            "horizon_months": horizon_months,
        },
        "baseline": {
            "monthly_income_usd": round(monthly_income_usd, 2),
            "monthly_expenses_usd": round(monthly_expenses, 2),
            "annual_net_usd": round(base_annual_net, 2),
            "current_fx_rate": binance_rate,
        },
        "shocked": {
            "monthly_income_usd": round(shocked_income, 2),
            "shocked_fx_rate": round(shocked_rate, 2),
            "total_monthly_inflation_pct": round(total_monthly_inflation * 100, 2),
        },
        "impact": {
            "annual_net_change_usd": round(shocked_annual_net - base_annual_net, 2),
            "annual_net_change_pct": round(
                (shocked_annual_net - base_annual_net) / abs(base_annual_net) * 100, 1
            ) if base_annual_net != 0 else None,
            "income_erosion_usd_12m": round(monthly_income_usd * 12 - cum_income, 2),
            "expense_inflation_usd_12m": round(cum_expenses - monthly_expenses * 12, 2),
        },
        "monthly_simulation": simulation,
    }


def simulate_timeline(conn, months_ahead: int = 12) -> dict[str, Any]:
    """
    'In X months, my finances will look like Y' — deterministic projection.
    Uses current trends + historical averages.
    """
    binance_rate = _get_binance_rate(conn)

    # Monthly spending trend (last 6 months)
    spending_trend = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(ABS(monto_usd)) as total_usd
           FROM transactions
           WHERE tipo='Gasto'
           GROUP BY year, month
           ORDER BY year DESC, month DESC
           LIMIT 6"""
    ).fetchall()

    avg_monthly_spend = (
        sum(r["total_usd"] for r in spending_trend) / len(spending_trend)
        if spending_trend else 0
    )

    # Runway baseline
    runway = compute_runway(conn)

    # FX trend (last 30 days)
    fx_trend = conn.execute(
        """SELECT tasa_binance FROM exchange_rates
           WHERE tasa_binance IS NOT NULL
           ORDER BY fecha DESC LIMIT 30"""
    ).fetchall()

    monthly_fx_drift = 0.02
    if len(fx_trend) >= 30:
        rate_now = fx_trend[0]["tasa_binance"]
        rate_30d = fx_trend[29]["tasa_binance"]
        if rate_30d > 0:
            monthly_fx_drift = max(0, (rate_now - rate_30d) / rate_30d)

    # Cesta basica coverage trend
    cesta_latest = conn.execute(
        "SELECT total_bs, total_usd FROM cesta_basica ORDER BY year DESC, month DESC LIMIT 1"
    ).fetchone()

    baskets_covered = None
    daily_income = runway.get("daily_income_usd", 0)
    monthly_income = daily_income * 30

    if cesta_latest and monthly_income > 0:
        cesta_usd = cesta_latest["total_usd"]
        if not cesta_usd and cesta_latest["total_bs"] and binance_rate > 0:
            cesta_usd = cesta_latest["total_bs"] / binance_rate
        if cesta_usd:
            baskets_covered = round(monthly_income / cesta_usd, 2)

    # Project X months forward
    projected_balance = runway.get("current_balance_usd", 0)
    projected_rate = binance_rate * ((1 + monthly_fx_drift) ** months_ahead)
    net_monthly = (daily_income - runway.get("daily_burn_usd", 0)) * 30
    projected_balance_future = projected_balance + net_monthly * months_ahead

    return {
        "horizon_months": months_ahead,
        "current": {
            "balance_usd": runway.get("current_balance_usd"),
            "monthly_income_usd": round(monthly_income, 2),
            "monthly_burn_usd": round(avg_monthly_spend, 2),
            "net_monthly_usd": round(net_monthly, 2),
            "binance_rate": binance_rate,
            "baskets_covered": baskets_covered,
        },
        "projected": {
            "balance_usd": round(projected_balance_future, 2),
            "binance_rate": round(projected_rate, 0),
            "months_until_zero": runway.get("days_no_income", 0) // 30 if net_monthly < 0 else None,
        },
        "assumptions": {
            "monthly_fx_drift_pct": round(monthly_fx_drift * 100, 2),
            "avg_monthly_spend_usd": round(avg_monthly_spend, 2),
        },
    }


def compute_goal_scenario(conn, target_usd: float, target_name: str = "Goal",
                           cancel_sub_ids: list[int] | None = None) -> dict[str, Any]:
    """
    Combined: saving goal + optional subscription cancellations.
    Shows impact of cancelling subs on time to goal.
    """
    plan = calculate_saving_plan(conn, target_usd, target_name)

    if cancel_sub_ids:
        toggle = simulate_subscription_toggle(conn, cancel_sub_ids, toggle_state=False)
        extra_monthly = toggle["impact"]["monthly_savings_usd"]

        # Recalculate plan with extra savings
        plan_with_cancels = calculate_saving_plan(
            conn, target_usd, target_name,
            monthly_contribution=plan["monthly_contribution_usd"] + extra_monthly,
        )
        plan_with_cancels["from_sub_cancellations_usd"] = round(extra_monthly, 2)
        plan_with_cancels["weeks_saved"] = max(0, round(
            (plan["months_needed"] - plan_with_cancels["months_needed"]) * 4.3
        )) if plan["months_needed"] and plan_with_cancels["months_needed"] else None

        return {
            "without_cancellations": plan,
            "with_cancellations": plan_with_cancels,
            "sub_toggle": toggle,
        }

    return {"without_cancellations": plan}
