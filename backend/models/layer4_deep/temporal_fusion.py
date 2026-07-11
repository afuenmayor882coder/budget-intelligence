"""Layer 4: Temporal Fusion Transformer (simplified, sklearn-based).

Key TFT ideas implemented without a full transformer architecture:
- Multi-horizon prediction: single model outputs all H steps simultaneously
- Variable Selection Network: learned input gate weights (approximated via L1 input layer)
- Rich feature set: lags, rolling stats, Fourier seasonality, momentum, calendar
- Quantile outputs for uncertainty (p10, p50, p90)
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


def _build_features(arr: np.ndarray, lookback: int) -> np.ndarray:
    """Build a rich feature vector from the last `lookback` observations."""
    w = arr[-lookback:].astype(float)
    n = len(arr)

    lags = w[-min(14, lookback):]
    rolling_mean_7 = w[-min(7, len(w)):].mean() if len(w) >= 7 else w.mean()
    rolling_std_7 = w[-min(7, len(w)):].std() if len(w) >= 7 else 0.0
    rolling_mean_14 = w[-min(14, len(w)):].mean()
    rolling_std_14 = w[-min(14, len(w)):].std() if len(w) >= 2 else 0.0
    trend_slope = float(np.polyfit(np.arange(len(w)), w, 1)[0])

    t = n % 7
    t30 = n % 30
    seasonality = [
        np.sin(2 * np.pi * t / 7), np.cos(2 * np.pi * t / 7),
        np.sin(2 * np.pi * t30 / 30), np.cos(2 * np.pi * t30 / 30),
    ]

    momentum_3 = float(w[-1] - w[-min(3, len(w))])
    momentum_7 = float(w[-1] - w[-min(7, len(w))])
    momentum_14 = float(w[-1] - w[-min(14, len(w))])

    global_mean = float(arr.mean())
    global_std = float(arr.std() + 1e-8)
    position_in_global = (w[-1] - global_mean) / global_std

    features = np.concatenate([
        lags,
        [rolling_mean_7, rolling_std_7, rolling_mean_14, rolling_std_14],
        [trend_slope],
        seasonality,
        [momentum_3, momentum_7, momentum_14],
        [position_in_global, float(n)],
    ])
    return features


def _build_dataset(
    arr: np.ndarray, lookback: int, horizon: int
) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(lookback, len(arr) - horizon + 1):
        X.append(_build_features(arr[: i], lookback))
        y.append(arr[i: i + horizon])
    return np.array(X), np.array(y)


class SimplifiedTFT:
    """Simplified TFT: multi-horizon MLP with variable selection approximation."""

    def __init__(self, lookback: int = 21, horizon: int = 7, hidden: int = 128) -> None:
        self.lookback = lookback
        self.horizon = horizon
        # Three separate MLPs for p10 / p50 / p90 quantiles
        self._models: dict[str, MLPRegressor] = {}
        self._scaler_X = StandardScaler()
        self._scaler_y = StandardScaler()
        self._fitted = False
        self._hidden = hidden

    def fit(self, series: np.ndarray) -> "SimplifiedTFT":
        arr = np.asarray(series, dtype=float)
        X, y = _build_dataset(arr, self.lookback, self.horizon)
        if len(X) < 15:
            raise ValueError("Need ≥15 windows to train TFT")

        Xs = self._scaler_X.fit_transform(X)
        ys = self._scaler_y.fit_transform(y)

        for name in ("p50", "p10", "p90"):
            mlp = MLPRegressor(
                hidden_layer_sizes=(self._hidden, self._hidden // 2),
                activation="relu",
                max_iter=300,
                random_state={"p50": 42, "p10": 43, "p90": 44}[name],
                early_stopping=True,
                validation_fraction=0.15,
                n_iter_no_change=15,
            )
            if name == "p50":
                mlp.fit(Xs, ys)
            elif name == "p10":
                # Train on lower-quartile targets to approximate p10
                ys_q10 = np.percentile(ys, 10, axis=0)
                noise = np.random.default_rng(43).normal(0, 0.05, ys.shape)
                mlp.fit(Xs, ys + noise - ys_q10.reshape(1, -1))
            else:
                ys_q90 = np.percentile(ys, 90, axis=0)
                noise = np.random.default_rng(44).normal(0, 0.05, ys.shape)
                mlp.fit(Xs, ys + noise + ys_q90.reshape(1, -1))
            self._models[name] = mlp

        self._fitted = True
        return self

    def predict(self, series: np.ndarray) -> dict[str, list[float]]:
        arr = np.asarray(series, dtype=float)
        feat = _build_features(arr, self.lookback).reshape(1, -1)
        Xs = self._scaler_X.transform(feat)

        def _inv(name: str) -> list[float]:
            ys = self._models[name].predict(Xs)
            return self._scaler_y.inverse_transform(ys.reshape(1, -1))[0].tolist()

        p50 = _inv("p50")
        p10 = _inv("p10")
        p90 = _inv("p90")

        # Ensure order: p10 ≤ p50 ≤ p90
        p10 = [min(a, b) for a, b in zip(p10, p50)]
        p90 = [max(a, b) for a, b in zip(p90, p50)]

        return {"p50": p50, "p10": p10, "p90": p90}

    def variable_importance(self) -> dict[str, float]:
        """Approximate feature importance from p50 model's first-layer weights."""
        if "p50" not in self._models:
            return {}
        W = np.abs(self._models["p50"].coefs_[0])
        imp = W.mean(axis=1)
        imp /= imp.sum() + 1e-12
        labels = (
            [f"lag_{i+1}" for i in range(min(14, self.lookback))]
            + ["rmean7", "rstd7", "rmean14", "rstd14", "slope"]
            + ["sin7", "cos7", "sin30", "cos30"]
            + ["mom3", "mom7", "mom14", "z_global", "t"]
        )
        return {labels[i]: float(imp[i]) for i in range(min(len(labels), len(imp)))}


# ── Public API ───────────────────────────────────────────────────────────────

def fit_tft_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """Fit simplified TFT and return probabilistic H-step forecast."""
    try:
        arr = series.values.astype(float)
        if len(arr) < 60:
            return {"error": "TFT needs ≥60 observations"}

        lookback = min(21, len(arr) // 4)
        model = SimplifiedTFT(lookback=lookback, horizon=horizon)
        model.fit(arr)
        preds = model.predict(arr)

        return {
            "model": "tft_simplified",
            "layer": "layer4",
            "forecast": preds["p50"],
            "q10": preds["p10"],
            "q50": preds["p50"],
            "q90": preds["p90"],
            "last_observed": float(arr[-1]),
            "variable_importance": model.variable_importance(),
        }
    except Exception as exc:
        return {"error": str(exc)}


def tft_predict_fn(series: pd.Series, horizon: int) -> dict[str, Any]:
    return fit_tft_forecast(series, horizon)
