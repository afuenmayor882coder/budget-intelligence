"""Monte Carlo scenario simulation for FX and personal finances."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def monte_carlo_fx_simulation(
    series: pd.Series,
    horizon_days: int = 30,
    n_simulations: int = 500,
    garch_vol: float | None = None,
) -> dict[str, Any]:
    """
    Simulate FX paths using geometric Brownian motion with estimated drift/vol.
    Optionally scale vol using GARCH conditional volatility.
    """
    s = series.dropna().astype(float)
    if len(s) < 30:
        return {"error": "Need at least 30 observations"}

    log_returns = np.log(s / s.shift(1)).dropna()
    mu = float(log_returns.mean())
    sigma = float(log_returns.std())
    if garch_vol is not None and garch_vol > 0:
        sigma = garch_vol / 100  # GARCH returns in percent

    last_price = float(s.iloc[-1])
    simulations = np.zeros((n_simulations, horizon_days))

    for i in range(n_simulations):
        price = last_price
        for t in range(horizon_days):
            shock = np.random.normal(mu, sigma)
            price = price * np.exp(shock)
            simulations[i, t] = price

    percentiles = {
        "p05": np.percentile(simulations, 5, axis=0).tolist(),
        "p25": np.percentile(simulations, 25, axis=0).tolist(),
        "p50": np.percentile(simulations, 50, axis=0).tolist(),
        "p75": np.percentile(simulations, 75, axis=0).tolist(),
        "p95": np.percentile(simulations, 95, axis=0).tolist(),
    }

    final_prices = simulations[:, -1]
    return {
        "method": "monte_carlo_gbm",
        "n_simulations": n_simulations,
        "horizon_days": horizon_days,
        "start_price": last_price,
        "drift_daily": mu,
        "volatility_daily": sigma,
        "percentiles": percentiles,
        "final_price_mean": float(final_prices.mean()),
        "final_price_std": float(final_prices.std()),
        "prob_increase": float((final_prices > last_price).mean()),
    }


def monte_carlo_balance_simulation(
    current_balance: float,
    monthly_income: float,
    monthly_expenses: float,
    monthly_inflation: float = 0.06,
    fx_monthly_drift: float = 0.02,
    horizon_months: int = 12,
    n_simulations: int = 500,
) -> dict[str, Any]:
    """Simulate personal balance paths under stochastic inflation/FX."""
    balances = np.zeros((n_simulations, horizon_months + 1))
    balances[:, 0] = current_balance

    for sim in range(n_simulations):
        bal = current_balance
        for m in range(1, horizon_months + 1):
            infl_shock = np.random.normal(monthly_inflation, monthly_inflation * 0.3)
            infl_shock = max(0, infl_shock)
            expenses = monthly_expenses * ((1 + infl_shock) ** m)
            income_noise = np.random.normal(0, monthly_income * 0.05)
            net = (monthly_income + income_noise) - expenses
            bal += net
            balances[sim, m] = max(bal, 0)

    final = balances[:, -1]
    zero_cross = (balances <= 0).any(axis=1)

    return {
        "method": "monte_carlo_balance",
        "n_simulations": n_simulations,
        "horizon_months": horizon_months,
        "percentiles_final": {
            "p05": float(np.percentile(final, 5)),
            "p50": float(np.percentile(final, 50)),
            "p95": float(np.percentile(final, 95)),
        },
        "prob_negative": float(zero_cross.mean()),
        "mean_final_balance": float(final.mean()),
        "monthly_paths_p50": np.percentile(balances, 50, axis=0).tolist(),
    }
