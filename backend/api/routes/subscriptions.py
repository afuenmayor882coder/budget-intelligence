from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.database import db_context
from services.subscription_optimizer import optimize_subscriptions

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


class SubscriptionCreate(BaseModel):
    name: str
    amount: float
    currency: str = "USD"
    frequency: str = "monthly"
    category: Optional[str] = None
    account: Optional[str] = None
    active: bool = True
    next_payment_date: Optional[str] = None
    essential: bool = False
    notes: Optional[str] = None


@router.get("")
def list_subscriptions():
    with db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM subscriptions ORDER BY active DESC, amount DESC"
        ).fetchall()
        return [dict(r) for r in rows]


@router.post("")
def create_subscription(sub: SubscriptionCreate):
    with db_context() as conn:
        cursor = conn.execute(
            """INSERT INTO subscriptions
               (name, amount, currency, frequency, category, account,
                active, next_payment_date, essential, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (sub.name, sub.amount, sub.currency, sub.frequency, sub.category,
             sub.account, int(sub.active), sub.next_payment_date,
             int(sub.essential), sub.notes),
        )
        return {"id": cursor.lastrowid, **sub.model_dump()}


@router.put("/{sub_id}")
def update_subscription(sub_id: int, sub: SubscriptionCreate):
    with db_context() as conn:
        existing = conn.execute(
            "SELECT id FROM subscriptions WHERE id=?", (sub_id,)
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Subscription not found")
        conn.execute(
            """UPDATE subscriptions
               SET name=?, amount=?, currency=?, frequency=?, category=?,
                   account=?, active=?, next_payment_date=?, essential=?, notes=?
               WHERE id=?""",
            (sub.name, sub.amount, sub.currency, sub.frequency, sub.category,
             sub.account, int(sub.active), sub.next_payment_date,
             int(sub.essential), sub.notes, sub_id),
        )
        return {"id": sub_id, **sub.model_dump()}


@router.delete("/{sub_id}")
def delete_subscription(sub_id: int):
    with db_context() as conn:
        conn.execute("DELETE FROM subscriptions WHERE id=?", (sub_id,))
    return {"status": "deleted"}


@router.get("/optimize")
def get_optimization():
    """Return subscription optimization analysis."""
    with db_context() as conn:
        return optimize_subscriptions(conn)
