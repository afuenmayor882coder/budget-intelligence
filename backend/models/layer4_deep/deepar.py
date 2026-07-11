"""Layer 4: DeepAR proxy — probabilistic autoregressive forecasting.

DeepAR's key innovation is outputting full predictive distributions rather than
point forecasts. This implementation approximates it using:
- MLPRegressor ensemble trained on windowed sequences with seasonal features
- Bootstrap residuals for uncertainty quantification (no Gaussian assumption)
- Outputs: point forecast + p10/p50/p90 prediction intervals

References:
- Salinas et al. (2020) "DeepAR: Probabilistic Forecasting with Autoregressive
  Recurrent Networks"
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


def _build_windows(
    arr: np.ndarray, lookback: int, horizon: int
) -> tuple[np.ndarray, np.ndarray]:
    """Build feature matrix: [lagged values + seasonal encodings] → H-step targets."""
    X, y = [], []
    for i in range(lookback, len(arr) - horizon + 1):
        window = arr[i - lookback: i]
        t_week = i % 7
        t_month = i % 30
        seasonal = [
            np.sin(2 * np.pi * t_week / 7),
            np.cos(2 * np.pi * t_week / 7),
            np.sin(2 * np.pi * t_month / 30),
            np.cos(2 * np.pi * t_month / 30),
        ]
        # Add log-scale features (stabilise heteroskedastic FX data)
        log_window = np.log(np.abs(window) + 1)
        feats = np.concatenate([window, log_window[-min(7, lookback):], seasonal])
        X.append(feats)
        y.append(arr[i: i + horizon])
    return np.array(X), np.array(y)


def fit_deepar_forecast(
    series: pd.Series,
    horizon: int = 7,
    n_bootstrap: int = 200,
) -> dict[str, Any]:
    """Fit DeepAR proxy and return point forecast + prediction intervals."""
    try:
        arr = series.values.astype(float)
        n = len(arr)
        if n < 60:
            return {"error": "DeepAR needs ≥60 observations"}

        lookback = min(21, n // 4)
        X, y = _build_windows(arr, lookback, horizon)
        if len(X) < 20:
            return {"error": "Not enough training windows"}

        scaler_X = StandardScaler()
        scaler_y = StandardScaler()
        Xs = scaler_X.fit_transform(X)
        ys = scaler_y.fit_transform(y)

        mlp = MLPRegressor(
            hidden_layer_sizes=(128, 64),
            activation="relu",
            max_iter=300,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.15,
            n_iter_no_change=15,
        )
        mlp.fit(Xs, ys)

        # In-sample residuals (normalised space)
        residuals_s = ys - mlp.predict(Xs)

        # Build query feature for the last window
        t_last_week = n % 7
        t_last_month = n % 30
        last_window = arr[-lookback:]
        log_last = np.log(np.abs(last_window) + 1)
        seasonal_last = [
            np.sin(2 * np.pi * t_last_week / 7),
            np.cos(2 * np.pi * t_last_week / 7),
            np.sin(2 * np.pi * t_last_month / 30),
            np.cos(2 * np.pi * t_last_month / 30),
        ]
        x_last = np.concatenate([last_window, log_last[-min(7, lookback):], seasonal_last])
        Xs_last = scaler_X.transform(x_last.reshape(1, -1))
        y_point_s = mlp.predict(Xs_last)

        # Bootstrap prediction intervals
        rng = np.random.default_rng(42)
        boots = []
        for _ in range(n_bootstrap):
            idx = rng.integers(0, len(residuals_s))
            noise = residuals_s[idx]
            y_boot_s = y_point_s[0] + noise
            y_boot = scaler_y.inverse_transform(y_boot_s.reshape(1, -1))[0]
            boots.append(y_boot)

        boots_arr = np.array(boots)
        q10 = np.percentile(boots_arr, 10, axis=0)
        q50 = np.percentile(boots_arr, 50, axis=0)
        q90 = np.percentile(boots_arr, 90, axis=0)
        point = scaler_y.inverse_transform(y_point_s)[0]

        return {
            "model": "deepar_proxy",
            "layer": "layer4",
            "forecast": point.tolist(),
            "q10": q10.tolist(),
            "q50": q50.tolist(),
            "q90": q90.tolist(),
            "prediction_interval_pct": 80,
            "last_observed": float(arr[-1]),
            "n_bootstrap": n_bootstrap,
        }
    except Exception as exc:
        return {"error": str(exc)}


def deepar_predict_fn(series: pd.Series, horizon: int) -> dict[str, Any]:
    return fit_deepar_forecast(series, horizon)
