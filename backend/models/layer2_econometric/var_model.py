"""Layer 2: Vector Autoregression (VAR)."""
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller


def _make_stationary(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Difference columns that fail ADF at 5%."""
    diff_info = {}
    result = df.copy()
    for col in df.columns:
        try:
            p = adfuller(df[col].dropna(), autolag="AIC")[1]
            if p > 0.05:
                result[col] = df[col].diff()
                diff_info[col] = 1
            else:
                diff_info[col] = 0
        except Exception:
            diff_info[col] = 0
    return result.dropna(), diff_info


def fit_var(df: pd.DataFrame, maxlags: int = 5, horizon: int = 7) -> dict[str, Any]:
    if len(df) < 40:
        return {"error": "Need at least 40 observations for VAR"}

    stationary, diff_info = _make_stationary(df)
    if len(stationary) < 30:
        return {"error": "Insufficient data after differencing"}

    try:
        model = VAR(stationary)
        lag_order = model.select_order(maxlags=min(maxlags, len(stationary) // 5))
        optimal_lag = lag_order.aic
        if optimal_lag is None or optimal_lag < 1:
            optimal_lag = 1

        fitted = model.fit(optimal_lag)
        fc = fitted.forecast(stationary.values[-optimal_lag:], steps=horizon)

        # Build per-variable forecasts (in differenced space; cumulative for diffed vars)
        forecasts = {}
        for i, col in enumerate(stationary.columns):
            fc_col = fc[:, i]
            if diff_info.get(col, 0) > 0:
                last_level = df[col].dropna().iloc[-1]
                fc_col = last_level + np.cumsum(fc_col)
            forecasts[col] = fc_col.tolist()

        return {
            "model": "VAR",
            "lag_order": int(optimal_lag),
            "variables": list(df.columns),
            "diff_orders": diff_info,
            "forecast": forecasts,
            "aic": float(fitted.aic),
            "bic": float(fitted.bic),
            "n_obs": int(fitted.nobs),
        }
    except Exception as e:
        return {"error": f"VAR fit failed: {e}"}
