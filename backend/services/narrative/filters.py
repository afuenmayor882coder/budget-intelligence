"""Custom Jinja2 filters for numeric/date formatting in narratives."""
from datetime import datetime


def money(value, currency="USD", precision=2) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if currency == "USD":
        return f"${v:,.{precision}f}"
    elif currency == "VES" or currency == "Bs":
        return f"Bs {v:,.{precision}f}"
    return f"{v:,.{precision}f} {currency}"


def money_compact(value, currency="USD") -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)

    if abs(v) >= 1_000_000:
        formatted = f"{v / 1_000_000:.1f}M"
    elif abs(v) >= 1_000:
        formatted = f"{v / 1_000:.1f}K"
    else:
        formatted = f"{v:.0f}"

    if currency == "USD":
        return f"${formatted}"
    return f"{formatted} {currency}"


def pct(value, precision=1) -> str:
    if value is None:
        return "N/A"
    try:
        return f"{float(value):.{precision}f}%"
    except (TypeError, ValueError):
        return str(value)


def pct_signed(value, precision=1) -> str:
    if value is None:
        return "N/A"
    try:
        v = float(value)
        sign = "+" if v >= 0 else ""
        return f"{sign}{v:.{precision}f}%"
    except (TypeError, ValueError):
        return str(value)


def delta(value) -> str:
    if value is None:
        return "unchanged"
    try:
        v = float(value)
        if abs(v) < 0.5:
            return "unchanged"
        direction = "up" if v > 0 else "down"
        return f"{direction} {abs(v):.1f}%"
    except (TypeError, ValueError):
        return "changed"


def date_relative(date_str: str | None) -> str:
    if not date_str:
        return "recently"
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        now = datetime.now()
        diff_days = (now - dt).days
        if diff_days == 0:
            return "today"
        elif diff_days == 1:
            return "yesterday"
        elif diff_days < 7:
            return f"{diff_days} days ago"
        elif diff_days < 14:
            return "last week"
        elif diff_days < 32:
            return "last month"
        else:
            return dt.strftime("%B %Y")
    except Exception:
        return date_str


def magnitude_word(label: str) -> str:
    return {
        "small": "modest",
        "moderate": "moderate",
        "notable": "notable",
        "large": "significant",
        "extreme": "dramatic",
    }.get(label, "moderate")


def period_label(year: int, month: int) -> str:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return f"{months[month-1]} {year}"


def verbally_pluralize(count: int, singular: str, plural: str | None = None) -> str:
    plural = plural or (singular + "s")
    return f"{count} {singular if count == 1 else plural}"


def register_filters(env):
    """Register all custom filters with a Jinja2 Environment."""
    env.filters["money"] = money
    env.filters["money_compact"] = money_compact
    env.filters["pct"] = pct
    env.filters["pct_signed"] = pct_signed
    env.filters["delta"] = delta
    env.filters["date_relative"] = date_relative
    env.filters["magnitude_word"] = magnitude_word
    env.filters["period"] = lambda y, m=None: period_label(y, m) if m else str(y)
    env.filters["pluralize"] = verbally_pluralize
