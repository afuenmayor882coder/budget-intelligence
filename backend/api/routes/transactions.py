from fastapi import APIRouter, HTTPException, Query
from core.database import db_context
from services.calculations import get_monthly_summary, get_monthly_series

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("")
def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    tipo: str | None = None,
    categoria: str | None = None,
    year: int | None = None,
    month: int | None = None,
):
    with db_context() as conn:
        where = ["tipo NOT IN ('Transferencia')"]
        params: list = []

        if tipo:
            where.append("tipo = ?")
            params.append(tipo)
        if categoria:
            where.append("categoria = ?")
            params.append(categoria)
        if year:
            where.append("CAST(strftime('%Y', fecha) AS INTEGER) = ?")
            params.append(year)
        if month:
            where.append("CAST(strftime('%m', fecha) AS INTEGER) = ?")
            params.append(month)

        sql = f"SELECT * FROM transactions WHERE {' AND '.join(where)} ORDER BY fecha DESC, hora DESC LIMIT ? OFFSET ?"
        params.extend([limit, skip])
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


@router.get("/summary")
def monthly_summary(year: int | None = None, month: int | None = None):
    with db_context() as conn:
        return get_monthly_summary(conn, year, month)


@router.get("/monthly-series")
def monthly_series(months: int = Query(12, ge=1, le=60)):
    with db_context() as conn:
        return get_monthly_series(conn, months)


@router.get("/categories")
def list_categories():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT DISTINCT categoria FROM transactions WHERE categoria IS NOT NULL ORDER BY categoria"
        ).fetchall()
        return [r["categoria"] for r in rows]


@router.delete("/{transaction_id}")
def delete_transaction(transaction_id: int):
    with db_context() as conn:
        result = conn.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Transaction not found")
        return {"ok": True}
