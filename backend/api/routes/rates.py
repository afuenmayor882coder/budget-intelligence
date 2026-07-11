from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query, HTTPException
from core.database import db_context
from jobs.rate_sync import sync_rates

router = APIRouter(prefix="/rates", tags=["rates"])


@router.get("")
def list_rates(limit: int = Query(365, le=3650)):
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM exchange_rates ORDER BY fecha ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/latest")
def get_latest_rate():
    with db_context() as conn:
        row = conn.execute(
            "SELECT * FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
        ).fetchone()
        if not row:
            return {}
        r = dict(row)
        # Add staleness info
        try:
            rate_date = datetime.strptime(r["fecha"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - rate_date).total_seconds() / 3600
            r["is_stale"] = age_hours > 26  # Stale if more than 26 hours old
            r["age_hours"] = round(age_hours, 1)
        except Exception:
            r["is_stale"] = True
            r["age_hours"] = None
        return r


@router.get("/gap")
def get_rate_gap(months: int = Query(12, le=60)):
    """Return BCV vs Binance gap analysis over time."""
    with db_context() as conn:
        cutoff = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")
        rows = conn.execute(
            """SELECT fecha, tasa_binance, tasa_bcv,
                      (tasa_binance - tasa_bcv) as gap_abs,
                      CASE WHEN tasa_bcv > 0 THEN (tasa_binance - tasa_bcv) / tasa_bcv * 100
                           ELSE NULL END as gap_pct
               FROM exchange_rates
               WHERE fecha >= ? AND tasa_binance IS NOT NULL AND tasa_bcv IS NOT NULL
               ORDER BY fecha""",
            (cutoff,),
        ).fetchall()
        return [dict(r) for r in rows]


@router.get("/volatility")
def get_rate_volatility(window: int = Query(30, ge=7, le=90)):
    """Return rolling volatility of log returns."""
    with db_context() as conn:
        rows = conn.execute(
            """SELECT fecha, log_return_binance, log_return_bcv
               FROM exchange_rates
               WHERE log_return_binance IS NOT NULL
               ORDER BY fecha DESC
               LIMIT ?""",
            (window * 3,),
        ).fetchall()
        if not rows:
            return {"rolling_vol_binance": None, "rolling_vol_bcv": None, "window": window}

        import math
        binance_returns = [r["log_return_binance"] for r in rows if r["log_return_binance"]]
        bcv_returns = [r["log_return_bcv"] for r in rows if r["log_return_bcv"]]

        def rolling_vol(returns, w):
            if len(returns) < 2:
                return None
            recent = returns[:w]
            n = len(recent)
            mean = sum(recent) / n
            variance = sum((x - mean) ** 2 for x in recent) / (n - 1)
            return round(math.sqrt(variance) * math.sqrt(252) * 100, 2)

        return {
            "rolling_vol_binance_pct": rolling_vol(binance_returns, window),
            "rolling_vol_bcv_pct": rolling_vol(bcv_returns, window),
            "window_days": window,
        }


@router.post("/sync")
def sync_now():
    """Trigger a manual rate sync from the configured cloud source."""
    try:
        result = sync_rates()
        return result
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {e}")


@router.get("/sync-status")
def get_sync_status():
    """Return last sync status."""
    with db_context() as conn:
        row = conn.execute(
            "SELECT * FROM sync_status WHERE id='rates'"
        ).fetchone()
        if not row:
            return {"status": "never_synced", "source": "local_only"}
        return dict(row)


@router.post("/cesta-basica/manual")
def add_cesta_manual(year: int, month: int, total_bs: float | None = None,
                     total_usd: float | None = None):
    """Manually add a Cesta Basica entry."""
    if not total_bs and not total_usd:
        raise HTTPException(400, "At least one of total_bs or total_usd is required")
    now = datetime.now(timezone.utc).isoformat()
    with db_context() as conn:
        conn.execute(
            """INSERT OR REPLACE INTO cesta_basica
               (year, month, total_bs, total_usd, source_url, fetched_at)
               VALUES (?,?,?,?,?,?)""",
            (year, month, total_bs, total_usd, "manual_entry", now),
        )
    return {"status": "ok", "year": year, "month": month}
