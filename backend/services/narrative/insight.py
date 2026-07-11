"""Insight dataclass and priority scoring."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


SEVERITY_WEIGHTS = {
    "info": 1.0,
    "notice": 2.0,
    "warning": 3.5,
    "critical": 5.0,
}


@dataclass
class Insight:
    id: str
    detector: str
    subject: str
    type: str  # trend | anomaly | compare | threshold | streak | milestone | risk | opportunity | ranking
    direction: str = "steady"  # up | down | steady
    magnitude: str = "small"  # small | moderate | notable | large | extreme
    severity: str = "info"  # info | notice | warning | critical
    evidence: dict[str, Any] = field(default_factory=dict)
    time_window: str = "current_month"
    tags: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    expires_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def compute_priority(self, magnitude_zscore: float = 0.0,
                         recency_weight: float = 1.0,
                         user_relevance: float = 0.5) -> float:
        severity_w = SEVERITY_WEIGHTS.get(self.severity, 1.0)
        score = (
            0.4 * severity_w
            + 0.3 * min(1.0, magnitude_zscore)
            + 0.2 * recency_weight
            + 0.1 * user_relevance
        )
        self.priority_score = round(score * 20, 1)  # Scale 0-100
        return self.priority_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "detector": self.detector,
            "subject": self.subject,
            "type": self.type,
            "direction": self.direction,
            "magnitude": self.magnitude,
            "severity": self.severity,
            "evidence": self.evidence,
            "time_window": self.time_window,
            "tags": self.tags,
            "priority_score": self.priority_score,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat(),
        }


def magnitude_label(pct_change: float) -> str:
    """Convert a percentage change to a magnitude label."""
    abs_pct = abs(pct_change)
    if abs_pct < 5:
        return "small"
    elif abs_pct < 15:
        return "moderate"
    elif abs_pct < 30:
        return "notable"
    elif abs_pct < 60:
        return "large"
    else:
        return "extreme"


def magnitude_word(label: str) -> str:
    return {
        "small": "modest",
        "moderate": "moderate",
        "notable": "notable",
        "large": "significant",
        "extreme": "dramatic",
    }.get(label, "moderate")
