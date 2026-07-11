"""Rate sync service: pulls exchange rates from configured cloud source."""
import csv
import io
import json
import logging
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any

import requests

from core.config import settings
from core.database import db_context

logger = logging.getLogger(__name__)


def _compute_log_return(current: float | None, previous: float | None) -> float | None:
    try:
        if current and previous and float(previous) > 0:
            return round(math.log(float(current) / float(previous)), 6)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _parse_csv_rows(text: str) -> list[dict]:
    """Parse rates CSV text into dicts."""
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        fecha = row.get("fecha", "").strip()
        if not fecha or len(fecha) < 8:
            continue
        def _f(key):
            v = row.get(key, "").strip()
            try:
                return float(v) if v else None
            except ValueError:
                return None
        rows.append({
            "fecha": fecha,
            "tasa_binance": _f("tasa_binance"),
            "tasa_bcv": _f("tasa_bcv"),
            "dif_pct_paralelo": _f("dif_pct_paralelo"),
            "dif_pct_oficial": _f("dif_pct_oficial"),
            "log_return_binance": _f("log_return_binance"),
            "log_return_bcv": _f("log_return_bcv"),
        })
    return rows


def fetch_from_github(url: str) -> list[dict] | None:
    """Fetch rates CSV from GitHub raw URL."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "BudgetIntelligence/2.0"})
        resp.raise_for_status()
        return _parse_csv_rows(resp.text)
    except Exception as e:
        logger.error(f"[RateSync] GitHub fetch failed: {e}")
        return None


def fetch_from_google_sheets(sheet_id: str) -> list[dict] | None:
    """Fetch rates from a publicly-shared Google Sheet as CSV."""
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=Rates"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return _parse_csv_rows(resp.text)
    except Exception as e:
        logger.error(f"[RateSync] Google Sheets fetch failed: {e}")
        return None


def upsert_rates(conn: sqlite3.Connection, rows: list[dict]) -> dict[str, int]:
    """Upsert rate rows into exchange_rates table."""
    if not rows:
        return {"inserted": 0, "updated": 0}

    inserted = 0
    updated = 0

    for row in rows:
        existing = conn.execute(
            "SELECT id FROM exchange_rates WHERE fecha=?", (row["fecha"],)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE exchange_rates
                   SET tasa_binance=?, tasa_bcv=?, dif_pct_paralelo=?,
                       dif_pct_oficial=?, log_return_binance=?, log_return_bcv=?
                   WHERE fecha=?""",
                (row["tasa_binance"], row["tasa_bcv"], row["dif_pct_paralelo"],
                 row["dif_pct_oficial"], row["log_return_binance"], row["log_return_bcv"],
                 row["fecha"]),
            )
            updated += 1
        else:
            conn.execute(
                """INSERT INTO exchange_rates
                   (fecha, tasa_binance, tasa_bcv, dif_pct_paralelo, dif_pct_oficial,
                    log_return_binance, log_return_bcv)
                   VALUES (?,?,?,?,?,?,?)""",
                (row["fecha"], row["tasa_binance"], row["tasa_bcv"],
                 row["dif_pct_paralelo"], row["dif_pct_oficial"],
                 row["log_return_binance"], row["log_return_bcv"]),
            )
            inserted += 1

    return {"inserted": inserted, "updated": updated}


def sync_rates() -> dict[str, Any]:
    """Main sync function. Returns status dict."""
    source = settings.rate_source
    now = datetime.now(timezone.utc).isoformat()

    rows = None
    source_used = "none"

    if source == "github" and settings.github_rates_url:
        rows = fetch_from_github(settings.github_rates_url)
        if rows:
            source_used = "github"

    elif source == "google_sheets" and settings.google_sheet_id:
        rows = fetch_from_google_sheets(settings.google_sheet_id)
        if rows:
            source_used = "google_sheets"

    if rows is None:
        logger.info("[RateSync] No external source available; using local DB only")
        return {
            "status": "local_only",
            "source": "local_only",
            "new_rows": 0,
            "updated_rows": 0,
            "synced_at": now,
            "message": "No cloud source configured. Using local data.",
        }

    with db_context() as conn:
        result = upsert_rates(conn, rows)
        # Record sync status
        conn.execute(
            """INSERT OR REPLACE INTO sync_status
               (id, source, synced_at, new_rows, updated_rows, status)
               VALUES ('rates', ?, ?, ?, ?, 'success')""",
            (source_used, now, result["inserted"], result["updated"]),
        )

    logger.info(
        f"[RateSync] Synced from {source_used}: "
        f"+{result['inserted']} new, {result['updated']} updated"
    )

    return {
        "status": "success",
        "source": source_used,
        "new_rows": result["inserted"],
        "updated_rows": result["updated"],
        "total_rows": len(rows),
        "synced_at": now,
    }


def sync_cesta_from_csv(csv_url: str) -> dict[str, Any]:
    """Sync cesta basica data from a CSV URL (GitHub)."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        resp = requests.get(csv_url, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return {"status": "error", "message": str(e), "synced_at": now}

    rows = []
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        try:
            year = int(row.get("year", 0))
            month = int(row.get("month", 0))
            if not year or not month:
                continue
            def _f(k):
                v = row.get(k, "").strip()
                return float(v) if v else None
            rows.append({
                "year": year, "month": month,
                "total_bs": _f("total_bs"), "total_usd": _f("total_usd"),
                "source_url": row.get("source_url", ""),
                "fetched_at": row.get("fetched_at", now),
            })
        except (ValueError, KeyError):
            pass

    if not rows:
        return {"status": "empty", "message": "No cesta rows parsed", "synced_at": now}

    with db_context() as conn:
        for r in rows:
            conn.execute(
                """INSERT OR REPLACE INTO cesta_basica
                   (year, month, total_bs, total_usd, source_url, fetched_at)
                   VALUES (?,?,?,?,?,?)""",
                (r["year"], r["month"], r["total_bs"], r["total_usd"],
                 r["source_url"], r["fetched_at"]),
            )

    return {"status": "success", "rows": len(rows), "synced_at": now}
