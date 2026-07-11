"""Layer 5: State-space Kalman filter for trend extraction."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.statespace.unobserved_components import UnobservedComponents
    HAS_UC = True
except ImportError:
    HAS_UC = False


def fit_kalman_trend(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """
    Local linear trend model via UnobservedComponents (Kalman filter).
    """
    if not HAS_UC:
        return {"error": "statsmodels UnobservedComponents unavailable"}

    s = series.dropna().astype(float)
    if len(s) < 30:
        return {"error": "Need at least 30 observations for Kalman filter"}

    try:
        model = UnobservedComponents(s, level="local linear trend")
        res = model.fit(disp=False)
        forecast = res.get_forecast(steps=horizon)
        fc_mean = forecast.predicted_mean
        conf = forecast.conf_int(alpha=0.05)

        # Decompose smoothed components
        smoothed = res.smoothed_state
        level = smoothed[0] if smoothed is not None else None

        return {
            "model": "Kalman",
            "layer": "layer5",
            "forecast": fc_mean.tolist(),
            "lower_95": conf.iloc[:, 0].tolist(),
            "upper_95": conf.iloc[:, 1].tolist(),
            "trend_level": float(level[-1]) if level is not None and len(level) else None,
            "aic": float(res.aic),
        }
    except Exception as e:
        return {"error": str(e), "model": "Kalman"}
