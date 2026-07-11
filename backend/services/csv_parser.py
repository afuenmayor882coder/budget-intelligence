"""Parse Rial CSV transaction exports."""
import csv
import io
import unicodedata
import uuid
from datetime import datetime
from typing import Any

RATES_COLUMNS_LOWER = {"fecha", "tasa binance", "tasa oficial"}


def _strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def _normalize_header(h: str) -> str:
    return _strip_accents(h.strip()).lower()


RIAL_NORMALIZED = {
    "fecha", "hora", "tipo", "categoria", "subcategoria",
    "descripcion", "cuenta", "monto (bs)", "monto (usd)", "tasa", "moneda", "comprobante"
}


def _clean_number(s: str) -> float | None:
    if not s or s.strip() in ("", "-", "N/A", "n/a"):
        return None
    s = s.strip().replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def detect_csv_type(headers: set[str]) -> str:
    norm = {_normalize_header(h) for h in headers}
    if RIAL_NORMALIZED.issubset(norm):
        return "transactions"
    if RATES_COLUMNS_LOWER.issubset(norm):
        return "rates"
    return "unknown"


def parse_transactions_csv(content: bytes | str) -> dict[str, Any]:
    """Parse a Rial CSV export. Returns {rows, warnings, date_range, columns}."""
    if isinstance(content, bytes):
        # Try UTF-8 first, then latin-1
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
    else:
        text = content

    reader = csv.DictReader(io.StringIO(text))
    raw_headers = list(reader.fieldnames or [])
    headers = set(raw_headers)
    file_type = detect_csv_type(headers)

    # Build normalized lookup: normalized_name -> actual_header
    header_map: dict[str, str] = {_normalize_header(h): h for h in raw_headers}

    def _get(row: dict, norm_key: str) -> str:
        actual = header_map.get(norm_key, norm_key)
        return (row.get(actual, "") or "").strip()

    rows = []
    warnings = []
    dates = []

    for i, raw in enumerate(reader):
        try:
            fecha = _get(raw, "fecha")
            hora = _get(raw, "hora")
            tipo = _get(raw, "tipo")
            categoria = _get(raw, "categoria")
            subcategoria = _get(raw, "subcategoria") or None
            descripcion = _get(raw, "descripcion")
            cuenta = _get(raw, "cuenta")
            monto_bs = _clean_number(_get(raw, "monto (bs)"))
            monto_usd = _clean_number(_get(raw, "monto (usd)"))
            tasa = _clean_number(_get(raw, "tasa"))
            moneda = _get(raw, "moneda")

            if not fecha or not tipo:
                warnings.append(f"Row {i+2}: Missing fecha or tipo, skipped")
                continue

            # Parse date for validation
            try:
                parsed = datetime.strptime(fecha, "%Y-%m-%d")
                dates.append(parsed)
            except ValueError:
                try:
                    parsed = datetime.strptime(fecha, "%d/%m/%Y")
                    fecha = parsed.strftime("%Y-%m-%d")
                    dates.append(parsed)
                except ValueError:
                    warnings.append(f"Row {i+2}: Unrecognized date format '{fecha}'")

            rows.append({
                "fecha": fecha,
                "hora": hora or None,
                "tipo": tipo,
                "categoria": categoria or None,
                "subcategoria": subcategoria,
                "descripcion": descripcion or None,
                "cuenta": cuenta or None,
                "monto_bs": monto_bs,
                "monto_usd": monto_usd,
                "tasa": tasa,
                "moneda": moneda or None,
            })
        except Exception as e:
            warnings.append(f"Row {i+2}: Parse error - {e}")

    date_range = None
    if dates:
        date_range = {
            "start": min(dates).strftime("%Y-%m-%d"),
            "end": max(dates).strftime("%Y-%m-%d"),
        }

    return {
        "file_type": file_type,
        "rows": rows,
        "warnings": warnings,
        "date_range": date_range,
        "columns": list(headers),
    }


def compute_dedup_key(row: dict) -> str:
    """Deduplication key: fecha + hora + monto_bs + descripcion."""
    parts = [
        row.get("fecha", ""),
        row.get("hora", ""),
        str(row.get("monto_bs", "")),
        (row.get("descripcion", "") or "")[:50],
    ]
    return "|".join(parts)


def import_transactions(conn, rows: list[dict], batch_id: str | None = None) -> dict[str, int]:
    """Import parsed rows into DB, skipping duplicates. Returns {imported, skipped}."""
    if batch_id is None:
        batch_id = str(uuid.uuid4())

    # Fetch existing dedup keys
    existing = set()
    cursor = conn.execute("SELECT fecha, hora, monto_bs, descripcion FROM transactions")
    for r in cursor.fetchall():
        existing.add(f"{r[0]}|{r[1]}|{r[2]}|{(r[3] or '')[:50]}")

    imported = 0
    skipped = 0

    for row in rows:
        key = compute_dedup_key(row)
        if key in existing:
            skipped += 1
            continue

        conn.execute(
            """INSERT INTO transactions
               (fecha, hora, tipo, categoria, subcategoria, descripcion,
                cuenta, monto_bs, monto_usd, tasa, moneda, import_batch_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                row["fecha"], row["hora"], row["tipo"], row["categoria"],
                row["subcategoria"], row["descripcion"], row["cuenta"],
                row["monto_bs"], row["monto_usd"], row["tasa"],
                row["moneda"], batch_id,
            ),
        )
        existing.add(key)
        imported += 1

    return {"imported": imported, "skipped": skipped, "batch_id": batch_id}
