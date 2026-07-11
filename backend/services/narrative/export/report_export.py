"""Monthly report export — PDF and Markdown."""
from datetime import datetime, timezone
from pathlib import Path

from core.database import db_context
from services.narrative.pipeline import generate_all_narratives
from services.forecast_service import run_forecasts
from services.macro_impact import compute_macro_impact
from services.calculations import compute_kpis, compute_runway


REPORTS_DIR = Path(__file__).parent.parent.parent / "data" / "reports"


def _ensure_reports_dir():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def generate_markdown_report(conn, horizon: int = 7) -> str:
    """Generate a full monthly markdown report."""
    kpis = compute_kpis(conn)
    runway = compute_runway(conn)
    narratives = generate_all_narratives(conn)
    forecasts = run_forecasts(conn, horizon=horizon, include_explainer=True)
    macro_impact = compute_macro_impact(conn)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        f"# Financial Analysis Report — {now}",
        "",
        "## Executive Summary",
        narratives.get("executive_summary", "No summary available."),
        "",
        "## Key Metrics",
        f"- Current balance: ${kpis.get('current_balance_usd', 0):,.2f} USD",
        f"- Runway (no income): {runway.get('days_no_income', 'N/A')} days",
        f"- Monthly burn: ${kpis.get('monthly_burn_usd', 0):,.2f} USD",
        f"- Savings rate: {kpis.get('savings_rate', 0):.1f}%",
        "",
        "## FX Forecasts",
    ]

    for target in ["binance", "bcv"]:
        ensemble = forecasts.get("pipeline", {}).get(f"{target}_ensemble")
        if ensemble:
            fc = ensemble.get("forecast", [])
            lines.append(f"- **{target.capitalize()}** ({horizon}-day): {fc[-1]:.1f} VES" if fc else f"- {target}: N/A")

    expl = forecasts.get("explanations", {})
    for key, val in expl.items():
        if isinstance(val, dict) and "verdict" in val:
            lines.append(f"  - {val['verdict']}")

    lines.extend(["", "## Macro Impact"])
    if macro_impact.get("elasticities"):
        lines.append(f"Categories analyzed: {macro_impact['categories_analyzed']}")
        lines.append(f"Risk level: {macro_impact.get('risk_level', 'unknown')} ({macro_impact.get('risk_score')}%)")
        for e in macro_impact["elasticities"][:5]:
            lines.append(f"- **{e['category']}**: {e['interpretation']}")

    lines.extend(["", "## Section Narratives"])
    for section, text in narratives.get("sections", {}).items():
        if text:
            lines.extend([f"### {section.capitalize()}", text, ""])

    if narratives.get("alerts"):
        lines.extend(["", "## Alerts"])
        for alert in narratives["alerts"]:
            lines.append(f"- **[{alert['severity'].upper()}]** {alert['text']}")

    lines.append("")
    lines.append(f"*Generated {datetime.now(timezone.utc).isoformat()}*")
    return "\n".join(lines)


def export_markdown(conn, filename: str | None = None) -> dict:
    _ensure_reports_dir()
    content = generate_markdown_report(conn)
    fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    path = REPORTS_DIR / fname
    path.write_text(content, encoding="utf-8")
    return {"format": "markdown", "path": str(path), "filename": fname, "size_bytes": path.stat().st_size}


def export_pdf(conn, filename: str | None = None) -> dict:
    """Export PDF via markdown → HTML → WeasyPrint if available."""
    _ensure_reports_dir()
    md_content = generate_markdown_report(conn)
    fname = filename or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    path = REPORTS_DIR / fname

    try:
        import markdown
        from weasyprint import HTML
        html = markdown.markdown(md_content, extensions=["tables", "fenced_code"])
        styled = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
        <style>
        body {{ font-family: Inter, sans-serif; max-width: 800px; margin: 40px auto; color: #0d0d0d; line-height: 1.6; }}
        h1 {{ font-size: 24px; }} h2 {{ font-size: 18px; margin-top: 24px; }} h3 {{ font-size: 14px; }}
        code {{ font-family: 'JetBrains Mono', monospace; }}
        </style></head><body>{html}</body></html>"""
        HTML(string=styled).write_pdf(str(path))
        return {"format": "pdf", "path": str(path), "filename": fname, "size_bytes": path.stat().st_size}
    except ImportError:
        # Fallback: save markdown with .pdf.md extension
        md_path = path.with_suffix(".md")
        md_path.write_text(md_content, encoding="utf-8")
        return {
            "format": "markdown_fallback",
            "path": str(md_path),
            "filename": md_path.name,
            "message": "WeasyPrint not installed — exported Markdown instead. pip install weasyprint markdown",
        }
