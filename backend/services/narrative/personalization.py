"""User preference tracking for narrative personalization."""
import json
from datetime import datetime


def get_pref(conn, key: str, default=None):
    row = conn.execute(
        "SELECT pref_value FROM user_prefs WHERE pref_key=?", (key,)
    ).fetchone()
    if not row:
        return default
    try:
        return json.loads(row["pref_value"])
    except Exception:
        return row["pref_value"]


def set_pref(conn, key: str, value) -> None:
    now = datetime.now().isoformat()
    serialized = json.dumps(value)
    conn.execute(
        """INSERT OR REPLACE INTO user_prefs (pref_key, pref_value, updated_at)
           VALUES (?,?,?)""",
        (key, serialized, now),
    )


def record_insight_click(conn, insight_id: str) -> None:
    """Track when user expands/clicks an insight — raises its future priority."""
    click_counts = get_pref(conn, "insight_clicks", {})
    click_counts[insight_id] = click_counts.get(insight_id, 0) + 1
    set_pref(conn, "insight_clicks", click_counts)


def record_insight_dismiss(conn, insight_id: str) -> None:
    """Track when user dismisses an insight — suppresses it temporarily."""
    dismissed = get_pref(conn, "dismissed_insights", {})
    dismissed[insight_id] = datetime.now().isoformat()
    set_pref(conn, "dismissed_insights", dismissed)


def is_dismissed(conn, insight_id: str, cooldown_days: int = 7) -> bool:
    """Check if an insight is in the dismissal cooldown period."""
    dismissed = get_pref(conn, "dismissed_insights", {})
    if insight_id not in dismissed:
        return False
    try:
        dismissed_at = datetime.fromisoformat(dismissed[insight_id])
        days_ago = (datetime.now() - dismissed_at).days
        return days_ago < cooldown_days
    except Exception:
        return False


def get_user_relevance(conn, insight_id: str) -> float:
    """Get relevance weight based on user interaction history."""
    click_counts = get_pref(conn, "insight_clicks", {})
    clicks = click_counts.get(insight_id, 0)
    # More clicks → higher relevance, saturates at 1.0 after 5 clicks
    return min(1.0, 0.3 + clicks * 0.14)


def get_narrative_density(conn) -> str:
    """Get user's preferred narrative density."""
    from core.config import settings
    return get_pref(conn, "narrative_density", settings.narrative_density)
