"""What-if simulation and saving plan API routes."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from core.database import db_context
from services.scenario_engine import (
    simulate_subscription_toggle,
    simulate_macro_shock,
    simulate_timeline,
    compute_goal_scenario,
)
from services.saving_planner import (
    calculate_saving_plan,
    get_all_active_goals,
    get_preset_goals,
    PRESET_GOALS,
)

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


class GoalRequest(BaseModel):
    target_usd: float
    target_name: str = "Goal"
    target_months: Optional[int] = None
    monthly_contribution: Optional[float] = None
    cancel_sub_ids: Optional[list[int]] = None


class SubToggleRequest(BaseModel):
    sub_ids: list[int]
    toggle_state: bool = False  # False = cancel, True = re-activate


class MacroShockRequest(BaseModel):
    ipc_monthly_change_pct: float = 0.0
    fx_devaluation_pct: float = 0.0
    income_change_pct: float = 0.0
    horizon_months: int = 12


@router.get("/presets")
def get_presets():
    """Return preset goal scenarios."""
    return PRESET_GOALS


@router.post("/saving-goal")
def calc_saving_goal(req: GoalRequest):
    with db_context() as conn:
        if req.cancel_sub_ids:
            return compute_goal_scenario(conn, req.target_usd, req.target_name, req.cancel_sub_ids)
        return calculate_saving_plan(
            conn,
            target_usd=req.target_usd,
            target_name=req.target_name,
            target_months=req.target_months,
            monthly_contribution=req.monthly_contribution,
        )


@router.get("/goals")
def list_active_goals():
    """Return saving plans for all active goals in DB."""
    with db_context() as conn:
        return get_all_active_goals(conn)


@router.post("/sub-toggle")
def toggle_subs(req: SubToggleRequest):
    with db_context() as conn:
        return simulate_subscription_toggle(conn, req.sub_ids, req.toggle_state)


@router.post("/macro-shock")
def macro_shock(req: MacroShockRequest):
    with db_context() as conn:
        return simulate_macro_shock(
            conn,
            ipc_monthly_change_pct=req.ipc_monthly_change_pct,
            fx_devaluation_pct=req.fx_devaluation_pct,
            income_change_pct=req.income_change_pct,
            horizon_months=req.horizon_months,
        )


@router.get("/timeline")
def get_timeline(months: int = Query(12, ge=1, le=60)):
    with db_context() as conn:
        return simulate_timeline(conn, months_ahead=months)
