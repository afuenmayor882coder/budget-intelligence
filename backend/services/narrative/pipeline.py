"""
Narrative pipeline orchestrator.
Stage 1: Run all detectors → emit Insights
Stage 2: Populate FactBase (dedup, score, relate)
Stage 3: Compose narrative text
"""
import hashlib
import logging
from datetime import datetime
from typing import Any

from services.narrative.fact_base import FactBase
from services.narrative.insight import Insight
from services.narrative.detectors.trend import detect_spending_trends
from services.narrative.detectors.comparison import detect_period_comparisons
from services.narrative.detectors.threshold import detect_thresholds
from services.narrative.detectors.anomaly import detect_anomalies
from services.narrative.detectors.milestone import detect_milestones
from services.narrative.detectors.risk import detect_risks
from services.narrative.detectors.opportunity import detect_opportunities
from services.narrative.detectors.streak import detect_streaks
from services.narrative.detectors.ranking_change import detect_ranking_changes
from services.narrative.detectors.forecast import detect_forecast_insights, detect_diagnostic_insights
from services.narrative.detectors.correlation import detect_correlations
from services.narrative.composer.selector import select_template
from services.narrative.composer.renderer import render_template
from services.narrative.composer.stitcher import stitch
from services.narrative.composer.style import vary_style
from services.narrative.composer.prioritizer import prioritize

logger = logging.getLogger(__name__)


def run_all_detectors(conn) -> list[Insight]:
    """Run all insight detectors and return combined list."""
    all_insights = []
    detectors = [
        ("trend", detect_spending_trends),
        ("comparison", detect_period_comparisons),
        ("threshold", detect_thresholds),
        ("anomaly", detect_anomalies),
        ("milestone", detect_milestones),
        ("risk", detect_risks),
        ("opportunity", detect_opportunities),
        ("streak", detect_streaks),
        ("ranking_change", detect_ranking_changes),
        ("forecast", detect_forecast_insights),
        ("diagnostic", detect_diagnostic_insights),
        ("correlation", detect_correlations),
    ]

    for name, detector_fn in detectors:
        try:
            insights = detector_fn(conn)
            all_insights.extend(insights)
        except Exception as e:
            logger.warning(f"Detector '{name}' failed: {e}")

    return all_insights


def build_fact_base(insights: list[Insight]) -> FactBase:
    """Build and populate the FactBase from raw insights."""
    fb = FactBase()

    for insight in insights:
        # Compute priority
        mag_map = {"small": 0.1, "moderate": 0.4, "notable": 0.6, "large": 0.8, "extreme": 1.0}
        mag_score = mag_map.get(insight.magnitude, 0.3)
        insight.compute_priority(magnitude_zscore=mag_score)
        fb.add(insight)

    return fb


def compose_paragraph(insights: list[Insight], context: str = "dashboard",
                       density: str = "normal", seed: int = 0) -> str:
    """
    Turn a list of prioritized insights into a paragraph of narrative text.
    """
    if not insights:
        return ""

    sentences = []
    used_words: list[str] = []

    for i, insight in enumerate(insights):
        template_path = select_template(insight)
        # Build context dict from insight data
        ctx = {
            "subject": insight.subject,
            "type": insight.type,
            "direction": insight.direction,
            "magnitude": insight.magnitude,
            "severity": insight.severity,
            **insight.evidence,
        }
        rendered = render_template(template_path, ctx)
        rendered = rendered.strip()
        if rendered and not rendered.startswith("["):
            varied = vary_style(rendered, seed=seed + i, used_words=used_words)
            sentences.append(varied)
            # Track used words to prevent repetition
            used_words.extend(varied.lower().split()[:10])

    # Determine tone from overall severity
    severities = [i.severity for i in insights]
    if "critical" in severities:
        tone = "concerned"
    elif "warning" in severities:
        tone = "cautionary"
    elif any(i.type == "milestone" for i in insights):
        tone = "celebratory"
    else:
        tone = "neutral"

    return stitch(sentences, tone=tone, seed=seed)


def generate_executive_summary(conn, density: str = "normal") -> str:
    """Generate the hero executive summary for the dashboard."""
    all_insights = run_all_detectors(conn)
    fb = build_fact_base(all_insights)

    # Pick top insights for hero summary
    top = prioritize(fb.all(), context="dashboard", max_count=5, density=density)

    if not top:
        txn_count = conn.execute("SELECT COUNT(*) as cnt FROM transactions").fetchone()["cnt"]
        if txn_count == 0:
            return ("No financial data uploaded yet. "
                    "Upload your first CSV via the Upload tab to see your personalized analysis.")
        return "Upload more data to generate a comprehensive financial summary."

    seed = int(hashlib.md5(datetime.now().strftime("%Y-%m-%d").encode()).hexdigest(), 16) % 10000
    return compose_paragraph(top, context="dashboard", density=density, seed=seed)


def generate_section_narrative(conn, section: str, density: str = "normal") -> str:
    """Generate narrative for a specific dashboard section."""
    all_insights = run_all_detectors(conn)
    fb = build_fact_base(all_insights)

    section_insights = prioritize(
        fb.all(), context=section, max_count=3, density=density
    )

    if not section_insights:
        return ""

    seed = int(hashlib.md5((section + datetime.now().strftime("%Y-%m-%d")).encode()).hexdigest(), 16) % 10000
    return compose_paragraph(section_insights, context=section, density=density, seed=seed)


def generate_all_narratives(conn, density: str = "normal") -> dict[str, Any]:
    """
    Run full pipeline and return narratives for all sections.
    Cached to avoid re-running detectors multiple times per request.
    """
    all_insights = run_all_detectors(conn)
    fb = build_fact_base(all_insights)
    seed = int(hashlib.md5(datetime.now().strftime("%Y-%m-%d-%H").encode()).hexdigest(), 16) % 10000

    sections = ["dashboard", "spending", "income", "subscriptions", "rates", "macro"]
    narratives = {}

    for section in sections:
        top = prioritize(fb.all(), context=section, max_count=5, density=density)
        if top:
            narratives[section] = compose_paragraph(top, context=section, density=density, seed=seed)
        else:
            narratives[section] = ""

    # Alert cards: critical/warning insights
    alerts = []
    for insight in fb.get_by_severity("critical"):
        template_path = select_template(insight)
        ctx = {
            "subject": insight.subject,
            "type": insight.type,
            "direction": insight.direction,
            "magnitude": insight.magnitude,
            "severity": insight.severity,
            **insight.evidence,
        }
        rendered = render_template(template_path, ctx).strip()
        if rendered and not rendered.startswith("["):
            alerts.append({
                "severity": "critical",
                "subject": insight.subject,
                "text": rendered,
                "insight_id": insight.id,
            })

    for insight in fb.get_by_severity("warning")[:3]:
        template_path = select_template(insight)
        ctx = {
            "subject": insight.subject,
            "type": insight.type,
            "direction": insight.direction,
            "magnitude": insight.magnitude,
            "severity": insight.severity,
            **insight.evidence,
        }
        rendered = render_template(template_path, ctx).strip()
        if rendered and not rendered.startswith("["):
            alerts.append({
                "severity": "warning",
                "subject": insight.subject,
                "text": rendered,
                "insight_id": insight.id,
            })

    return {
        "executive_summary": narratives.get("dashboard", ""),
        "sections": narratives,
        "alerts": alerts,
        "insight_count": len(fb),
        "top_insights": [i.to_dict() for i in fb.get_top(5)],
        "generated_at": datetime.now().isoformat(),
    }
