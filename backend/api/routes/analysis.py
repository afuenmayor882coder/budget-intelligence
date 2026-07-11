"""Analysis API routes: narrative, purchasing power, KPIs."""
from fastapi import APIRouter, Query
from core.database import db_context
from services.calculations import compute_kpis, get_monthly_series, get_monthly_summary, compute_runway
from services.purchasing_power import compute_purchasing_power
from services.narrative.pipeline import generate_all_narratives, generate_section_narrative
from services.narrative.personalization import (
    record_insight_click, record_insight_dismiss,
    get_narrative_density
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/kpis")
def get_kpis():
    with db_context() as conn:
        return compute_kpis(conn)


@router.get("/monthly-series")
def get_monthly_series_route(months: int = Query(12, le=60)):
    with db_context() as conn:
        return get_monthly_series(conn, months)


@router.get("/monthly-summary")
def get_monthly_summary_route(year: int | None = None, month: int | None = None):
    with db_context() as conn:
        return get_monthly_summary(conn, year, month)


@router.get("/runway")
def get_runway(projection_days: int = Query(180, le=365)):
    with db_context() as conn:
        return compute_runway(conn, projection_days)


@router.get("/purchasing-power")
def get_purchasing_power():
    with db_context() as conn:
        return compute_purchasing_power(conn)


@router.get("/narrative")
def get_full_narrative():
    """Generate all narratives for the full app."""
    with db_context() as conn:
        density = get_narrative_density(conn)
        return generate_all_narratives(conn, density=density)


@router.get("/narrative/{section}")
def get_section_narrative(section: str):
    """Generate narrative for a specific section."""
    with db_context() as conn:
        density = get_narrative_density(conn)
        text = generate_section_narrative(conn, section, density=density)
        return {"section": section, "text": text}


@router.post("/narrative/insight/{insight_id}/click")
def click_insight(insight_id: str):
    """Record user clicking/expanding an insight."""
    with db_context() as conn:
        record_insight_click(conn, insight_id)
    return {"status": "ok"}


@router.post("/narrative/insight/{insight_id}/dismiss")
def dismiss_insight(insight_id: str):
    """Record user dismissing an insight."""
    with db_context() as conn:
        record_insight_dismiss(conn, insight_id)
    return {"status": "ok"}
