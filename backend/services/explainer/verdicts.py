"""Severity mapping for verdict cards."""
from typing import Literal

Severity = Literal["excellent", "good", "moderate", "concerning", "critical", "informational"]

SEVERITY_COLORS = {
    "excellent": "green",
    "good": "green",
    "moderate": "amber",
    "concerning": "amber",
    "critical": "red",
    "informational": "neutral",
}


def mae_severity(mae: float, scale: float = 100) -> Severity:
    ratio = mae / max(scale, 1)
    if ratio < 0.03:
        return "excellent"
    if ratio < 0.08:
        return "good"
    if ratio < 0.15:
        return "moderate"
    if ratio < 0.30:
        return "concerning"
    return "critical"


def pvalue_severity(p: float, reject_is_good: bool = False) -> Severity:
    if reject_is_good:
        if p < 0.01:
            return "excellent"
        if p < 0.05:
            return "good"
        return "informational"
    if p < 0.01:
        return "critical"
    if p < 0.05:
        return "concerning"
    return "good"


def coverage_severity(coverage_pct: float, target: float = 95) -> Severity:
    diff = abs(coverage_pct - target)
    if diff <= 3:
        return "excellent"
    if diff <= 8:
        return "good"
    if diff <= 15:
        return "moderate"
    return "concerning"
