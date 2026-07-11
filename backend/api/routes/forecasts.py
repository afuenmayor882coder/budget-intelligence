"""Forecast and econometric model API routes — Phase 3."""
from fastapi import APIRouter, Query

from core.database import db_context
from services.forecast_service import run_forecasts
from services.macro_impact import compute_macro_impact
from models.registry.model_store import list_runs, get_best_model, load_registry
from services.explainer import explain_pipeline

router = APIRouter(prefix="/forecasts", tags=["forecasts"])


@router.get("/fx")
def get_fx_forecasts(horizon: int = Query(7, ge=1, le=90)):
    """Run Layer 1-2 FX forecast pipeline with plain-language explanations."""
    with db_context() as conn:
        return run_forecasts(conn, horizon=horizon, include_explainer=True)


@router.get("/fx/latest")
def get_cached_forecasts(horizon: int = Query(7, le=90)):
    """Return most recent cached forecasts without re-running models."""
    import json
    with db_context() as conn:
        rows = conn.execute(
            """SELECT target, forecast, created_at FROM forecast_cache
               WHERE horizon_days = ? ORDER BY created_at DESC LIMIT 10""",
            (horizon,),
        ).fetchall()
        cached = {}
        for r in rows:
            if r["target"] not in cached:
                cached[r["target"]] = {
                    "forecast": json.loads(r["forecast"]),
                    "created_at": r["created_at"],
                }
        if cached:
            return {"cached": True, "forecasts": cached}
        return run_forecasts(conn, horizon=horizon, include_explainer=True)


@router.get("/macro-impact")
def get_macro_impact():
    """Category-macro elasticities and risk scoring."""
    with db_context() as conn:
        return compute_macro_impact(conn)


@router.get("/registry")
def get_model_registry(target: str | None = None, layer: str | None = None):
    return {
        "runs": list_runs(target=target, layer=layer),
        "registry": load_registry(),
    }


@router.get("/registry/best")
def get_best_models():
    return {
        "binance": get_best_model("binance"),
        "bcv": get_best_model("bcv"),
    }


@router.post("/explain")
def explain_results(payload: dict):
    """Generate explainer verdicts for a pipeline result dict."""
    pipeline = payload.get("pipeline", payload)
    return explain_pipeline(pipeline)
