"""Scrape CENDAS-FVM Cesta Basica Familiar monthly data."""
import csv
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

CENDAS_URL = "https://www.cendasfvm.org/"
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "cesta_basica.csv")

MONTH_MAP = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def fetch_cesta() -> dict | None:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; BudgetBot/1.0)"}
    try:
        resp = requests.get(CENDAS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"[CENDAS] Request failed: {e}", file=sys.stderr)
        return None

    soup = BeautifulSoup(resp.text, "lxml")
    text = soup.get_text(" ", strip=True)

    # Look for cesta basica amount patterns like "Bs. 1,234,567.89" or "USD 1,234.56"
    bs_pattern = re.compile(r"(?:Bs\.?|Bs\s+|BsF\.?)\s*([\d,\.]+)", re.IGNORECASE)
    usd_pattern = re.compile(r"(?:USD?\$?)\s*([\d,\.]+)", re.IGNORECASE)

    bs_matches = bs_pattern.findall(text)
    usd_matches = usd_pattern.findall(text)

    total_bs = None
    total_usd = None

    for m in bs_matches:
        try:
            val = float(m.replace(",", ""))
            if val > 10_000:  # Cesta is in millions of Bs
                total_bs = val
                break
        except ValueError:
            pass

    for m in usd_matches:
        try:
            val = float(m.replace(",", ""))
            if 50 < val < 10_000:  # Reasonable USD range for cesta
                total_usd = val
                break
        except ValueError:
            pass

    # Find month/year reference
    month_pattern = re.compile(
        r"(" + "|".join(MONTH_MAP.keys()) + r")\s+(?:de\s+)?(\d{4})",
        re.IGNORECASE
    )
    period_match = month_pattern.search(text)

    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month

    if period_match:
        month_name = period_match.group(1).lower()
        year_str = period_match.group(2)
        if month_name in MONTH_MAP:
            month = MONTH_MAP[month_name]
        try:
            year = int(year_str)
        except ValueError:
            pass

    if total_bs is None and total_usd is None:
        print("[CENDAS] Could not extract cesta basica amounts", file=sys.stderr)
        return None

    return {
        "year": year,
        "month": month,
        "total_bs": total_bs,
        "total_usd": total_usd,
        "source_url": CENDAS_URL,
        "fetched_at": now.isoformat(),
    }


def update_csv(entry: dict) -> None:
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    existing = []
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not (int(row["year"]) == entry["year"] and int(row["month"]) == entry["month"]):
                    existing.append(row)

    existing.append(entry)
    existing.sort(key=lambda r: (int(r["year"]), int(r["month"])))

    fieldnames = ["year", "month", "total_bs", "total_usd", "source_url", "fetched_at"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing)

    print(f"[CENDAS] Updated {OUTPUT_FILE} with {entry['year']}-{entry['month']:02d} data")


if __name__ == "__main__":
    entry = fetch_cesta()
    if entry:
        update_csv(entry)
    else:
        print("[CENDAS] No data fetched", file=sys.stderr)
        sys.exit(1)
