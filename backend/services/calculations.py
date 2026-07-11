"""Core financial calculations."""
from datetime import datetime, timedelta
from typing import Any


def get_monthly_summary(conn, year: int | None = None, month: int | None = None) -> dict[str, Any]:
    """Get income, expenses, net balance, and category breakdown for a period."""
    if year is None or month is None:
        now = datetime.now()
        year, month = now.year, now.month

    start = f"{year:04d}-{month:02d}-01"
    # End of month
    if month == 12:
        end = f"{year+1:04d}-01-01"
    else:
        end = f"{year:04d}-{month+1:02d}-01"

    # Income (Ingresos only, exclude Transferencias)
    cursor = conn.execute(
        """SELECT COALESCE(SUM(ABS(monto_usd)), 0) as total
           FROM transactions
           WHERE tipo = 'Ingreso' AND fecha >= ? AND fecha < ?""",
        (start, end),
    )
    total_income = cursor.fetchone()[0] or 0.0

    # Expenses (Gastos only)
    cursor = conn.execute(
        """SELECT COALESCE(SUM(ABS(monto_usd)), 0) as total
           FROM transactions
           WHERE tipo = 'Gasto' AND fecha >= ? AND fecha < ?""",
        (start, end),
    )
    total_expenses = cursor.fetchone()[0] or 0.0

    net = total_income - total_expenses
    savings_rate = (net / total_income * 100) if total_income > 0 else 0.0

    # Category breakdown (Gastos only)
    cursor = conn.execute(
        """SELECT categoria,
                  SUM(ABS(monto_usd)) as total_usd,
                  COUNT(*) as txn_count,
                  AVG(ABS(monto_usd)) as avg_usd
           FROM transactions
           WHERE tipo = 'Gasto' AND fecha >= ? AND fecha < ? AND categoria IS NOT NULL
           GROUP BY categoria
           ORDER BY total_usd DESC""",
        (start, end),
    )
    cats = cursor.fetchall()

    category_breakdown = []
    for cat in cats:
        pct = (cat["total_usd"] / total_expenses * 100) if total_expenses > 0 else 0
        category_breakdown.append({
            "categoria": cat["categoria"],
            "total_usd": round(cat["total_usd"], 2),
            "pct_of_expenses": round(pct, 1),
            "transaction_count": cat["txn_count"],
            "avg_transaction_usd": round(cat["avg_usd"], 2),
        })

    return {
        "year": year,
        "month": month,
        "total_income_usd": round(total_income, 2),
        "total_expenses_usd": round(total_expenses, 2),
        "net_balance_usd": round(net, 2),
        "savings_rate": round(savings_rate, 1),
        "category_breakdown": category_breakdown,
    }


def get_monthly_series(conn, months: int = 12) -> list[dict]:
    """Return month-by-month income/expense/net series."""
    cursor = conn.execute(
        """SELECT
             CAST(strftime('%Y', fecha) AS INTEGER) as year,
             CAST(strftime('%m', fecha) AS INTEGER) as month,
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd) ELSE 0 END) as total_income_usd,
             SUM(CASE WHEN tipo='Gasto' THEN ABS(monto_usd) ELSE 0 END) as total_expenses_usd
           FROM transactions
           WHERE tipo IN ('Ingreso', 'Gasto')
           GROUP BY year, month
           ORDER BY year, month
           LIMIT ?""",
        (months,),
    )
    rows = cursor.fetchall()
    result = []
    for r in rows:
        net = r["total_income_usd"] - r["total_expenses_usd"]
        result.append({
            "year": r["year"],
            "month": r["month"],
            "total_income_usd": round(r["total_income_usd"], 2),
            "total_expenses_usd": round(r["total_expenses_usd"], 2),
            "net_balance_usd": round(net, 2),
        })
    return result


def compute_kpis(conn) -> dict[str, Any]:
    """Compute dashboard KPIs."""
    now = datetime.now()
    year, month = now.year, now.month

    # Current month summary
    current = get_monthly_summary(conn, year, month)

    # Previous month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    prev = get_monthly_summary(conn, prev_year, prev_month)

    # Net accumulated balance (income - expenses across all tracked transactions)
    cursor = conn.execute(
        """SELECT
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd)
                      WHEN tipo='Gasto' THEN -ABS(monto_usd)
                      ELSE 0 END) as balance
           FROM transactions WHERE tipo IN ('Ingreso', 'Gasto')"""
    )
    balance = (cursor.fetchone()[0] or 0.0)

    # Previous month balance
    cursor = conn.execute(
        """SELECT
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd)
                      WHEN tipo='Gasto' THEN -ABS(monto_usd)
                      ELSE 0 END) as balance
           FROM transactions
           WHERE tipo IN ('Ingreso', 'Gasto')
             AND fecha < ?""",
        (f"{year:04d}-{month:02d}-01",),
    )
    prev_balance = cursor.fetchone()[0] or 0.0

    balance_change_pct = (
        ((balance - prev_balance) / abs(prev_balance) * 100)
        if prev_balance != 0 else 0.0
    )

    burn_change_pct = (
        ((current["total_expenses_usd"] - prev["total_expenses_usd"]) / prev["total_expenses_usd"] * 100)
        if prev["total_expenses_usd"] > 0 else 0.0
    )

    savings_rate_change = current["savings_rate"] - prev["savings_rate"]

    # Real income (use income sources)
    cursor = conn.execute(
        "SELECT amount, currency, frequency FROM income_sources WHERE active=1"
    )
    income_sources = cursor.fetchall()
    monthly_income_usd = 0.0
    for s in income_sources:
        amt = s["amount"]
        if s["frequency"] == "biweekly":
            amt *= 2.17
        elif s["frequency"] == "weekly":
            amt *= 4.33
        elif s["frequency"] == "annual":
            amt /= 12
        if s["currency"] == "VES":
            # Use latest Binance rate or fallback
            cursor2 = conn.execute("SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1")
            rate_row = cursor2.fetchone()
            rate = rate_row["tasa_binance"] if rate_row and rate_row["tasa_binance"] else 700
            amt /= rate
        monthly_income_usd += amt

    # Runway
    runway = compute_runway(conn)

    return {
        "current_balance_usd": round(balance, 2),
        "balance_change_pct": round(balance_change_pct, 1),
        "runway_days": runway.get("days_no_income"),
        "monthly_burn_usd": round(current["total_expenses_usd"], 2),
        "burn_change_pct": round(burn_change_pct, 1),
        "savings_rate": round(current["savings_rate"], 1),
        "savings_rate_change": round(savings_rate_change, 1),
        "real_income_usd": round(monthly_income_usd, 2),
        "real_income_change_pct": 0.0,
    }


def compute_runway(conn, projection_days: int = 180) -> dict[str, Any]:
    """Compute cashflow runway (no income vs with income)."""
    # Current balance — use absolute value of last 30 days net as proxy
    # (sum of all txns may be negative if tracking partial history)
    cursor = conn.execute(
        """SELECT
             SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd)
                      WHEN tipo='Gasto' THEN -ABS(monto_usd)
                      ELSE 0 END) as balance
           FROM transactions WHERE tipo IN ('Ingreso', 'Gasto')"""
    )
    raw_balance = cursor.fetchone()[0] or 0.0

    # If calculated balance is negative (partial history), use a 90-day rolling view
    if raw_balance <= 0:
        ninety_ago = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
        cursor = conn.execute(
            """SELECT
                 SUM(CASE WHEN tipo='Ingreso' THEN ABS(monto_usd)
                          WHEN tipo='Gasto' THEN -ABS(monto_usd)
                          ELSE 0 END) as balance
               FROM transactions
               WHERE tipo IN ('Ingreso', 'Gasto') AND fecha >= ?""",
            (ninety_ago,),
        )
        raw_balance = cursor.fetchone()[0] or 0.0

    balance = max(raw_balance, 0.0)

    # Average daily spend (last 30 days)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    cursor = conn.execute(
        """SELECT COALESCE(SUM(ABS(monto_usd)), 0) / 30.0 as daily_burn
           FROM transactions
           WHERE tipo='Gasto' AND fecha >= ?""",
        (thirty_days_ago,),
    )
    daily_burn = cursor.fetchone()[0] or 0.0

    # Subscription daily cost
    cursor = conn.execute(
        "SELECT amount, currency, frequency FROM subscriptions WHERE active=1"
    )
    subs = cursor.fetchall()
    monthly_subs_usd = 0.0
    cursor2 = conn.execute("SELECT tasa_binance FROM exchange_rates ORDER BY fecha DESC LIMIT 1")
    rate_row = cursor2.fetchone()
    binance_rate = rate_row["tasa_binance"] if rate_row and rate_row["tasa_binance"] else 700

    for s in subs:
        amt = s["amount"]
        if s["frequency"] == "annual":
            amt /= 12
        elif s["frequency"] == "quarterly":
            amt /= 3
        if s["currency"] == "VES":
            amt /= binance_rate
        monthly_subs_usd += amt

    daily_subs = monthly_subs_usd / 30.0
    total_daily_burn = daily_burn + daily_subs

    # Income sources
    cursor = conn.execute("SELECT amount, currency, frequency FROM income_sources WHERE active=1")
    income_sources = cursor.fetchall()
    monthly_income_usd = 0.0
    for s in income_sources:
        amt = s["amount"]
        if s["frequency"] == "biweekly":
            amt *= 2.17
        elif s["frequency"] == "weekly":
            amt *= 4.33
        elif s["frequency"] == "annual":
            amt /= 12
        if s["currency"] == "VES":
            amt /= binance_rate
        monthly_income_usd += amt

    daily_income = monthly_income_usd / 30.0

    # Runway (no income)
    if total_daily_burn > 0:
        days_no_income = int(balance / total_daily_burn)
    else:
        days_no_income = 9999

    # Runway (with income) - find days to zero or show surplus
    net_daily = daily_income - total_daily_burn
    if net_daily >= 0:
        days_with_income = -1  # Surplus
    elif total_daily_burn - daily_income > 0:
        days_with_income = int(balance / (total_daily_burn - daily_income))
    else:
        days_with_income = 9999

    # Generate projection points
    today = datetime.now()
    projection_no_income = []
    projection_with_income = []

    bal_no = balance
    bal_with = balance

    for d in range(0, min(projection_days, days_no_income + 30, 365)):
        date_str = (today + timedelta(days=d)).strftime("%Y-%m-%d")
        bal_no = max(0, balance - total_daily_burn * d)
        projection_no_income.append({"date": date_str, "balance_usd": round(bal_no, 2)})
        if bal_no == 0:
            break

    for d in range(0, projection_days):
        date_str = (today + timedelta(days=d)).strftime("%Y-%m-%d")
        bal_with = balance + net_daily * d
        projection_with_income.append({"date": date_str, "balance_usd": round(bal_with, 2)})
        if bal_with <= 0 and net_daily < 0:
            break

    return {
        "days_no_income": days_no_income,
        "days_with_income": days_with_income,
        "daily_burn_usd": round(total_daily_burn, 2),
        "daily_income_usd": round(daily_income, 2),
        "current_balance_usd": round(balance, 2),
        "projection_no_income": projection_no_income,
        "projection_with_income": projection_with_income,
    }
