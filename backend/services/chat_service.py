"""AI Financial Chat Service — Phase 5.

Operates in two modes:
1. Rule-based (always available): classifies query type and returns a structured
   answer assembled from pre-computed analysis data stored in the DB.
2. LLM-powered (optional): if the user provides an Anthropic or OpenAI API key,
   the service injects the rule-based context as a system prompt and lets the LLM
   generate a natural-language response.

Classification categories:
- spending    : questions about expenses, categories, trends
- income      : salary, real income, inflation erosion
- runway      : how long money will last
- forecast    : FX rate outlook, model results
- scenario    : what-if, goal planning, subscription toggle
- purchasing  : purchasing power, Cesta Básica, VES depreciation
- macro       : IPC, M2, oil, GDP, parallel rate spread
- general     : anything else
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.config import settings

logger = logging.getLogger(__name__)

# ── Keyword classifier ──────────────────────────────────────────────────────

_PATTERNS: list[tuple[str, list[str]]] = [
    ("spending",   ["spend", "expense", "cost", "gasto", "category", "categoría",
                    "buy", "bought", "transaction", "how much", "cuánto"]),
    ("income",     ["income", "ingreso", "salary", "earn", "wage", "real income",
                    "inflation-adjusted", "eroded"]),
    ("runway",     ["runway", "last", "survive", "balance", "zero", "days",
                    "burn", "cash", "how long"]),
    ("forecast",   ["forecast", "predict", "future", "next week", "tomorrow",
                    "rate", "tasa", "BCV", "Binance", "exchange"]),
    ("scenario",   ["what if", "qué pasa", "if I cancel", "goal", "save for",
                    "subscription", "scenario", "simulate", "shock"]),
    ("purchasing", ["purchasing power", "poder adquisitivo", "cesta", "basket",
                    "depreciation", "VES", "bolivar", "real value"]),
    ("macro",      ["IPC", "inflation", "inflación", "M2", "liquidity", "GDP",
                    "oil", "petróleo", "parallel rate", "spread", "macro"]),
]


def classify_query(text: str) -> str:
    text_lower = text.lower()
    for category, keywords in _PATTERNS:
        if any(kw.lower() in text_lower for kw in keywords):
            return category
    return "general"


# ── Context fetchers ─────────────────────────────────────────────────────────

def _fmt_usd(v: float | None, decimals: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"${v:,.{decimals}f}"


def _get_financial_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    """Fetch a concise financial snapshot from the DB."""
    snap: dict[str, Any] = {}

    # Balance + spending
    row = conn.execute(
        """SELECT SUM(CASE WHEN tipo='Ingreso' THEN monto_usd ELSE 0 END) income,
                  SUM(CASE WHEN tipo='Gasto'   THEN monto_usd ELSE 0 END) expenses
           FROM transactions
           WHERE fecha >= date('now', '-30 days')"""
    ).fetchone()
    if row:
        snap["monthly_income_usd"] = round(row["income"] or 0, 2)
        snap["monthly_expenses_usd"] = round(row["expenses"] or 0, 2)
        snap["monthly_net_usd"] = round((row["income"] or 0) - (row["expenses"] or 0), 2)

    # Current balance proxy (sum of all transactions)
    bal = conn.execute(
        """SELECT SUM(CASE WHEN tipo='Ingreso' THEN monto_usd
                          WHEN tipo='Gasto'   THEN -monto_usd
                          ELSE 0 END) bal
           FROM transactions"""
    ).fetchone()
    snap["estimated_balance_usd"] = round((bal["bal"] or 0), 2) if bal else 0

    # Top category this month
    cats = conn.execute(
        """SELECT categoria, SUM(monto_usd) total FROM transactions
           WHERE tipo='Gasto' AND fecha >= date('now', '-30 days')
           GROUP BY categoria ORDER BY total DESC LIMIT 3"""
    ).fetchall()
    snap["top_categories"] = [{"name": r["categoria"], "usd": round(r["total"] or 0, 2)} for r in cats]

    # FX rates
    rate = conn.execute(
        "SELECT tasa_binance, tasa_bcv FROM exchange_rates ORDER BY fecha DESC LIMIT 1"
    ).fetchone()
    if rate:
        snap["fx_binance"] = rate["tasa_binance"]
        snap["fx_bcv"] = rate["tasa_bcv"]
        if rate["tasa_binance"] and rate["tasa_bcv"]:
            snap["fx_spread_pct"] = round(
                (rate["tasa_binance"] - rate["tasa_bcv"]) / rate["tasa_bcv"] * 100, 1
            )

    # IPC
    ipc = conn.execute(
        "SELECT year, month, var_pct FROM macro_ipc ORDER BY year DESC, month DESC LIMIT 1"
    ).fetchone()
    if ipc:
        snap["ipc_monthly_pct"] = ipc["var_pct"]
        snap["ipc_period"] = f"{ipc['year']}-{ipc['month']:02d}"

    # Cesta Basica
    cb = conn.execute(
        "SELECT total_usd FROM cesta_basica ORDER BY year DESC, month DESC LIMIT 1"
    ).fetchone()
    if cb:
        snap["cesta_basica_usd"] = cb["total_usd"]

    # Subscriptions
    subs = conn.execute(
        "SELECT COUNT(*) n, SUM(cost_usd) total FROM subscriptions WHERE is_active=1"
    ).fetchone()
    if subs:
        snap["active_subscriptions"] = subs["n"]
        snap["subscription_total_usd"] = round(subs["total"] or 0, 2)

    # Latest forecast (cached)
    fc = conn.execute(
        "SELECT forecast, horizon_days, target FROM forecast_cache ORDER BY id DESC LIMIT 2"
    ).fetchall()
    snap["cached_forecasts"] = [
        {"target": r["target"], "horizon": r["horizon_days"],
         "values": json.loads(r["forecast"]) if r["forecast"] else []}
        for r in fc
    ]

    return snap


# ── Rule-based answer generator ──────────────────────────────────────────────

def _rule_based_answer(category: str, snap: dict[str, Any]) -> str:
    def _income_block() -> str:
        inc = snap.get("monthly_income_usd")
        exp = snap.get("monthly_expenses_usd")
        net = snap.get("monthly_net_usd")
        parts = []
        if inc is not None:
            parts.append(f"Your income this month is **{_fmt_usd(inc)}** USD.")
        if exp is not None:
            parts.append(f"Expenses: **{_fmt_usd(exp)}** USD.")
        if net is not None:
            parts.append(
                f"Net: **{_fmt_usd(net)}** USD ({'surplus 🟢' if net >= 0 else 'deficit 🔴'})."
            )
        ipc = snap.get("ipc_monthly_pct")
        if ipc:
            parts.append(
                f"Monthly inflation (IPC) is **{ipc:.1f}%**, so your real purchasing power "
                f"falls by roughly that amount each month unless your income keeps up."
            )
        return " ".join(parts) if parts else "No income or transaction data loaded yet."

    def _spending_block() -> str:
        cats = snap.get("top_categories", [])
        exp = snap.get("monthly_expenses_usd")
        if not cats:
            return "No spending data found. Upload your CSV transactions first."
        lines = [f"**{c['name']}** — {_fmt_usd(c['usd'])}" for c in cats]
        header = f"Total expenses this month: **{_fmt_usd(exp)}**." if exp else ""
        return f"{header}\n\nTop spending categories:\n" + "\n".join(f"- {l}" for l in lines)

    def _runway_block() -> str:
        exp = snap.get("monthly_expenses_usd", 0)
        inc = snap.get("monthly_income_usd", 0)
        bal = snap.get("estimated_balance_usd", 0)
        if bal == 0 and exp == 0:
            return "No transaction data yet. Upload transactions to calculate your runway."
        daily_burn = exp / 30 if exp > 0 else 0
        days_no_inc = int(bal / daily_burn) if daily_burn > 0 else 9999
        net_daily = (inc - exp) / 30
        if net_daily >= 0:
            runway_with = "indefinite (surplus)"
        else:
            days_with = int(bal / abs(net_daily))
            runway_with = f"~{days_with} days"
        return (
            f"**Without income:** ~{days_no_inc} days at current burn rate.\n\n"
            f"**With income:** {runway_with}.\n\n"
            f"Daily burn: {_fmt_usd(daily_burn)} | Daily income: {_fmt_usd(inc/30)}"
        )

    def _forecast_block() -> str:
        fx_b = snap.get("fx_binance")
        fx_bcv = snap.get("fx_bcv")
        spread = snap.get("fx_spread_pct")
        fc_list = snap.get("cached_forecasts", [])

        lines = []
        if fx_b:
            lines.append(f"**Current Binance (parallel) rate:** Bs {fx_b:,.0f}/USD")
        if fx_bcv:
            lines.append(f"**Current BCV (official) rate:** Bs {fx_bcv:,.0f}/USD")
        if spread:
            lines.append(f"**Parallel/Official spread:** {spread:.1f}%")

        for fc in fc_list:
            vals = fc.get("values", [])
            if vals and isinstance(vals, list) and len(vals) > 0:
                avg = sum(v for v in vals if isinstance(v, (int, float))) / len(vals)
                lines.append(
                    f"\n**7-day {fc['target']} forecast avg:** Bs {avg:,.0f}/USD"
                )

        if not lines:
            return (
                "No exchange rate data loaded. Upload `Historial_TCBinance.xlsx` "
                "via the Upload tab, then run the forecast from the Macro tab."
            )
        lines.append(
            "\n> Run a fresh forecast in the **Macro** tab for full multi-model ensemble results."
        )
        return "\n".join(lines)

    def _scenario_block() -> str:
        subs_total = snap.get("subscription_total_usd")
        subs_n = snap.get("active_subscriptions")
        net = snap.get("monthly_net_usd", 0)
        parts = []
        if subs_total and subs_n:
            parts.append(
                f"You have **{subs_n} active subscriptions** costing **{_fmt_usd(subs_total)}/mo**."
            )
        if net is not None:
            parts.append(
                f"Monthly surplus/deficit: **{_fmt_usd(net)}**. "
                "Use the **Scenarios** tab to run what-if simulations, saving goal calculators, "
                "and macro shock analysis."
            )
        if not parts:
            return "Use the **Scenarios** tab to run what-if simulations and goal planning."
        return " ".join(parts)

    def _purchasing_block() -> str:
        ipc = snap.get("ipc_monthly_pct")
        cb = snap.get("cesta_basica_usd")
        inc = snap.get("monthly_income_usd")
        parts = []
        if ipc:
            parts.append(f"**Monthly IPC:** {ipc:.1f}% inflation.")
            annual = (1 + ipc / 100) ** 12 - 1
            parts.append(f"Compounded annually: **{annual * 100:.0f}%** depreciation.")
        if cb:
            parts.append(f"**Cesta Básica:** {_fmt_usd(cb)} — the basic food basket price.")
        if inc and cb:
            ratio = inc / cb
            parts.append(f"Your income covers **{ratio:.1f}×** the Cesta Básica.")
        if not parts:
            return "Upload IPC and Cesta Básica data via the Upload tab to see purchasing power metrics."
        return " ".join(parts)

    def _macro_block() -> str:
        ipc = snap.get("ipc_monthly_pct")
        period = snap.get("ipc_period", "")
        fx_b = snap.get("fx_binance")
        spread = snap.get("fx_spread_pct")
        parts = []
        if ipc:
            parts.append(f"**IPC ({period}):** {ipc:.1f}% monthly inflation.")
        if fx_b:
            parts.append(f"**Parallel exchange rate:** Bs {fx_b:,.0f}/USD.")
        if spread:
            parts.append(f"**Parallel/official spread:** {spread:.1f}%.")
        parts.append("For full macro indicators, visit the **Macro** tab.")
        return " ".join(parts) if parts else "Upload macro Excel files (IPC, liquidity, GDP) for macro insights."

    def _general_block() -> str:
        return (
            "I'm your Budget Intelligence assistant. I can help you understand:\n\n"
            "- **Spending patterns** — 'How much did I spend on food this month?'\n"
            "- **Income & runway** — 'How many days until I run out of money?'\n"
            "- **FX forecasts** — 'What's the expected Binance rate next week?'\n"
            "- **Purchasing power** — 'How is inflation eroding my income?'\n"
            "- **What-if scenarios** — 'What if I cancel Netflix?'\n"
            "- **Macro context** — 'What's the current IPC inflation?'\n\n"
            "Ask me anything about your finances!"
        )

    dispatch = {
        "spending": _spending_block,
        "income": _income_block,
        "runway": _runway_block,
        "forecast": _forecast_block,
        "scenario": _scenario_block,
        "purchasing": _purchasing_block,
        "macro": _macro_block,
        "general": _general_block,
    }
    return dispatch.get(category, _general_block)()


# ── LLM integration ──────────────────────────────────────────────────────────

def _call_anthropic(messages: list[dict], system: str, api_key: str) -> str:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system,
            messages=messages,
        )
        return response.content[0].text
    except ImportError:
        return "(Anthropic SDK not installed: `pip install anthropic`)"
    except Exception as exc:
        logger.error(f"Anthropic call failed: {exc}")
        return f"(Anthropic error: {exc})"


def _call_openai(messages: list[dict], system: str, api_key: str) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        full_messages = [{"role": "system", "content": system}] + messages
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=full_messages,
        )
        return response.choices[0].message.content or ""
    except ImportError:
        return "(OpenAI SDK not installed: `pip install openai`)"
    except Exception as exc:
        logger.error(f"OpenAI call failed: {exc}")
        return f"(OpenAI error: {exc})"


# ── Main entry point ─────────────────────────────────────────────────────────

def chat(
    user_message: str,
    conversation_history: list[dict[str, str]],
    conn: sqlite3.Connection,
    anthropic_key: str = "",
    openai_key: str = "",
) -> dict[str, Any]:
    """Process a chat message and return a response dict.

    Returns:
        {
            "reply": str,          # markdown-formatted response
            "category": str,       # classified query category
            "mode": str,           # "llm" | "rule_based"
            "source": str,         # "anthropic" | "openai" | "rule_based"
            "timestamp": str,
        }
    """
    category = classify_query(user_message)
    snap = _get_financial_snapshot(conn)
    rule_answer = _rule_based_answer(category, snap)

    use_anthropic = bool(anthropic_key or settings.anthropic_api_key)
    use_openai = bool(openai_key or settings.openai_api_key)
    effective_anthropic = anthropic_key or settings.anthropic_api_key
    effective_openai = openai_key or settings.openai_api_key

    if use_anthropic or use_openai:
        system_prompt = (
            "You are a concise, expert personal finance assistant specialised in "
            "Venezuela's dual-currency economy (VES/USD). "
            "Use the financial context below to give a precise, data-driven answer. "
            "Format responses in Markdown. Be direct and quantitative. "
            "If the data is insufficient, say so and suggest what the user should upload.\n\n"
            f"=== FINANCIAL CONTEXT ===\n{rule_answer}\n\n"
            f"=== RAW SNAPSHOT ===\n{json.dumps(snap, ensure_ascii=False, indent=2)}"
        )
        msgs = [{"role": m["role"], "content": m["content"]} for m in conversation_history[-10:]]
        msgs.append({"role": "user", "content": user_message})

        if use_anthropic:
            reply = _call_anthropic(msgs, system_prompt, effective_anthropic)
            mode, source = "llm", "anthropic"
        else:
            reply = _call_openai(msgs, system_prompt, effective_openai)
            mode, source = "llm", "openai"
    else:
        reply = rule_answer
        mode, source = "rule_based", "rule_based"

    return {
        "reply": reply,
        "category": category,
        "mode": mode,
        "source": source,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context_snapshot": snap,
    }


def get_suggested_questions(conn: sqlite3.Connection) -> list[str]:
    """Return context-aware suggested questions."""
    snap = _get_financial_snapshot(conn)
    questions = ["What is my current monthly surplus or deficit?"]

    if snap.get("top_categories"):
        top = snap["top_categories"][0]["name"]
        questions.append(f"How much did I spend on {top} this month?")

    if snap.get("fx_binance"):
        questions.append("What is the Binance rate forecast for next week?")

    if snap.get("ipc_monthly_pct"):
        ipc = snap["ipc_monthly_pct"]
        questions.append(f"With {ipc:.1f}% monthly inflation, how is my purchasing power changing?")

    if snap.get("active_subscriptions", 0) > 0:
        questions.append("Which subscriptions should I cancel to save money?")

    questions.append("How many days of runway do I have without income?")
    questions.append("What would happen if the Binance rate jumps 20%?")

    return questions[:6]
