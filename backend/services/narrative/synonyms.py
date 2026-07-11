"""Controlled synonym pool to avoid repetition in narratives."""
import random

SYNONYMS = {
    "spending": ["spending", "expenses", "outflows", "expenditure"],
    "income": ["income", "earnings", "revenue", "inflows"],
    "increase": ["increased", "rose", "grew", "climbed", "expanded", "accelerated"],
    "decrease": ["decreased", "fell", "dropped", "declined", "contracted", "softened"],
    "period": ["month", "period", "billing cycle", "timeframe"],
    "month": ["month", "period", "cycle"],
    "subscription": ["subscription", "recurring payment", "service charge"],
    "balance": ["balance", "net position", "available funds"],
    "budget": ["budget", "finances", "financial position"],
    "rate": ["rate", "exchange rate", "FX rate", "conversion rate"],
    "forecast": ["forecast", "projection", "outlook", "estimate"],
    "significant": ["significant", "notable", "meaningful", "substantial", "marked"],
    "small": ["small", "modest", "marginal", "slight", "minor"],
}


def pick_synonym(word: str, seed: int | None = None, exclude: list[str] | None = None) -> str:
    """Pick a synonym for a word, avoiding recent repeats."""
    pool = SYNONYMS.get(word.lower(), [word])
    if exclude:
        pool = [w for w in pool if w not in exclude]
    if not pool:
        pool = SYNONYMS.get(word.lower(), [word])
    rng = random.Random(seed)
    return rng.choice(pool)
