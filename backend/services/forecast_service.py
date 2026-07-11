"""Forecast service — orchestrates Phase 4 modeling pipeline (Layers 1-5)."""
import json
from datetime import datetime, timezone

import pandas as pd

from models.validation.backtest import run_fx_forecast_pipeline
from models.registry.model_store import list_runs, get_best_model
from services.explainer import explain_pipeline


def load_rates_dataframe(conn) -> pd.DataFrame:
    rows = conn.execute(
        "SELECT fecha, tasa_binance, tasa_bcv FROM exchange_rates ORDER BY fecha"
    ).fetchall()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([dict(r) for r in rows])


def run_forecasts(conn, horizon: int = 7, include_explainer: bool = True) -> dict:
    df = load_rates_dataframe(conn)
    if df.empty:
        return {"error": "No exchange rate data available. Upload rates or sync from cloud."}

    pipeline = run_fx_forecast_pipeline(df, horizon=horizon, conn=conn)

    # Cache forecasts in SQLite
    for target in ["binance", "bcv"]:
        ensemble = pipeline.get(f"{target}_ensemble")
        if not ensemble:
            continue
        conn.execute(
            """INSERT INTO forecast_cache (model_run_id, horizon_days, target, forecast, confidence_bands)
               VALUES (NULL, ?, ?, ?, NULL)""",
            (horizon, target, json.dumps(ensemble)),
        )

    result = {
        "horizon": horizon,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "registry": {
            "recent_runs": list_runs()[-10:],
            "best_binance": get_best_model("binance"),
            "best_bcv": get_best_model("bcv"),
        },
    }

    if include_explainer:
        result["explanations"] = explain_pipeline(pipeline)

    return result
