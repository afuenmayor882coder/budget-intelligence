"""Fetch Binance P2P rate for USDT/VES."""
import json
import os
import sys
from datetime import datetime, timezone

import requests

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "binance_today.json")
BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"


def fetch_binance_rate() -> float | None:
    payload = {
        "asset": "USDT",
        "fiat": "VES",
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "rows": 20,
        "tradeType": "BUY",
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    try:
        resp = requests.post(BINANCE_P2P_URL, json=payload, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"[Binance] Request failed: {e}", file=sys.stderr)
        return None

    ads = data.get("data", [])
    if not ads:
        print("[Binance] No P2P ads found", file=sys.stderr)
        return None

    prices = []
    for ad in ads[:10]:
        try:
            price = float(ad["adv"]["price"])
            max_amount = float(ad["adv"]["maxSingleTransAmount"])
            if 1 < price < 10_000 and max_amount >= 10:
                prices.append(price)
        except (KeyError, ValueError, TypeError):
            pass

    if not prices:
        print("[Binance] No valid prices extracted", file=sys.stderr)
        return None

    prices.sort()
    n = len(prices)
    median = (prices[n // 2 - 1] + prices[n // 2]) / 2 if n % 2 == 0 else prices[n // 2]
    print(f"[Binance] Median rate from {len(prices)} ads: {median:.2f} VES/USDT")
    return round(median, 2)


def run_fetch(fecha: str | None = None, output_file: str = OUTPUT_FILE) -> dict:
    """Fetch Binance rate and write JSON. Returns structured result (no sys.exit)."""
    fecha = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rate = fetch_binance_rate()

    result = {
        "success": rate is not None,
        "source": "binance",
        "fecha": fecha,
        "tasa_binance": rate,
        "carried_forward": False,
        "error": None if rate is not None else "Could not fetch Binance P2P rate",
    }

    if rate is not None:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "fecha": fecha,
                "tasa_binance": rate,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, f)
        print(f"[Binance] Saved rate {rate} to {output_file}")

    return result


if __name__ == "__main__":
    outcome = run_fetch()
    if outcome["success"]:
        sys.exit(0)
    print("[Binance] No rate fetched", file=sys.stderr)
    sys.exit(1)
