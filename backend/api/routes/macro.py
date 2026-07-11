from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime, timezone
from core.database import db_context

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/ipc")
def get_ipc(months: int = Query(120, le=600)):
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM macro_ipc ORDER BY year, month DESC LIMIT ?",
            (months,),
        ).fetchall()
        return sorted([dict(r) for r in rows], key=lambda r: (r["year"], r["month"]))


@router.get("/ipc/latest")
def get_ipc_latest():
    with db_context() as conn:
        row = conn.execute(
            "SELECT * FROM macro_ipc ORDER BY year DESC, month DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}


@router.get("/liquidity")
def get_liquidity():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM macro_liquidity ORDER BY year, month"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/gdp")
def get_gdp():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM macro_gdp ORDER BY year, quarter"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/oil")
def get_oil():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM macro_oil ORDER BY year"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/parallel-rate")
def get_parallel_rate():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM parallel_rate_monthly ORDER BY year, month"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/cesta-basica")
def get_cesta_basica():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM cesta_basica ORDER BY year, month"
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/cesta-basica/latest")
def get_cesta_latest():
    with db_context() as conn:
        row = conn.execute(
            "SELECT * FROM cesta_basica ORDER BY year DESC, month DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else {}


class CestaManualEntry(BaseModel):
    year: int
    month: int
    total_bs: float | None = None
    total_usd: float | None = None


@router.post("/cesta-basica/manual")
def add_cesta_manual(entry: CestaManualEntry):
    if not entry.total_bs and not entry.total_usd:
        raise HTTPException(400, "At least one of total_bs or total_usd is required")
    now = datetime.now(timezone.utc).isoformat()
    with db_context() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO cesta_basica
               (year, month, total_bs, total_usd, source_url, fetched_at)
               VALUES (?,?,?,?,?,?)""",
            (entry.year, entry.month, entry.total_bs, entry.total_usd, "manual_entry", now),
        )
    return {"status": "ok", "year": entry.year, "month": entry.month}


@router.get("/summary")
def get_macro_summary():
    """Return latest values for all macro indicators for the dashboard strip."""
    with db_context() as conn:
        ipc = conn.execute(
            "SELECT year, month, indice, var_pct FROM macro_ipc ORDER BY year DESC, month DESC LIMIT 2"
        ).fetchall()
        ipc_rows = [dict(r) for r in ipc]

        liq = conn.execute(
            "SELECT year, month, m2 FROM macro_liquidity ORDER BY year DESC, month DESC LIMIT 2"
        ).fetchall()
        liq_rows = [dict(r) for r in liq]

        rate = conn.execute(
            "SELECT fecha, tasa_binance, tasa_bcv FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
        ).fetchone()

        cesta = conn.execute(
            "SELECT year, month, total_bs, total_usd FROM cesta_basica ORDER BY year DESC, month DESC LIMIT 1"
        ).fetchone()

        oil = conn.execute(
            "SELECT year, revenue_usd_bn FROM macro_oil ORDER BY year DESC LIMIT 1"
        ).fetchone()

        return {
            "ipc_latest": ipc_rows[0] if ipc_rows else None,
            "ipc_prev": ipc_rows[1] if len(ipc_rows) > 1 else None,
            "liquidity_latest": liq_rows[0] if liq_rows else None,
            "liquidity_prev": liq_rows[1] if len(liq_rows) > 1 else None,
            "rate_latest": dict(rate) if rate else None,
            "cesta_latest": dict(cesta) if cesta else None,
            "oil_latest": dict(oil) if oil else None,
        }
