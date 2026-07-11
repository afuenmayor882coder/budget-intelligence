"""Daily exchange rate orchestrator with carry-forward resilience."""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
RATES_CSV = os.path.join(DATA_DIR, "rates.csv")
BCV_FILE = os.path.join(DATA_DIR, "bcv_today.json")
BINANCE_FILE = os.path.join(DATA_DIR, "binance_today.json")
SYNC_META_FILE = os.path.join(DATA_DIR, "sync_meta.json")

from fetch_bcv import run_fetch as fetch_bcv  # noqa: E402
from fetch_binance import run_fetch as fetch_binance  # noqa: E402
from update_csv import main as update_csv  # noqa: E402


def _coerce_rate(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _last_known_rates() -> dict:
    if not os.path.exists(RATES_CSV):
        return {}
    with open(RATES_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    last = rows[-1]
    return {
        "fecha": last.get("fecha"),
        "tasa_bcv": _coerce_rate(last.get("tasa_bcv")),
        "tasa_binance": _coerce_rate(last.get("tasa_binance")),
    }


def _write_json(path: str, payload: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)


def _write_sync_meta(fecha: str, bcv_result: dict, binance_result: dict) -> None:
    meta = {
        "last_successful_run": datetime.now(timezone.utc).isoformat(),
        "last_fecha": fecha,
        "bcv": {
            "success": bcv_result.get("success"),
            "carried_forward": bcv_result.get("carried_forward", False),
            "tasa_bcv": bcv_result.get("tasa_bcv"),
        },
        "binance": {
            "success": binance_result.get("success"),
            "carried_forward": binance_result.get("carried_forward", False),
            "tasa_binance": binance_result.get("tasa_binance"),
        },
    }
    _write_json(SYNC_META_FILE, meta)


def main() -> int:
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fallback = _last_known_rates()

    bcv_result = fetch_bcv(fecha=fecha, output_file=BCV_FILE)
    binance_result = fetch_binance(fecha=fecha, output_file=BINANCE_FILE)

    if not bcv_result["success"]:
        if fallback.get("tasa_bcv") is not None:
            bcv_result["tasa_bcv"] = fallback["tasa_bcv"]
            bcv_result["carried_forward"] = True
            bcv_result["success"] = True
            _write_json(BCV_FILE, {
                "fecha": fecha,
                "tasa_bcv": fallback["tasa_bcv"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "carried_forward": True,
            })
            print(
                f"[Orchestrator] BCV fetch failed; carried forward {fallback['tasa_bcv']} "
                f"from {fallback.get('fecha')}",
                file=sys.stderr,
            )
        else:
            print("[Orchestrator] BCV fetch failed and no fallback available", file=sys.stderr)

    if not binance_result["success"]:
        if fallback.get("tasa_binance") is not None:
            binance_result["tasa_binance"] = fallback["tasa_binance"]
            binance_result["carried_forward"] = True
            binance_result["success"] = True
            _write_json(BINANCE_FILE, {
                "fecha": fecha,
                "tasa_binance": fallback["tasa_binance"],
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "carried_forward": True,
            })
            print(
                f"[Orchestrator] Binance fetch failed; carried forward {fallback['tasa_binance']} "
                f"from {fallback.get('fecha')}",
                file=sys.stderr,
            )
        else:
            print("[Orchestrator] Binance fetch failed and no fallback available", file=sys.stderr)

    has_bcv = bcv_result.get("tasa_bcv") is not None
    has_binance = binance_result.get("tasa_binance") is not None

    if not has_bcv and not has_binance:
        print("ERROR: Both sources failed with no carry-forward fallback", file=sys.stderr)
        return 1

    update_status = update_csv()
    if update_status != 0:
        return update_status

    _write_sync_meta(fecha, bcv_result, binance_result)
    print(
        f"[Orchestrator] Complete for {fecha} | "
        f"BCV={'live' if bcv_result['success'] and not bcv_result.get('carried_forward') else 'carry-forward' if bcv_result.get('carried_forward') else 'missing'} | "
        f"Binance={'live' if binance_result['success'] and not binance_result.get('carried_forward') else 'carry-forward' if binance_result.get('carried_forward') else 'missing'}"
    )
    return 0


if __name__ == "__main__":
    os.chdir(SCRIPTS_DIR)
    raise SystemExit(main())
