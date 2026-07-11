"""Layer 3: Tree-based and linear ML forecasters."""
from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import ElasticNet
from sklearn.neural_network import MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from models.preprocessing.features import build_calendar_features, build_lag_features, build_rolling_features

# Optional gradient boosting libraries
try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False

try:
    from catboost import CatBoostRegressor
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False


def _build_supervised_frame(series: pd.Series, max_lag: int = 30) -> tuple[pd.DataFrame, pd.Series]:
    """Build lag + rolling + calendar features aligned to target y."""
    s = series.dropna().astype(float)
    if len(s) < max_lag + 10:
        raise ValueError(f"Need at least {max_lag + 10} observations")

    lags = build_lag_features(s, lags=[1, 2, 3, 7, 14, 21, 30])
    rolls = build_rolling_features(s, windows=[7, 14, 30])
    cal = build_calendar_features(s.index)
    df = pd.concat([lags, rolls.drop(columns=["y"], errors="ignore"), cal], axis=1)
    df["y"] = s
    df = df.dropna()
    y = df.pop("y")
    return df, y


def _make_estimator(name: str):
    if name == "xgboost" and HAS_XGB:
        return xgb.XGBRegressor(
            n_estimators=120, max_depth=4, learning_rate=0.08,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
        )
    if name == "lightgbm" and HAS_LGB:
        return lgb.LGBMRegressor(
            n_estimators=120, max_depth=4, learning_rate=0.08,
            subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1,
        )
    if name == "catboost" and HAS_CATBOOST:
        return CatBoostRegressor(
            iterations=120, depth=4, learning_rate=0.08,
            random_seed=42, verbose=0,
        )
    if name == "random_forest":
        return RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42, n_jobs=-1)
    if name == "elastic_net":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("model", ElasticNet(alpha=0.05, l1_ratio=0.5, max_iter=5000)),
        ])
    if name == "mlp":
        return Pipeline([
            ("scaler", StandardScaler()),
            ("model", MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=400, random_state=42)),
        ])
    raise ValueError(f"Unknown or unavailable model: {name}")


def _recursive_forecast(
    series: pd.Series,
    estimator,
    horizon: int,
    feature_cols: list[str],
) -> np.ndarray:
    """Recursive multi-step forecast using fitted estimator."""
    history = series.dropna().astype(float).copy()
    preds = []

    for _ in range(horizon):
        lags = build_lag_features(history, lags=[1, 2, 3, 7, 14, 21, 30])
        rolls = build_rolling_features(history, windows=[7, 14, 30])
        cal = build_calendar_features(history.index)
        row = pd.concat([lags.iloc[[-1]], rolls.iloc[[-1]].drop(columns=["y"], errors="ignore"), cal.iloc[[-1]]], axis=1)
        row = row.reindex(columns=feature_cols, fill_value=0).fillna(0)
        next_val = float(estimator.predict(row)[0])
        preds.append(next_val)
        next_idx = history.index[-1] + pd.Timedelta(days=1)
        history = pd.concat([history, pd.Series([next_val], index=[next_idx])])

    return np.array(preds)


def fit_ml_forecast(series: pd.Series, model_name: str, horizon: int = 7) -> dict[str, Any]:
    """Fit ML model and produce horizon-step forecast with naive confidence band."""
    available = get_available_models()
    if model_name not in available:
        return {"error": f"Model {model_name} not available", "available": available}

    try:
        X, y = _build_supervised_frame(series)
        estimator = _make_estimator(model_name)
        estimator.fit(X, y)
        forecast = _recursive_forecast(series, estimator, horizon, list(X.columns))

        residuals = y.values - estimator.predict(X)
        std = float(np.std(residuals)) if len(residuals) > 1 else abs(forecast[0] * 0.02)
        z = 1.96

        return {
            "model": model_name,
            "layer": "layer3" if model_name not in ("mlp",) else "layer4",
            "forecast": forecast.tolist(),
            "lower_95": (forecast - z * std).tolist(),
            "upper_95": (forecast + z * std).tolist(),
            "residual_std": std,
            "n_train": len(y),
            "feature_count": X.shape[1],
        }
    except Exception as e:
        return {"error": str(e), "model": model_name}


def ml_predict_fn(model_name: str) -> Callable[[pd.Series, int], np.ndarray]:
    def predict(train: pd.Series, horizon: int) -> np.ndarray:
        result = fit_ml_forecast(train, model_name, horizon)
        if "forecast" not in result:
            raise ValueError(result.get("error", f"{model_name} failed"))
        return np.array(result["forecast"])
    return predict


def get_available_models() -> list[str]:
    models = ["random_forest", "elastic_net", "mlp"]
    if HAS_XGB:
        models.insert(0, "xgboost")
    if HAS_LGB:
        models.insert(1 if HAS_XGB else 0, "lightgbm")
    if HAS_CATBOOST:
        models.append("catboost")
    return models


def build_layer3_registry() -> dict:
    registry = {}
    for name in get_available_models():
        layer = "layer4" if name == "mlp" else "layer3"

        def _fit_factory(model_name: str):
            def fit(s: pd.Series, horizon: int = 7):
                return fit_ml_forecast(s, model_name, horizon)
            return fit

        registry[name] = {
            "fit": _fit_factory(name),
            "predict_fn": ml_predict_fn(name),
            "layer": layer,
        }
    return registry
