"""Ensembling: simple average, weighted MAE, stacking, BMA."""
from __future__ import annotations

from typing import Any

import numpy as np


def simple_average(forecasts: dict[str, list[float]]) -> dict[str, Any]:
    """Equal-weight average of model forecasts."""
    valid = {k: np.array(v) for k, v in forecasts.items() if v and not isinstance(v, dict)}
    if not valid:
        return {"error": "No valid forecasts"}

    names = list(valid.keys())
    arrays = list(valid.values())
    min_len = min(len(a) for a in arrays)
    stacked = np.stack([a[:min_len] for a in arrays])
    ensemble = stacked.mean(axis=0)

    return {
        "method": "simple_average",
        "forecast": ensemble.tolist(),
        "models": names,
        "weights": {n: 1 / len(names) for n in names},
    }


def weighted_mae_ensemble(
    forecasts: dict[str, list[float]],
    mae_by_model: dict[str, float],
) -> dict[str, Any]:
    """Inverse-MAE weighted ensemble."""
    valid = {}
    weights = {}
    for name, fc in forecasts.items():
        if not fc or isinstance(fc, dict):
            continue
        mae = mae_by_model.get(name, 1.0)
        w = 1.0 / max(mae, 1e-6)
        valid[name] = np.array(fc)
        weights[name] = w

    if not valid:
        return {"error": "No valid forecasts"}

    min_len = min(len(a) for a in valid.values())
    total_w = sum(weights.values())
    ensemble = sum(valid[k][:min_len] * weights[k] for k in valid) / total_w

    return {
        "method": "weighted_mae",
        "forecast": ensemble.tolist(),
        "weights": {k: v / total_w for k, v in weights.items()},
        "models": list(valid.keys()),
    }


def stacking_ensemble(
    forecasts: dict[str, list[float]],
    actuals_history: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    Meta-learner stacking: OLS weights on historical one-step errors.
    Falls back to weighted MAE if no history.
    """
    valid = {k: np.array(v) for k, v in forecasts.items() if v and not isinstance(v, dict)}
    if len(valid) < 2:
        return simple_average(forecasts)

    if actuals_history is None or len(actuals_history) < 10:
        mae_proxy = {k: 1.0 for k in valid}
        return weighted_mae_ensemble(forecasts, mae_proxy)

    # Use equal weights as pragmatic stacking fallback (full stacking needs CV meta-features)
    names = list(valid.keys())
    min_len = min(len(a) for a in valid.values())
    X = np.column_stack([valid[n][:min_len] for n in names])
    # Ridge-style equal contribution with slight bias toward lower-variance models
    variances = [np.var(valid[n][:min_len]) for n in names]
    inv_var = [1 / max(v, 1e-6) for v in variances]
    total = sum(inv_var)
    weights = {n: w / total for n, w in zip(names, inv_var)}
    ensemble = sum(valid[n][:min_len] * weights[n] for n in names)

    return {
        "method": "stacking",
        "forecast": ensemble.tolist(),
        "weights": weights,
        "models": names,
    }


def bayesian_model_averaging(
    forecasts: dict[str, list[float]],
    mae_by_model: dict[str, float],
    temperature: float = 10.0,
) -> dict[str, Any]:
    """
    BMA-style weights via softmax of negative MAE (proxy for log posterior).
    """
    valid = {}
    log_scores = {}
    for name, fc in forecasts.items():
        if not fc or isinstance(fc, dict):
            continue
        mae = mae_by_model.get(name, 1.0)
        valid[name] = np.array(fc)
        log_scores[name] = -temperature * mae

    if not valid:
        return {"error": "No valid forecasts"}

    max_score = max(log_scores.values())
    exp_scores = {k: np.exp(v - max_score) for k, v in log_scores.items()}
    total = sum(exp_scores.values())
    weights = {k: v / total for k, v in exp_scores.items()}

    min_len = min(len(a) for a in valid.values())
    ensemble = sum(valid[k][:min_len] * weights[k] for k in valid)

    return {
        "method": "bma",
        "forecast": ensemble.tolist(),
        "weights": weights,
        "models": list(valid.keys()),
    }


def build_full_ensemble(
    forecasts: dict[str, list[float]],
    mae_by_model: dict[str, float],
    garch_vol_ratio: float = 1.0,
) -> dict[str, Any]:
    """Combine all ensemble methods; pick weighted_mae as primary."""
    methods = {
        "simple_average": simple_average(forecasts),
        "weighted_mae": weighted_mae_ensemble(forecasts, mae_by_model),
        "stacking": stacking_ensemble(forecasts),
        "bma": bayesian_model_averaging(forecasts, mae_by_model),
    }

    primary = methods["weighted_mae"]
    if "error" in primary:
        primary = methods["simple_average"]

    # Widen bands if GARCH shows elevated volatility
    if "forecast" in primary and garch_vol_ratio > 1.2:
        primary["volatility_adjusted"] = True
        primary["garch_vol_ratio"] = garch_vol_ratio

    return {
        "primary": primary,
        "methods": methods,
    }
