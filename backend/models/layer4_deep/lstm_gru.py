"""Layer 4: LSTM/GRU proxy via Echo State Networks (Reservoir Computing).

Echo State Networks (ESN) are proper Recurrent Neural Networks:
- A large random, fixed recurrent reservoir acts as the "memory" (analogous to LSTM cells)
- Only the readout layer is trained — via ridge regression, making training instant
- Proven competitive with trained LSTMs on time-series forecasting tasks

GRU proxy uses a smaller, faster reservoir with higher leaking rate.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


class EchoStateNetwork:
    """Echo State Network — reservoir computer used as LSTM/GRU proxy."""

    def __init__(
        self,
        n_reservoir: int = 200,
        spectral_radius: float = 0.95,
        input_scaling: float = 0.5,
        leaking_rate: float = 0.3,
        ridge_alpha: float = 1e-3,
        seed: int = 42,
    ) -> None:
        rng = np.random.default_rng(seed)

        W = rng.standard_normal((n_reservoir, n_reservoir))
        eigenvalues = np.linalg.eigvals(W)
        rho = np.max(np.abs(eigenvalues))
        self.W = W * (spectral_radius / (rho + 1e-10))

        self.n_reservoir = n_reservoir
        self.input_scaling = input_scaling
        self.leaking_rate = leaking_rate
        self.ridge = Ridge(alpha=ridge_alpha, fit_intercept=True)
        self.scaler_in = StandardScaler()
        self.scaler_out = StandardScaler()
        self._Win: np.ndarray | None = None
        self._fitted = False

    def _build_win(self, n_features: int, seed: int = 42) -> None:
        rng = np.random.default_rng(seed)
        self._Win = rng.standard_normal((self.n_reservoir, n_features)) * self.input_scaling

    def _run_reservoir(self, inputs: np.ndarray) -> np.ndarray:
        """Run reservoir dynamics. inputs: (T, n_features)."""
        if inputs.ndim == 1:
            inputs = inputs.reshape(-1, 1)
        T, n_feat = inputs.shape

        if self._Win is None:
            self._build_win(n_feat)

        states = np.zeros((T, self.n_reservoir))
        state = np.zeros(self.n_reservoir)
        for t in range(T):
            pre = self.W @ state + self._Win @ inputs[t]
            state = (1 - self.leaking_rate) * state + self.leaking_rate * np.tanh(pre)
            states[t] = state
        return states

    def fit(self, X: np.ndarray, y: np.ndarray) -> "EchoStateNetwork":
        X2 = self.scaler_in.fit_transform(X.reshape(-1, 1) if X.ndim == 1 else X)
        y2 = self.scaler_out.fit_transform(y.reshape(-1, 1))
        states = self._run_reservoir(X2)
        washout = min(50, len(states) // 5)
        self.ridge.fit(states[washout:], y2[washout:].ravel())
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        X2 = self.scaler_in.transform(X.reshape(-1, 1) if X.ndim == 1 else X)
        states = self._run_reservoir(X2)
        y_s = self.ridge.predict(states)
        return self.scaler_out.inverse_transform(y_s.reshape(-1, 1)).ravel()


def _make_windows(arr: np.ndarray, lookback: int, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    X, y = [], []
    for i in range(lookback, len(arr) - horizon + 1):
        X.append(arr[i - lookback: i])
        y.append(arr[i: i + horizon])
    return np.array(X), np.array(y)


def fit_lstm_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """LSTM proxy (large ESN) — H-step autoregressive forecast."""
    try:
        arr = series.values.astype(float)
        n = len(arr)
        if n < 60:
            return {"error": "LSTM needs ≥60 observations"}

        lookback = min(30, n // 4)
        X_wins, y_wins = _make_windows(arr, lookback, horizon)
        if len(X_wins) < 20:
            return {"error": "Insufficient training windows"}

        forecasts: list[float] = []
        for h in range(horizon):
            esn = EchoStateNetwork(n_reservoir=200, spectral_radius=0.95, leaking_rate=0.3)
            esn.fit(X_wins, y_wins[:, h])
            x_last = arr[-lookback:].reshape(1, lookback)
            pred = esn.predict(x_last)
            forecasts.append(float(pred[0]))

        return {
            "model": "lstm_esn",
            "layer": "layer4",
            "forecast": forecasts,
            "last_observed": float(arr[-1]),
            "n_reservoir": 200,
            "lookback": lookback,
        }
    except Exception as exc:
        return {"error": str(exc)}


def fit_gru_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """GRU proxy (compact ESN with fast leaking) — H-step forecast."""
    try:
        arr = series.values.astype(float)
        n = len(arr)
        if n < 60:
            return {"error": "GRU needs ≥60 observations"}

        lookback = min(21, n // 5)
        X_wins, y_wins = _make_windows(arr, lookback, horizon)
        if len(X_wins) < 20:
            return {"error": "Insufficient training windows"}

        forecasts: list[float] = []
        for h in range(horizon):
            esn = EchoStateNetwork(n_reservoir=100, spectral_radius=0.90, leaking_rate=0.5)
            esn.fit(X_wins, y_wins[:, h])
            pred = esn.predict(arr[-lookback:].reshape(1, lookback))
            forecasts.append(float(pred[0]))

        return {
            "model": "gru_esn",
            "layer": "layer4",
            "forecast": forecasts,
            "last_observed": float(arr[-1]),
            "lookback": lookback,
        }
    except Exception as exc:
        return {"error": str(exc)}


def lstm_predict_fn(series: pd.Series, horizon: int) -> dict[str, Any]:
    return fit_lstm_forecast(series, horizon)


def gru_predict_fn(series: pd.Series, horizon: int) -> dict[str, Any]:
    return fit_gru_forecast(series, horizon)
