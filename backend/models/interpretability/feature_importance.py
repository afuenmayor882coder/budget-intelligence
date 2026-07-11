"""Interpretability: SHAP and permutation importance."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False

from models.layer3_ml.ml_forecaster import _build_supervised_frame, _make_estimator


def compute_permutation_importance(
    series: pd.Series,
    model_name: str = "random_forest",
    n_repeats: int = 5,
) -> dict[str, Any]:
    """Permutation importance for ML forecaster features."""
    try:
        X, y = _build_supervised_frame(series)
        estimator = _make_estimator(model_name)
        estimator.fit(X, y)

        # Unwrap pipeline for sklearn inspection
        model = estimator.named_steps["model"] if hasattr(estimator, "named_steps") else estimator
        X_fit = estimator.named_steps["scaler"].transform(X) if hasattr(estimator, "named_steps") else X

        result = permutation_importance(model, X_fit, y, n_repeats=n_repeats, random_state=42)
        importances = sorted(
            zip(X.columns, result.importances_mean),
            key=lambda x: -x[1],
        )[:10]

        return {
            "method": "permutation",
            "model": model_name,
            "top_features": [
                {"feature": f, "importance": round(float(imp), 4)}
                for f, imp in importances
            ],
        }
    except Exception as e:
        return {"error": str(e), "method": "permutation"}


def compute_shap_importance(
    series: pd.Series,
    model_name: str = "random_forest",
    max_samples: int = 200,
) -> dict[str, Any]:
    """SHAP mean absolute values for tree/linear models."""
    if not HAS_SHAP:
        return {"error": "shap not installed", "method": "shap"}

    try:
        X, y = _build_supervised_frame(series)
        if len(X) > max_samples:
            X = X.iloc[-max_samples:]
            y = y.iloc[-max_samples:]

        estimator = _make_estimator(model_name)
        estimator.fit(X, y)

        model = estimator.named_steps["model"] if hasattr(estimator, "named_steps") else estimator
        X_fit = estimator.named_steps["scaler"].transform(X) if hasattr(estimator, "named_steps") else X.values

        if model_name in ("xgboost", "lightgbm", "catboost", "random_forest"):
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_fit)
        else:
            explainer = shap.Explainer(model, X_fit)
            shap_values = explainer(X_fit).values

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        mean_abs = np.abs(shap_values).mean(axis=0)
        ranked = sorted(
            zip(X.columns, mean_abs),
            key=lambda x: -x[1],
        )[:10]

        return {
            "method": "shap",
            "model": model_name,
            "top_features": [
                {"feature": f, "shap_mean_abs": round(float(v), 4)}
                for f, v in ranked
            ],
        }
    except Exception as e:
        return {"error": str(e), "method": "shap"}


def run_interpretability(series: pd.Series, model_name: str = "random_forest") -> dict[str, Any]:
    return {
        "permutation": compute_permutation_importance(series, model_name),
        "shap": compute_shap_importance(series, model_name),
    }
