"""In-memory Fact Base: stores, deduplicates, and prioritizes Insights."""
import json
from datetime import datetime
from typing import Any

from services.narrative.insight import Insight


class FactBase:
    def __init__(self):
        self._insights: dict[str, Insight] = {}

    def add(self, insight: Insight) -> None:
        """Add or merge an insight. If same id exists, keep higher priority."""
        existing = self._insights.get(insight.id)
        if existing and existing.priority_score >= insight.priority_score:
            return
        self._insights[insight.id] = insight

    def add_all(self, insights: list[Insight]) -> None:
        for i in insights:
            self.add(i)

    def get_by_context(self, context: str, limit: int = 10) -> list[Insight]:
        """Return top-N insights relevant to a given context/tab."""
        now = datetime.now()
        relevant = [
            i for i in self._insights.values()
            if context in i.tags or "global" in i.tags
            if not i.expires_at or i.expires_at > now
        ]
        return sorted(relevant, key=lambda x: x.priority_score, reverse=True)[:limit]

    def get_top(self, n: int = 5, min_severity: str = "info",
                exclude_types: list[str] | None = None) -> list[Insight]:
        """Return global top-N insights."""
        severity_order = {"info": 0, "notice": 1, "warning": 2, "critical": 3}
        min_sev = severity_order.get(min_severity, 0)
        now = datetime.now()
        filtered = [
            i for i in self._insights.values()
            if severity_order.get(i.severity, 0) >= min_sev
            if not i.expires_at or i.expires_at > now
            if not exclude_types or i.type not in exclude_types
        ]
        return sorted(filtered, key=lambda x: x.priority_score, reverse=True)[:n]

    def get_by_severity(self, severity: str) -> list[Insight]:
        return [i for i in self._insights.values() if i.severity == severity]

    def all(self) -> list[Insight]:
        return list(self._insights.values())

    def clear(self) -> None:
        self._insights.clear()

    def __len__(self) -> int:
        return len(self._insights)

    def to_list(self) -> list[dict[str, Any]]:
        return [i.to_dict() for i in sorted(
            self._insights.values(),
            key=lambda x: x.priority_score,
            reverse=True
        )]


def load_from_db(conn, context: str | None = None) -> FactBase:
    """Load cached insights from SQLite."""
    fb = FactBase()
    now = datetime.now().isoformat()

    if context:
        rows = conn.execute(
            "SELECT * FROM insights_cache WHERE context=? AND (expires_at IS NULL OR expires_at > ?) ORDER BY priority_score DESC",
            (context, now),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM insights_cache WHERE expires_at IS NULL OR expires_at > ? ORDER BY priority_score DESC",
            (now,),
        ).fetchall()

    for row in rows:
        try:
            payload = json.loads(row["payload"]) if row["payload"] else {}
            insight = Insight(
                id=row["id"],
                detector="cache",
                subject=row["subject"] or "",
                type=row["insight_type"] or "info",
                severity=row["severity"] or "info",
                priority_score=row["priority_score"] or 0.0,
                evidence=payload,
                tags=[row["context"]] if row["context"] else [],
            )
            fb.add(insight)
        except Exception:
            pass

    return fb


def save_to_db(conn, fb: FactBase, context: str, ttl_hours: int = 6) -> None:
    """Persist insights to SQLite cache."""
    from datetime import timedelta
    expires = (datetime.now() + timedelta(hours=ttl_hours)).isoformat()

    # Clear old insights for this context
    conn.execute("DELETE FROM insights_cache WHERE context=?", (context,))

    for insight in fb.all():
        conn.execute(
            """INSERT OR REPLACE INTO insights_cache
               (id, context, insight_type, subject, severity, priority_score, payload, expires_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                insight.id,
                context,
                insight.type,
                insight.subject,
                insight.severity,
                insight.priority_score,
                json.dumps(insight.evidence),
                expires,
            ),
        )
