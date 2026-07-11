"""Layer 1: Prophet forecasting (optional dependency)."""
from typing import Any

import pandas as pd


def fit_prophet_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    try:
        from prophet import Prophet
    except ImportError:
        return {"error": "Prophet not installed (optional dependency)", "skipped": True}

    s = series.dropna().astype(float)
    if len(s) < 30:
        return {"error": "Need at least 30 observations for Prophet"}

    df = pd.DataFrame({
        "ds": pd.to_datetime(s.index if isinstance(s.index, pd.DatetimeIndex) else range(len(s))),
        "y": s.values,
    })

    try:
        model = Prophet(daily_seasonality=True, weekly_seasonality=True, yearly_seasonality=False)
        model.fit(df)
        future = model.make_future_dataframe(periods=horizon)
        forecast_df = model.predict(future)
        tail = forecast_df.tail(horizon)
        return {
            "model": "Prophet",
            "forecast": tail["yhat"].tolist(),
            "lower_95": tail["yhat_lower"].tolist(),
            "upper_95": tail["yhat_upper"].tolist(),
        }
    except Exception as e:
        return {"error": f"Prophet failed: {e}", "skipped": True}


def prophet_predict_fn(series: pd.Series, horizon: int):
    import numpy as np
    result = fit_prophet_forecast(series, horizon=horizon)
    if "forecast" not in result:
        raise ValueError(result.get("error", "Prophet forecast failed"))
    return np.array(result["forecast"])
