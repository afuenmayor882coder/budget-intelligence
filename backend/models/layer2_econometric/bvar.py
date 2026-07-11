"""Layer 2: Bayesian VAR with Minnesota prior (simplified)."""
from typing import Any

import numpy as np
import pandas as pd


def fit_bvar(df: pd.DataFrame, lags: int = 2, horizon: int = 7, lambda_: float = 0.2) -> dict[str, Any]:
    """
    Simplified BVAR with Minnesota-style shrinkage on VAR coefficients.
    Uses ridge penalty as practical Minnesota prior approximation.
    """
    from sklearn.linear_model import Ridge

    data = df.dropna().astype(float)
    n_vars = data.shape[1]
    n = len(data)
    if n < 30:
        return {"error": "Need at least 30 observations for BVAR"}

    lags = min(lags, n // (n_vars + 5))
    if lags < 1:
        lags = 1

    # Build lagged design matrix
    Y_list, X_list = [], []
    vals = data.values
    for t in range(lags, n):
        y = vals[t]
        x_parts = [vals[t - lag] for lag in range(1, lags + 1)]
        x = np.concatenate(x_parts + [np.ones(1)])
        Y_list.append(y)
        X_list.append(x)

    Y = np.array(Y_list)
    X = np.array(X_list)

    forecasts = {col: [] for col in data.columns}
    coeffs = {}
    last_vals = vals[-lags:].copy()

    for j, col in enumerate(data.columns):
        ridge = Ridge(alpha=lambda_ * n, fit_intercept=False)
        ridge.fit(X, Y[:, j])
        coeffs[col] = ridge.coef_.tolist()

        # Iterative multi-step forecast
        hist = [row.copy() for row in last_vals]
        col_forecasts = []
        for _ in range(horizon):
            x_parts = [hist[-lag] for lag in range(1, lags + 1)]
            x = np.concatenate(x_parts + [np.ones(1)])
            pred = float(ridge.predict(x.reshape(1, -1))[0])
            col_forecasts.append(pred)
            new_row = hist[-1].copy()
            new_row[j] = pred
            hist.append(new_row)
        forecasts[col] = col_forecasts

    return {
        "model": "BVAR",
        "lags": lags,
        "lambda": lambda_,
        "variables": list(data.columns),
        "forecast": forecasts,
        "coefficients": coeffs,
    }
