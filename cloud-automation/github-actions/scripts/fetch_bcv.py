"""Fetch BCV official exchange rate from BCV website."""
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.exceptions import SSLError

BCV_URL = "https://www.bcv.org.ve/"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "bcv_today.json")


def _get_bcv_html(headers: dict) -> str | None:
    """Fetch BCV homepage HTML, falling back if their cert chain is broken."""
    try:
        resp = requests.get(BCV_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.text
    except SSLError as e:
        # BCV's public site often serves an incomplete TLS chain; verify=False is
        # required to scrape the official USD rate reliably from CI and local.
        print(f"[BCV] SSL verify failed ({e}); retrying without certificate verification", file=sys.stderr)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        try:
            resp = requests.get(BCV_URL, headers=headers, timeout=15, verify=False)
            resp.raise_for_status()
            return resp.text
        except Exception as retry_err:
            print(f"[BCV] Request failed after SSL fallback: {retry_err}", file=sys.stderr)
            return None
    except Exception as e:
        print(f"[BCV] Request failed: {e}", file=sys.stderr)
        return None


def fetch_bcv_rate() -> float | None:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
    }

    html = _get_bcv_html(headers)
    if html is None:
        return None

    soup = BeautifulSoup(html, "lxml")

    selectors = [
        "#dolar strong",
        ".type-rate strong",
        '[id*="dolar"] strong',
        '[id*="dollar"] strong',
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            text = el.get_text(strip=True).replace(",", ".").replace(" ", "")
            m = re.search(r"[\d]+\.[\d]+", text)
            if m:
                try:
                    rate = float(m.group())
                    if 1 < rate < 100_000:
                        print(f"[BCV] Rate found via '{sel}': {rate}")
                        return rate
                except ValueError:
                    pass

    text = soup.get_text()
    matches = re.findall(r"1\s*USD\s*=\s*([\d,\.]+)\s*(?:Bs|VEF|VES|Bol)", text, re.IGNORECASE)
    for m in matches:
        try:
            rate = float(m.replace(",", "."))
            if 1 < rate < 100_000:
                print(f"[BCV] Rate found via text search: {rate}")
                return rate
        except ValueError:
            pass

    print("[BCV] Could not extract rate from BCV website", file=sys.stderr)
    return None


def run_fetch(fecha: str | None = None, output_file: str = OUTPUT_FILE) -> dict:
    """Fetch BCV rate and write JSON. Returns structured result (no sys.exit)."""
    fecha = fecha or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rate = fetch_bcv_rate()

    result = {
        "success": rate is not None,
        "source": "bcv",
        "fecha": fecha,
        "tasa_bcv": rate,
        "carried_forward": False,
        "error": None if rate is not None else "Could not extract rate from BCV website",
    }

    if rate is not None:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "fecha": fecha,
                "tasa_bcv": rate,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }, f)
        print(f"[BCV] Saved rate {rate} to {output_file}")

    return result


if __name__ == "__main__":
    outcome = run_fetch()
    if outcome["success"]:
        sys.exit(0)
    print("[BCV] No rate fetched - will use last known value", file=sys.stderr)
    sys.exit(1)
