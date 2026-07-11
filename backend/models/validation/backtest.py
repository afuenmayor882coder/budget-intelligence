"""Full backtest orchestrator — Phase 4 complete (Layers 1-5 + Layer 4 deep + ensemble)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from models.layer1_classical.arima_sarima import arima_predict_fn, fit_arima_forecast
from models.layer1_classical.ets_holt_winters import ets_predict_fn, fit_ets_forecast
from models.layer1_classical.theta import theta_predict_fn, fit_theta_forecast
from models.layer2_econometric.var_model import fit_var
from models.layer2_econometric.bvar import fit_bvar
from models.layer3_ml.ml_forecaster import fit_ml_forecast, ml_predict_fn, get_available_models
from models.layer4_deep.lstm_gru import fit_lstm_forecast, fit_gru_forecast, lstm_predict_fn, gru_predict_fn
from models.layer4_deep.nbeats import fit_nbeats_forecast, nbeats_predict_fn
from models.layer4_deep.temporal_fusion import fit_tft_forecast, tft_predict_fn
from models.layer4_deep.deepar import fit_deepar_forecast, deepar_predict_fn
from models.layer5_bayesian.garch_egarch import fit_garch_volatility
from models.layer5_bayesian.hmm_regimes import fit_hmm_regimes
from models.layer5_bayesian.state_space_kalman import fit_kalman_trend
from models.layer5_bayesian.markov_switching import fit_markov_switching
from models.validation.cv_rolling import rolling_cv
from models.ensemble.model_selection import diebold_mariano
from models.ensemble.mcs import model_confidence_set
from models.ensemble.ensemble import build_full_ensemble
from models.preprocessing.anomaly_detection import run_anomaly_detection
from models.interpretability.feature_importance import run_interpretability
from models.scenario.monte_carlo import monte_carlo_fx_simulation
from models.registry.model_store import register_run


LAYER1_MODELS = {
    "arima": {"fit": fit_arima_forecast, "predict_fn": arima_predict_fn, "layer": "layer1"},
    "ets": {"fit": fit_ets_forecast, "predict_fn": ets_predict_fn, "layer": "layer1"},
    "theta": {"fit": fit_theta_forecast, "predict_fn": theta_predict_fn, "layer": "layer1"},
}


def _build_layer4_models() -> dict:
    """Layer 4 deep learning models (ESN/LSTM, GRU, N-BEATS, TFT, DeepAR)."""
    return {
        "lstm": {"fit": fit_lstm_forecast, "predict_fn": lstm_predict_fn, "layer": "layer4"},
        "gru": {"fit": fit_gru_forecast, "predict_fn": gru_predict_fn, "layer": "layer4"},
        "nbeats": {"fit": fit_nbeats_forecast, "predict_fn": nbeats_predict_fn, "layer": "layer4"},
        "tft": {"fit": fit_tft_forecast, "predict_fn": tft_predict_fn, "layer": "layer4"},
        "deepar": {"fit": fit_deepar_forecast, "predict_fn": deepar_predict_fn, "layer": "layer4"},
    }


def _build_layer3_models() -> dict:
    models = {}
    for name in get_available_models():
        layer = "layer4" if name == "mlp" else "layer3"

        def _fit_factory(model_name: str):
            def fit(s: pd.Series, horizon: int = 7):
                return fit_ml_forecast(s, model_name, horizon)
            return fit

        models[name] = {
            "fit": _fit_factory(name),
            "predict_fn": ml_predict_fn(name),
            "layer": layer,
        }
    return models


def get_all_forecast_models() -> dict:
    return {**LAYER1_MODELS, **_build_layer3_models(), **_build_layer4_models()}


def backtest_univariate(
    series: pd.Series,
    target_name: str,
    horizon: int = 7,
    conn=None,
    include_ml: bool = True,
) -> dict[str, Any]:
    """Backtest all Layer 1 + Layer 3/4 models on a univariate series."""
    models = dict(LAYER1_MODELS)
    if include_ml:
        models.update(_build_layer3_models())

    results = {}
    errors = {}

    for name, spec in models.items():
        cv = rolling_cv(
            series, spec["predict_fn"], horizon=horizon,
            initial_train=max(60, len(series) // 3),
        )
        results[name] = cv

        if cv.get("summary"):
            register_run(
                model_name=name,
                layer=spec["layer"],
                target=target_name,
                metrics=cv["summary"],
                conn=conn,
            )

        fold_errors = []
        for fold in cv.get("folds", []):
            if "metrics" in fold:
                fold_errors.append(fold["metrics"].get("mae", np.nan))
        if fold_errors:
            errors[name] = np.array(fold_errors)

    comparisons = []
    names = list(errors.keys())
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if len(errors[names[i]]) == len(errors[names[j]]):
                dm = diebold_mariano(errors[names[i]], errors[names[j]], loss="absolute")
                comparisons.append({"model_a": names[i], "model_b": names[j], **dm})

    mcs = model_confidence_set(errors) if errors else {}

    best = None
    best_mae = float("inf")
    for name, cv in results.items():
        mae = cv.get("summary", {}).get("mae")
        if mae is not None and mae < best_mae:
            best_mae = mae
            best = name

    return {
        "target": target_name,
        "horizon": horizon,
        "models": results,
        "comparisons": comparisons,
        "mcs": mcs,
        "best_model": best,
        "best_mae": best_mae if best else None,
    }


def run_fx_forecast_pipeline(
    rates_df: pd.DataFrame,
    horizon: int = 7,
    conn=None,
) -> dict[str, Any]:
    """
    Full Phase 4 FX forecast pipeline.
    rates_df columns: fecha (index), tasa_binance, tasa_bcv
    """
    df = rates_df.copy()
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df.set_index("fecha")
    df = df.sort_index()

    output: dict[str, Any] = {
        "horizon": horizon,
        "generated_at": pd.Timestamp.now().isoformat(),
        "phase": 4,
    }

    all_models = get_all_forecast_models()

    for col, target in [("tasa_binance", "binance"), ("tasa_bcv", "bcv")]:
        if col not in df.columns or df[col].dropna().empty:
            continue
        series = df[col].dropna()
        output[f"{target}_backtest"] = backtest_univariate(series, target, horizon=horizon, conn=conn)

        forecasts = {}
        mae_by_model = {}
        for name, spec in all_models.items():
            try:
                fc = spec["fit"](series, horizon=horizon)
                forecasts[name] = fc
                mae = output[f"{target}_backtest"]["models"].get(name, {}).get("summary", {}).get("mae")
                if mae is not None:
                    mae_by_model[name] = mae
            except Exception as e:
                forecasts[name] = {"error": str(e)}

        output[f"{target}_forecasts"] = forecasts

        # Extract point forecasts for ensemble
        point_forecasts = {
            name: fc["forecast"]
            for name, fc in forecasts.items()
            if isinstance(fc, dict) and "forecast" in fc
        }

        # Layer 5: GARCH + HMM on this series
        garch = fit_garch_volatility(series, model_type="GARCH", horizon=horizon)
        egarch = fit_garch_volatility(series, model_type="EGARCH", horizon=horizon)
        hmm = fit_hmm_regimes(series)
        kalman = fit_kalman_trend(series, horizon=horizon)
        markov = fit_markov_switching(series)

        output[f"{target}_garch"] = garch
        output[f"{target}_egarch"] = egarch
        output[f"{target}_hmm"] = hmm
        output[f"{target}_kalman"] = kalman
        output[f"{target}_markov"] = markov

        vol_ratio = garch.get("volatility_ratio", 1.0) if isinstance(garch, dict) else 1.0
        ensemble_result = build_full_ensemble(point_forecasts, mae_by_model, garch_vol_ratio=vol_ratio)
        output[f"{target}_ensemble"] = ensemble_result.get("primary", {})
        output[f"{target}_ensemble_methods"] = ensemble_result.get("methods", {})

        # Anomaly detection
        output[f"{target}_anomalies"] = run_anomaly_detection(series)

        # Interpretability on best ML model
        bt = output[f"{target}_backtest"]
        ml_candidates = [m for m in get_available_models() if m in bt.get("models", {})]
        best_ml = None
        best_ml_mae = float("inf")
        for m in ml_candidates:
            mae = bt["models"][m].get("summary", {}).get("mae")
            if mae is not None and mae < best_ml_mae:
                best_ml_mae = mae
                best_ml = m
        if best_ml:
            output[f"{target}_interpretability"] = run_interpretability(series, best_ml)

        # Monte Carlo FX simulation
        garch_vol = garch.get("current_volatility_pct") if isinstance(garch, dict) else None
        output[f"{target}_monte_carlo"] = monte_carlo_fx_simulation(
            series, horizon_days=horizon, n_simulations=300, garch_vol=garch_vol,
        )

    # Multivariate VAR/BVAR (Layer 2)
    mv_cols = [c for c in ["tasa_binance", "tasa_bcv"] if c in df.columns]
    if len(mv_cols) >= 2:
        mv = df[mv_cols].dropna()
        output["var"] = fit_var(mv, horizon=horizon)
        output["bvar"] = fit_bvar(mv, horizon=horizon)

        from models.layer2_econometric.cointegration import johansen_test, engle_granger_test
        from models.layer2_econometric.granger_causality import granger_pairwise
        from models.layer2_econometric.impulse_response import compute_irf
        from models.layer2_econometric.structural_breaks import detect_structural_breaks
        from models.layer2_econometric.vecm import fit_vecm
        from models.preprocessing.stationarity import run_stationarity_tests

        output["cointegration"] = johansen_test(mv)
        if len(mv_cols) == 2:
            output["engle_granger"] = engle_granger_test(mv.iloc[:, 0], mv.iloc[:, 1])
        output["granger"] = granger_pairwise(mv)
        output["irf"] = compute_irf(mv, periods=14, shock_var="tasa_binance")
        output["vecm"] = fit_vecm(mv, horizon=horizon)

        for col in mv_cols:
            output[f"stationarity_{col}"] = run_stationarity_tests(mv[col], name=col)
            output[f"breaks_{col}"] = detect_structural_breaks(mv[col])

    # Hierarchical spending forecast
    if conn is not None:
        try:
            from models.spending.hierarchical_forecast import (
                load_category_spending, forecast_spending_hierarchy,
            )
            cat_data = load_category_spending(conn)
            if cat_data:
                output["spending_hierarchy"] = forecast_spending_hierarchy(cat_data, horizon=3)
        except Exception as e:
            output["spending_hierarchy"] = {"error": str(e)}

    return output
