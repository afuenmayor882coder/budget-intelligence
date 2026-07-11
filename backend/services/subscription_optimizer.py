"""Subscription optimizer: score and rank subscriptions for cancellation/downgrade."""
from typing import Any


def _get_binance_rate(conn) -> float:
    row = conn.execute(
        "SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    return row["tasa_binance"] if row and row["tasa_binance"] else 700.0


def _monthly_usd(sub: dict, binance_rate: float) -> float:
    amt = sub["amount"]
    freq = sub.get("frequency", "monthly")
    currency = sub.get("currency", "USD")

    if freq == "annual":
        amt /= 12
    elif freq == "quarterly":
        amt /= 3
    elif freq == "biweekly":
        amt *= 2.17
    elif freq == "weekly":
        amt *= 4.33

    if currency == "VES":
        amt /= binance_rate

    return round(amt, 2)


def compute_subscription_score(sub: dict, monthly_usd: float, total_monthly_usd: float,
                                monthly_income_usd: float, binance_rate: float,
                                rate_6m_ago: float | None) -> dict[str, Any]:
    """
    Score = weighted combination of:
    - cost_weight (0-40): higher cost → higher score (more to save)
    - income_pct_weight (0-30): % of income this sub consumes
    - fx_exposure_weight (0-20): USD subs are more costly as VES devalues
    - essential_weight (-20-0): essential subs get a penalty (don't cancel)
    """
    cost_score = min(40, monthly_usd / max(total_monthly_usd, 1) * 40 * 3)

    income_pct = (monthly_usd / monthly_income_usd * 100) if monthly_income_usd > 0 else 0
    income_score = min(30, income_pct * 3)

    fx_score = 0
    fx_growth_pct = None
    if sub.get("currency") == "USD" and rate_6m_ago and rate_6m_ago > 0:
        fx_growth_pct = round((binance_rate - rate_6m_ago) / rate_6m_ago * 100, 1)
        fx_score = min(20, max(0, fx_growth_pct / 5))

    essential_penalty = -20 if sub.get("essential") else 0

    total_score = cost_score + income_score + fx_score + essential_penalty

    # Build recommendation
    if sub.get("essential"):
        action = "keep"
        reason = "Marked as essential — not recommended for cancellation"
    elif monthly_usd > 30:
        action = "review"
        reason = f"High-cost subscription (${monthly_usd:.2f}/mo) — consider downgrading"
    elif income_pct > 5:
        action = "review"
        reason = f"Consumes {income_pct:.1f}% of monthly income"
    elif monthly_usd < 5:
        action = "keep"
        reason = "Low cost — minimal savings from cancellation"
    else:
        action = "monitor"
        reason = "Moderate cost — evaluate usage"

    return {
        "monthly_usd": monthly_usd,
        "income_pct": round(income_pct, 1),
        "fx_growth_6m_pct": fx_growth_pct,
        "fx_exposure": sub.get("currency") == "USD",
        "score": round(total_score, 1),
        "action": action,
        "reason": reason,
        "annual_savings_if_cancelled_usd": round(monthly_usd * 12, 2),
    }


def optimize_subscriptions(conn) -> dict[str, Any]:
    """Analyze all active subscriptions and return optimization recommendations."""
    binance_rate = _get_binance_rate(conn)

    rate_6m_row = conn.execute(
        """SELECT tasa_binance FROM exchange_rates
           WHERE fecha <= date('now', '-6 months')
           ORDER BY fecha DESC LIMIT 1"""
    ).fetchone()
    rate_6m_ago = rate_6m_row["tasa_binance"] if rate_6m_row else None

    # Monthly income
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

    # All active subscriptions
    subs = conn.execute(
        "SELECT * FROM subscriptions WHERE active=1 ORDER BY amount DESC"
    ).fetchall()
    subs = [dict(s) for s in subs]

    # Compute monthly totals
    for s in subs:
        s["monthly_usd"] = _monthly_usd(s, binance_rate)

    total_monthly_usd = sum(s["monthly_usd"] for s in subs)

    # Score each subscription
    results = []
    for s in subs:
        score_data = compute_subscription_score(
            s, s["monthly_usd"], total_monthly_usd,
            monthly_income_usd, binance_rate, rate_6m_ago
        )
        results.append({
            "id": s["id"],
            "name": s["name"],
            "currency": s["currency"],
            "frequency": s["frequency"],
            "essential": bool(s["essential"]),
            "category": s.get("category"),
            **score_data,
        })

    # Sort by score descending (highest savings potential first)
    results.sort(key=lambda x: x["score"], reverse=True)

    # Top recommendations
    cancel_candidates = [r for r in results if r["action"] in ("review",) and not r["essential"]]
    potential_savings = sum(c["monthly_usd"] for c in cancel_candidates)

    # Subscription portfolio stats
    usd_subs = [r for r in results if r["fx_exposure"]]
    ves_subs = [r for r in results if not r["fx_exposure"]]

    return {
        "total_monthly_usd": round(total_monthly_usd, 2),
        "total_annual_usd": round(total_monthly_usd * 12, 2),
        "income_pct_of_subs": round(total_monthly_usd / monthly_income_usd * 100, 1) if monthly_income_usd > 0 else None,
        "sub_count": len(results),
        "usd_subs_count": len(usd_subs),
        "ves_subs_count": len(ves_subs),
        "potential_monthly_savings_usd": round(potential_savings, 2),
        "potential_annual_savings_usd": round(potential_savings * 12, 2),
        "ranked_subscriptions": results,
        "cancel_candidates": cancel_candidates[:3],
        "binance_rate": binance_rate,
        "fx_change_6m_pct": round((binance_rate - rate_6m_ago) / rate_6m_ago * 100, 1) if rate_6m_ago else None,
    }
