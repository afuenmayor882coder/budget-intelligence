"""Layer 1: Theta method forecasting."""
from typing import Any

import numpy as np
import pandas as pd


def fit_theta_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """
    Simple Theta decomposition: theta=2 line + drift.
    """
    s = series.dropna().astype(float)
    n = len(s)
    if n < 10:
        return {"error": "Need at least 10 observations for Theta"}

    # Linear trend on deseasonalized series
    x = np.arange(n)
    coef = np.polyfit(x, s.values, 1)
    trend = np.polyval(coef, x)
    residual = s.values - trend

    # Theta=2: combine level and trend
    level = s.values[-1]
    drift = coef[0]
    forecast = []
    for h in range(1, horizon + 1):
        # Theta-2 forecast: level + h*drift + damped residual mean
        fc = level + h * drift + 0.5 * np.mean(residual[-min(7, n):])
        forecast.append(float(fc))

    return {
        "model": "Theta",
        "drift": float(drift),
        "forecast": forecast,
        "lower_95": None,
        "upper_95": None,
    }


def theta_predict_fn(series: pd.Series, horizon: int) -> np.ndarray:
    result = fit_theta_forecast(series, horizon=horizon)
    if "forecast" not in result:
        raise ValueError(result.get("error", "Theta forecast failed"))
    return np.array(result["forecast"])
