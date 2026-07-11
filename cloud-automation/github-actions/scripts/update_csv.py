"""Merge BCV and Binance daily fetches into rates.csv."""
import csv
import json
import math
import os
import sys
from datetime import datetime, timezone

SCRIPTS_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(SCRIPTS_DIR, "..", "data")
BCV_FILE = os.path.join(DATA_DIR, "bcv_today.json")
BINANCE_FILE = os.path.join(DATA_DIR, "binance_today.json")
RATES_CSV = os.path.join(DATA_DIR, "rates.csv")

FIELDNAMES = [
    "fecha", "tasa_binance", "tasa_bcv",
    "dif_pct_paralelo", "dif_pct_oficial",
    "log_return_binance", "log_return_bcv",
    "updated_at",
]


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_csv():
    if not os.path.exists(RATES_CSV):
        return []
    with open(RATES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def compute_log_return(current, previous):
    try:
        if current and previous and float(previous) > 0:
            return round(math.log(float(current) / float(previous)), 6)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _coerce_rate(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main():
    bcv_data = load_json(BCV_FILE)
    binance_data = load_json(BINANCE_FILE)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    fecha = bcv_data.get("fecha") or binance_data.get("fecha") or today

    tasa_bcv = _coerce_rate(bcv_data.get("tasa_bcv"))
    tasa_binance = _coerce_rate(binance_data.get("tasa_binance"))

    if tasa_bcv is None and tasa_binance is None:
        print("ERROR: No rates available for today - nothing to commit", file=sys.stderr)
        return 1

    rows = load_csv()
    prev_row = rows[-1] if rows else None
    prev_binance = _coerce_rate(prev_row.get("tasa_binance")) if prev_row else None
    prev_bcv = _coerce_rate(prev_row.get("tasa_bcv")) if prev_row else None

    if tasa_bcv is None:
        print(f"WARNING: BCV rate missing for {fecha}; row will have null tasa_bcv", file=sys.stderr)
    if tasa_binance is None:
        print(f"WARNING: Binance rate missing for {fecha}; row will have null tasa_binance", file=sys.stderr)

    dif_pct_paralelo = None
    dif_pct_oficial = None
    if tasa_binance and tasa_bcv:
        try:
            dif_pct_paralelo = round((tasa_binance - tasa_bcv) / tasa_bcv * 100, 2)
            dif_pct_oficial = round((tasa_bcv - tasa_binance) / tasa_binance * 100, 2)
        except ZeroDivisionError:
            pass

    new_row = {
        "fecha": fecha,
        "tasa_binance": tasa_binance,
        "tasa_bcv": tasa_bcv,
        "dif_pct_paralelo": dif_pct_paralelo,
        "dif_pct_oficial": dif_pct_oficial,
        "log_return_binance": compute_log_return(tasa_binance, prev_binance),
        "log_return_bcv": compute_log_return(tasa_bcv, prev_bcv),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    rows = [r for r in rows if r.get("fecha") != fecha]
    rows.append(new_row)
    rows.sort(key=lambda r: r.get("fecha", ""))

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(RATES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    null_fields = [k for k in ("tasa_binance", "tasa_bcv") if new_row.get(k) is None]
    print(
        f"Updated rates.csv: fecha={fecha} | BCV={tasa_bcv} | Binance={tasa_binance} | "
        f"Total rows={len(rows)} | null_fields={null_fields or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
