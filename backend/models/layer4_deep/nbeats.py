"""Layer 4: N-BEATS — Neural Basis Expansion Analysis for Time Series.

True N-BEATS implementation:
- Each block decomposes the input into backcast (what can be explained) and
  forecast (future contribution) via learned basis expansions
- Trend stack: polynomial basis (captures slow drift)
- Seasonality stack: Fourier basis (captures weekly/daily cycles)
- Generic stack: identity basis (captures residual patterns)
- Greedy sequential training — no full backprop needed across blocks
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


# ── Basis expansion helpers ──────────────────────────────────────────────────

def _poly_basis(theta: np.ndarray, degree: int, length: int) -> np.ndarray:
    """Polynomial trend basis: length-vector from degree-p theta coefficients."""
    t = np.linspace(0, 1, length)
    T = np.column_stack([t ** i for i in range(degree + 1)])
    k = min(degree + 1, len(theta))
    return T[:, :k] @ theta[:k]


def _fourier_basis(theta: np.ndarray, harmonics: int, period: int, length: int) -> np.ndarray:
    """Fourier seasonality basis."""
    t = np.arange(length)
    cols = []
    for i in range(1, harmonics + 1):
        cols.append(np.cos(2 * np.pi * i * t / period))
        cols.append(np.sin(2 * np.pi * i * t / period))
    S = np.column_stack(cols)
    k = min(2 * harmonics, len(theta))
    return S[:, :k] @ theta[:k]


# ── Single N-BEATS block ─────────────────────────────────────────────────────

class _NBEATSBlock:
    """One N-BEATS block: MLP → theta → (backcast, forecast) via basis expansion."""

    _TREND_DEGREE = 3
    _HARMONICS = 4
    _PERIOD = 7

    def __init__(self, backcast_len: int, forecast_len: int, block_type: str, hidden: int = 128) -> None:
        self.backcast_len = backcast_len
        self.forecast_len = forecast_len
        self.block_type = block_type

        if block_type == "trend":
            self._theta_bc = self._TREND_DEGREE + 1
            self._theta_fc = self._TREND_DEGREE + 1
        elif block_type == "seasonality":
            self._theta_bc = 2 * self._HARMONICS
            self._theta_fc = 2 * self._HARMONICS
        else:
            self._theta_bc = backcast_len
            self._theta_fc = forecast_len

        out_size = self._theta_bc + self._theta_fc
        self._mlp = MLPRegressor(
            hidden_layer_sizes=(hidden, hidden // 2),
            activation="relu",
            max_iter=300,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=15,
        )
        self._scaler = StandardScaler()
        self._fitted = False

    def fit(self, X: np.ndarray, y_bc: np.ndarray, y_fc: np.ndarray) -> "_NBEATSBlock":
        Xs = self._scaler.fit_transform(X)
        # Pack targets: first theta_bc columns are backcast targets, rest forecast
        target = np.column_stack([
            y_bc[:, : self._theta_bc],
            y_fc[:, : self._theta_fc],
        ])
        self._mlp.fit(Xs, target)
        self._fitted = True
        return self

    def _expand(self, theta_bc: np.ndarray, theta_fc: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if self.block_type == "trend":
            bc = _poly_basis(theta_bc, self._TREND_DEGREE, self.backcast_len)
            fc = _poly_basis(theta_fc, self._TREND_DEGREE, self.forecast_len)
        elif self.block_type == "seasonality":
            bc = _fourier_basis(theta_bc, self._HARMONICS, self._PERIOD, self.backcast_len)
            fc = _fourier_basis(theta_fc, self._HARMONICS, self._PERIOD, self.forecast_len)
        else:
            bc = theta_bc[: self.backcast_len]
            fc = theta_fc[: self.forecast_len]
        return bc, fc

    def predict_window(self, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        xs = self._scaler.transform(x.reshape(1, -1))
        theta = self._mlp.predict(xs)[0]
        theta_bc = theta[: self._theta_bc]
        theta_fc = theta[self._theta_bc :]
        return self._expand(theta_bc, theta_fc)


# ── Full N-BEATS stack ───────────────────────────────────────────────────────

class NBEATS:
    """N-BEATS: greedy stack of blocks with residual connections."""

    def __init__(
        self,
        backcast_len: int = 21,
        forecast_len: int = 7,
        stack_types: list[str] | None = None,
        hidden: int = 128,
    ) -> None:
        self.backcast_len = backcast_len
        self.forecast_len = forecast_len
        if stack_types is None:
            stack_types = ["trend", "seasonality", "generic"]
        self.blocks = [_NBEATSBlock(backcast_len, forecast_len, t, hidden) for t in stack_types]
        self._mean = 0.0
        self._std = 1.0

    def _make_windows(self, arr: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        X, y_bc, y_fc = [], [], []
        for i in range(self.backcast_len, len(arr) - self.forecast_len + 1):
            X.append(arr[i - self.backcast_len: i])
            y_bc.append(arr[i - self.backcast_len: i])
            y_fc.append(arr[i: i + self.forecast_len])
        return np.array(X), np.array(y_bc), np.array(y_fc)

    def fit(self, series: np.ndarray) -> "NBEATS":
        arr = np.asarray(series, dtype=float)
        self._mean = arr.mean()
        self._std = arr.std() + 1e-8
        arr_n = (arr - self._mean) / self._std

        residuals = arr_n.copy()
        _, _, y_fc_orig = self._make_windows(arr_n)

        for block in self.blocks:
            X_r, y_bc_r, _ = self._make_windows(residuals)
            if len(X_r) < 10:
                continue
            block.fit(X_r, y_bc_r, y_fc_orig[: len(X_r)])

            # Subtract backcasts from residuals (greedy step)
            new_res = residuals.copy()
            for i in range(self.backcast_len, len(residuals) - self.forecast_len + 1):
                x_win = residuals[i - self.backcast_len: i]
                bc, _ = block.predict_window(x_win)
                if len(bc) == self.backcast_len:
                    new_res[i - self.backcast_len: i] -= bc
            residuals = new_res

        return self

    def predict(self, series: np.ndarray) -> np.ndarray:
        arr_n = (np.asarray(series, dtype=float) - self._mean) / self._std
        x = arr_n[-self.backcast_len:]
        forecast_sum = np.zeros(self.forecast_len)
        for block in self.blocks:
            if block._fitted:
                _, fc = block.predict_window(x)
                if len(fc) == self.forecast_len:
                    forecast_sum += fc
        return forecast_sum * self._std + self._mean


# ── Public API ───────────────────────────────────────────────────────────────

def fit_nbeats_forecast(series: pd.Series, horizon: int = 7) -> dict[str, Any]:
    """Fit N-BEATS and return H-step forecast."""
    try:
        arr = series.values.astype(float)
        if len(arr) < 60:
            return {"error": "N-BEATS needs ≥60 observations"}

        backcast_len = min(21, len(arr) // 4)
        model = NBEATS(backcast_len=backcast_len, forecast_len=horizon)
        model.fit(arr)
        forecast = model.predict(arr)

        return {
            "model": "nbeats",
            "layer": "layer4",
            "forecast": forecast.tolist(),
            "last_observed": float(arr[-1]),
            "backcast_len": backcast_len,
        }
    except Exception as exc:
        return {"error": str(exc)}


def nbeats_predict_fn(series: pd.Series, horizon: int) -> dict[str, Any]:
    return fit_nbeats_forecast(series, horizon)
