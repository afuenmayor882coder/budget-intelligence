import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from core.database import db_context
from services.csv_parser import parse_transactions_csv, import_transactions
from services.xlsx_parser import (
    parse_rates_xlsx, parse_ipc_xlsx, parse_liquidity_xlsx,
    parse_gdp_xlsx, parse_oil_parallel_xlsx,
    import_rates, import_ipc, import_liquidity, import_gdp, import_oil_parallel,
    detect_xlsx_type
)
import openpyxl
import io

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/preview")
async def preview_file(file: UploadFile = File(...)):
    """Preview a file without importing."""
    content = await file.read()
    filename = file.filename or ""

    if filename.lower().endswith(".csv"):
        parsed = parse_transactions_csv(content)
        rows = parsed["rows"]
        return {
            "filename": filename,
            "fileType": parsed["file_type"],
            "rowCount": len(rows),
            "columns": parsed["columns"],
            "preview": [_row_to_preview(r) for r in rows[:4]],
            "dateRange": parsed.get("date_range"),
            "warnings": parsed["warnings"],
            "duplicates": None,
        }

    elif filename.lower().endswith((".xlsx", ".xls")):
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            file_type = detect_xlsx_type(wb)
        except Exception as e:
            raise HTTPException(400, f"Could not open Excel file: {e}")

        if file_type == "rates":
            parsed = parse_rates_xlsx(content)
            rows = parsed["rows"]
            return {
                "filename": filename,
                "fileType": "rates",
                "rowCount": len(rows),
                "columns": ["fecha", "tasa_binance", "tasa_bcv", "dif_pct_paralelo"],
                "preview": [_rate_to_preview(r) for r in rows[:4]],
                "dateRange": parsed.get("date_range"),
                "warnings": parsed["warnings"],
            }
        elif file_type == "macro_ipc":
            parsed = parse_ipc_xlsx(content)
            return {
                "filename": filename,
                "fileType": "macro_ipc",
                "rowCount": parsed["row_count"],
                "columns": ["year", "month", "indice", "var_pct"],
                "preview": [],
                "dateRange": None,
                "warnings": parsed["warnings"],
            }
        elif file_type == "macro_liquidity":
            parsed = parse_liquidity_xlsx(content)
            return {
                "filename": filename,
                "fileType": "macro_liquidity",
                "rowCount": parsed["row_count"],
                "columns": parsed["columns"],
                "preview": [],
                "dateRange": None,
                "warnings": parsed["warnings"],
            }
        elif file_type == "macro_gdp":
            parsed = parse_gdp_xlsx(content)
            return {
                "filename": filename,
                "fileType": "macro_gdp",
                "rowCount": parsed["row_count"],
                "columns": parsed["columns"],
                "preview": [],
                "dateRange": None,
                "warnings": parsed["warnings"],
            }
        elif file_type in ("macro_oil", "macro_oil_parallel"):
            parsed = parse_oil_parallel_xlsx(content)
            return {
                "filename": filename,
                "fileType": "macro_oil_parallel",
                "rowCount": parsed["row_count"],
                "columns": ["year", "revenue_usd_bn", "status"],
                "preview": [],
                "dateRange": None,
                "warnings": parsed["warnings"],
            }
        else:
            return {
                "filename": filename,
                "fileType": file_type,
                "rowCount": 0,
                "columns": [],
                "preview": [],
                "dateRange": None,
                "warnings": [f"File type '{file_type}' — import may be limited. Try uploading directly."],
            }
    else:
        raise HTTPException(400, "Unsupported file type. Upload .csv or .xlsx/.xls")


@router.post("/csv")
async def import_csv(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "upload.csv"

    parsed = parse_transactions_csv(content)
    if parsed["file_type"] != "transactions":
        raise HTTPException(400, "File does not appear to be a Rial transactions CSV")

    batch_id = str(uuid.uuid4())
    with db_context() as conn:
        result = import_transactions(conn, parsed["rows"], batch_id)
        dr = parsed.get("date_range") or {}
        conn.execute(
            "INSERT INTO import_history (id, filename, file_type, date_range_start, date_range_end, row_count) VALUES (?,?,?,?,?,?)",
            (batch_id, filename, "transactions", dr.get("start"), dr.get("end"), result["imported"]),
        )

    return {
        "imported": result["imported"],
        "skipped": result["skipped"],
        "batch_id": batch_id,
        "warnings": parsed["warnings"],
    }


@router.post("/xlsx")
async def import_xlsx(
    file: UploadFile = File(...),
    file_type: str = Form(default="auto"),
):
    content = await file.read()
    filename = file.filename or "upload.xlsx"

    if file_type == "auto":
        try:
            wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
            file_type = detect_xlsx_type(wb)
        except Exception as e:
            raise HTTPException(400, f"Could not open Excel file: {e}")

    batch_id = str(uuid.uuid4())

    with db_context() as conn:
        if file_type == "rates":
            parsed = parse_rates_xlsx(content)
            result = import_rates(conn, parsed["rows"])
            conn.execute(
                "INSERT INTO import_history (id, filename, file_type, row_count) VALUES (?,?,?,?)",
                (batch_id, filename, "rates", result["imported"]),
            )
            return {
                "imported": result["imported"],
                "skipped": result["skipped"],
                "file_type": "rates",
                "message": f"Imported {result['imported']} exchange rate entries",
            }

        elif file_type == "macro_ipc":
            parsed = parse_ipc_xlsx(content)
            result = import_ipc(conn, parsed["rows"])
            conn.execute(
                "INSERT INTO import_history (id, filename, file_type, row_count) VALUES (?,?,?,?)",
                (batch_id, filename, "macro_ipc", result["imported"]),
            )
            return {
                "imported": result["imported"],
                "skipped": 0,
                "file_type": "macro_ipc",
                "message": f"Imported {result['imported']} IPC records",
            }

        elif file_type == "macro_liquidity":
            parsed = parse_liquidity_xlsx(content)
            result = import_liquidity(conn, parsed["rows"])
            conn.execute(
                "INSERT INTO import_history (id, filename, file_type, row_count) VALUES (?,?,?,?)",
                (batch_id, filename, "macro_liquidity", result["imported"]),
            )
            return {
                "imported": result["imported"],
                "skipped": 0,
                "file_type": "macro_liquidity",
                "message": f"Imported {result['imported']} monetary liquidity records",
            }

        elif file_type == "macro_gdp":
            parsed = parse_gdp_xlsx(content)
            result = import_gdp(conn, parsed["rows"])
            conn.execute(
                "INSERT INTO import_history (id, filename, file_type, row_count) VALUES (?,?,?,?)",
                (batch_id, filename, "macro_gdp", result["imported"]),
            )
            return {
                "imported": result["imported"],
                "skipped": 0,
                "file_type": "macro_gdp",
                "message": f"Imported {result['imported']} GDP records",
            }

        elif file_type in ("macro_oil", "macro_oil_parallel"):
            parsed = parse_oil_parallel_xlsx(content)
            result = import_oil_parallel(conn, parsed.get("oil_rows", []), parsed.get("parallel_rows", []))
            conn.execute(
                "INSERT INTO import_history (id, filename, file_type, row_count) VALUES (?,?,?,?)",
                (batch_id, filename, "macro_oil_parallel", result["imported"]),
            )
            return {
                "imported": result["imported"],
                "skipped": 0,
                "file_type": "macro_oil_parallel",
                "message": f"Imported {result['imported']} oil/parallel rate records",
            }

        else:
            raise HTTPException(400, f"Unsupported or undetected file type: '{file_type}'")


@router.get("/history")
def get_history():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM import_history ORDER BY imported_at DESC LIMIT 50"
        ).fetchall()
        return [dict(r) for r in rows]


def _row_to_preview(r: dict) -> dict:
    return {
        "Fecha": r.get("fecha", ""),
        "Tipo": r.get("tipo", ""),
        "Categoria": r.get("categoria", ""),
        "Descripcion": (r.get("descripcion", "") or "")[:40],
        "Monto (USD)": str(r.get("monto_usd", "")),
        "Cuenta": r.get("cuenta", ""),
    }


def _rate_to_preview(r: dict) -> dict:
    return {
        "fecha": r.get("fecha", ""),
        "tasa_binance": str(r.get("tasa_binance", "")),
        "tasa_bcv": str(r.get("tasa_bcv", "")),
        "dif_pct_paralelo": str(r.get("dif_pct_paralelo", "")),
    }
