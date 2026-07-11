"""Goal-based saving plan calculator with FX-aware projections."""
from datetime import datetime, timedelta
from typing import Any


PRESET_GOALS = [
    {"name": "iPhone 17 Pro", "target_usd": 1199, "category": "tech"},
    {"name": "MacBook Pro", "target_usd": 1999, "category": "tech"},
    {"name": "Car (used)", "target_usd": 8000, "category": "vehicle"},
    {"name": "Emergency Fund (6 months)", "target_usd": None, "category": "emergency"},
]


def _get_binance_rate(conn) -> float:
    row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    return row["tasa_binance"] if row and row["tasa_binance"] else 700.0


def _project_fx_rate(current_rate: float, months_ahead: int,
                     monthly_fx_drift: float = 0.02) -> float:
    """Simple FX projection: compound monthly drift rate."""
    return round(current_rate * ((1 + monthly_fx_drift) ** months_ahead), 2)


def _get_monthly_surplus(conn, binance_rate: float) -> float:
    """Estimate current monthly surplus (income - expenses - subscriptions)."""
    from services.calculations import compute_runway
    runway = compute_runway(conn)
    daily_income = runway.get("daily_income_usd", 0)
    daily_burn = runway.get("daily_burn_usd", 0)
    return (daily_income - daily_burn) * 30


def calculate_saving_plan(
    conn,
    target_usd: float,
    target_name: str = "Goal",
    target_months: int | None = None,
    monthly_contribution: float | None = None,
) -> dict[str, Any]:
    """
    Compute a saving plan for a USD-denominated goal.

    Returns:
    - months_needed (at current surplus)
    - recommended_monthly_contribution
    - completion_date
    - feasibility_score (0-100)
    - fx_adjusted projection
    """
    binance_rate = _get_binance_rate(conn)

    # Estimate monthly surplus
    monthly_surplus = _get_monthly_surplus(conn, binance_rate)

    # Get average monthly FX drift from historical data
    rates_90d = conn.execute(
        """SELECT tasa_binance FROM exchange_rates
           WHERE tasa_binance IS NOT NULL
           ORDER BY fecha DESC LIMIT 90"""
    ).fetchall()

    monthly_fx_drift = 0.02  # Default 2% monthly
    if len(rates_90d) >= 30:
        rate_now = rates_90d[0]["tasa_binance"]
        rate_30d = rates_90d[min(29, len(rates_90d)-1)]["tasa_binance"]
        if rate_30d > 0:
            monthly_fx_drift = max(0, (rate_now - rate_30d) / rate_30d)

    # Use user-specified contribution or current surplus
    if monthly_contribution is not None:
        save_per_month = monthly_contribution
    else:
        save_per_month = max(0, monthly_surplus)

    # Calculate months needed
    if save_per_month <= 0:
        months_needed = None
        feasibility = 0
    else:
        months_needed = int(target_usd / save_per_month) + 1
        feasibility = min(100, int((save_per_month / (target_usd / 12)) * 100))

    # FX-adjusted target (if purchasing in Venezuela with VES)
    fx_adjusted_ves_needed = None
    if months_needed:
        projected_rate = _project_fx_rate(binance_rate, months_needed, monthly_fx_drift)
        fx_adjusted_ves_needed = round(target_usd * projected_rate, 0)

    # Completion date
    completion_date = None
    if months_needed:
        completion_date = (datetime.now() + timedelta(days=months_needed * 30.5)).strftime("%Y-%m-%d")

    # Alternative timelines
    timelines = []
    for months in [3, 6, 12, 18, 24, 36]:
        needed_per_month = target_usd / months
        projected_rate_at_t = _project_fx_rate(binance_rate, months, monthly_fx_drift)
        timelines.append({
            "months": months,
            "required_monthly_usd": round(needed_per_month, 2),
            "feasible": needed_per_month <= monthly_surplus * 1.5 if monthly_surplus > 0 else False,
            "projected_fx_at_purchase": projected_rate_at_t,
            "ves_needed": round(target_usd * projected_rate_at_t, 0),
        })

    return {
        "target_name": target_name,
        "target_usd": target_usd,
        "monthly_surplus_usd": round(monthly_surplus, 2),
        "monthly_contribution_usd": round(save_per_month, 2),
        "months_needed": months_needed,
        "completion_date": completion_date,
        "feasibility_score": feasibility,
        "current_binance_rate": binance_rate,
        "monthly_fx_drift_pct": round(monthly_fx_drift * 100, 2),
        "fx_adjusted_ves_needed": fx_adjusted_ves_needed,
        "timelines": timelines,
    }


def get_all_active_goals(conn) -> list[dict[str, Any]]:
    """Calculate saving plans for all active goals in DB."""
    binance_rate = _get_binance_rate(conn)
    monthly_surplus = _get_monthly_surplus(conn, binance_rate)

    goals = conn.execute(
        "SELECT * FROM saving_goals WHERE active=1 ORDER BY priority"
    ).fetchall()

    results = []
    for g in goals:
        plan = calculate_saving_plan(
            conn,
            target_usd=g["target_amount"],
            target_name=g["name"],
            target_months=None,
            monthly_contribution=g.get("monthly_contribution"),
        )
        plan["goal_id"] = g["id"]
        plan["target_date"] = g.get("target_date")
        plan["priority"] = g.get("priority", 1)
        results.append(plan)

    return results


def get_preset_goals() -> list[dict]:
    return PRESET_GOALS
