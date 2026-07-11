"""Layer 1: ARIMA/SARIMA forecasting."""
from typing import Any

import numpy as np
import pandas as pd

try:
    import pmdarima as pm
    HAS_PMDARIMA = True
except ImportError:
    HAS_PMDARIMA = False

from statsmodels.tsa.arima.model import ARIMA


def fit_arima_forecast(series: pd.Series, horizon: int = 7, seasonal: bool = False) -> dict[str, Any]:
    s = series.dropna().astype(float)
    if len(s) < 30:
        return {"error": "Need at least 30 observations for ARIMA"}

    if HAS_PMDARIMA and seasonal:
        try:
            model = pm.auto_arima(
                s.values, seasonal=True, m=7, stepwise=True,
                suppress_warnings=True, error_action="ignore",
                max_p=3, max_q=3, max_P=2, max_Q=2,
            )
            forecast, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=0.05)
            return {
                "model": "SARIMA",
                "order": str(model.order),
                "seasonal_order": str(getattr(model, "seasonal_order", None)),
                "forecast": forecast.tolist(),
                "lower_95": conf_int[:, 0].tolist(),
                "upper_95": conf_int[:, 1].tolist(),
                "aic": float(model.aic()) if hasattr(model, "aic") else None,
            }
        except Exception:
            pass

    if HAS_PMDARIMA:
        try:
            model = pm.auto_arima(
                s.values, seasonal=False, stepwise=True,
                suppress_warnings=True, error_action="ignore",
                max_p=5, max_q=5,
            )
            forecast, conf_int = model.predict(n_periods=horizon, return_conf_int=True, alpha=0.05)
            return {
                "model": "ARIMA",
                "order": str(model.order),
                "forecast": forecast.tolist(),
                "lower_95": conf_int[:, 0].tolist(),
                "upper_95": conf_int[:, 1].tolist(),
                "aic": float(model.aic()) if hasattr(model, "aic") else None,
            }
        except Exception as e:
            last_err = str(e)
    else:
        last_err = "pmdarima not available"

    # Fallback: simple ARIMA(1,1,1)
    try:
        model = ARIMA(s, order=(1, 1, 1)).fit()
        fc = model.get_forecast(steps=horizon)
        return {
            "model": "ARIMA",
            "order": "(1,1,1)",
            "forecast": fc.predicted_mean.tolist(),
            "lower_95": fc.conf_int().iloc[:, 0].tolist(),
            "upper_95": fc.conf_int().iloc[:, 1].tolist(),
            "aic": float(model.aic),
            "fallback": True,
        }
    except Exception as e:
        return {"error": f"ARIMA failed: {last_err}; fallback: {e}"}


def arima_predict_fn(series: pd.Series, horizon: int) -> np.ndarray:
    result = fit_arima_forecast(series, horizon=horizon)
    if "forecast" not in result:
        raise ValueError(result.get("error", "ARIMA forecast failed"))
    return np.array(result["forecast"])
