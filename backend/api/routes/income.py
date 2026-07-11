from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from core.database import db_context

router = APIRouter(prefix="/income", tags=["income"])


class IncomeCreate(BaseModel):
    name: str
    amount: float
    currency: str = "USD"
    frequency: str = "monthly"
    start_date: str | None = None
    indexed_to_inflation: bool = False
    active: bool = True


@router.get("")
def list_income():
    with db_context() as conn:
        rows = conn.execute("SELECT * FROM income_sources ORDER BY name ASC").fetchall()
        return [dict(r) for r in rows]


@router.post("")
def create_income(data: IncomeCreate):
    with db_context() as conn:
        cursor = conn.execute(
            """INSERT INTO income_sources (name, amount, currency, frequency, start_date, indexed_to_inflation, active)
               VALUES (?,?,?,?,?,?,?)""",
            (data.name, data.amount, data.currency, data.frequency,
             data.start_date, int(data.indexed_to_inflation), int(data.active)),
        )
        row = conn.execute("SELECT * FROM income_sources WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


@router.put("/{income_id}")
def update_income(income_id: int, data: IncomeCreate):
    with db_context() as conn:
        result = conn.execute(
            """UPDATE income_sources
               SET name=?, amount=?, currency=?, frequency=?, start_date=?,
                   indexed_to_inflation=?, active=?
               WHERE id=?""",
            (data.name, data.amount, data.currency, data.frequency,
             data.start_date, int(data.indexed_to_inflation), int(data.active), income_id),
        )
        if result.rowcount == 0:
            raise HTTPException(404, "Income source not found")
        row = conn.execute("SELECT * FROM income_sources WHERE id=?", (income_id,)).fetchone()
        return dict(row)


@router.delete("/{income_id}")
def delete_income(income_id: int):
    with db_context() as conn:
        result = conn.execute("DELETE FROM income_sources WHERE id=?", (income_id,))
        if result.rowcount == 0:
            raise HTTPException(404, "Income source not found")
        return {"ok": True}
