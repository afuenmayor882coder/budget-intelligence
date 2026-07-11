"""Layer 1: ETS / Holt-Winters exponential smoothing."""
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing


def fit_ets_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    s = series.dropna().astype(float)
    if len(s) < 20:
        return {"error": "Need at least 20 observations for ETS"}

    errors = []
    for seasonal in [None, "add"]:
        for trend in ["add", None]:
            if seasonal and len(s) < 14:
                continue
            try:
                model = ExponentialSmoothing(
                    s,
                    trend=trend,
                    seasonal=seasonal,
                    seasonal_periods=7 if seasonal else None,
                ).fit(optimized=True)
                forecast = model.forecast(horizon)
                return {
                    "model": "ETS",
                    "trend": trend or "none",
                    "seasonal": seasonal or "none",
                    "forecast": forecast.tolist(),
                    "aic": float(model.aic) if model.aic is not None else None,
                    "lower_95": None,
                    "upper_95": None,
                }
            except Exception as e:
                errors.append(str(e))

    return {"error": f"ETS failed: {errors[-1] if errors else 'unknown'}"}


def ets_predict_fn(series: pd.Series, horizon: int) -> np.ndarray:
    result = fit_ets_forecast(series, horizon=horizon)
    if "forecast" not in result:
        raise ValueError(result.get("error", "ETS forecast failed"))
    return np.array(result["forecast"])
