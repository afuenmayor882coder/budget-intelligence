"""Forecast direction and diagnostic insight detectors."""
import hashlib
from datetime import datetime, timedelta

from services.narrative.insight import Insight


def detect_forecast_insights(conn) -> list[Insight]:
    """Detect notable forecast outputs from cached forecasts."""
    import json
    insights = []

    for target, label in [("binance", "Binance FX"), ("bcv", "BCV rate")]:
        row = conn.execute(
            """SELECT forecast, created_at FROM forecast_cache
               WHERE target = ? ORDER BY created_at DESC LIMIT 2""",
            (target,),
        ).fetchall()

        if len(row) < 1:
            continue

        current = json.loads(row[0]["forecast"])
        fc = current.get("forecast", [])
        if len(fc) < 2:
            continue

        change_pct = (fc[-1] - fc[0]) / max(fc[0], 1) * 100
        direction = "up" if change_pct > 1 else "down" if change_pct < -1 else "steady"
        magnitude = "large" if abs(change_pct) > 10 else "notable" if abs(change_pct) > 5 else "moderate"

        if direction != "steady":
            insights.append(Insight(
                id=hashlib.md5(f"forecast_{target}_{datetime.now().date()}".encode()).hexdigest()[:12],
                detector="forecast",
                subject=f"{label} forecast",
                type="forecast",
                direction=direction,
                magnitude=magnitude,
                severity="notice" if abs(change_pct) > 5 else "info",
                evidence={
                    "target": target,
                    "change_pct": round(change_pct, 2),
                    "forecast_end": round(fc[-1], 2),
                    "forecast_start": round(fc[0], 2),
                    "horizon_days": len(fc),
                },
                tags=["forecast", "rates", target],
            ))

    return insights


def detect_diagnostic_insights(conn) -> list[Insight]:
    """Surface noteworthy statistical diagnostics if model runs exist."""
    import json
    insights = []

    rows = conn.execute(
        "SELECT model_name, layer, metrics FROM model_runs ORDER BY trained_at DESC LIMIT 5"
    ).fetchall()

    for row in rows:
        metrics = json.loads(row["metrics"] or "{}")
        mae = metrics.get("mae")
        if mae is None:
            continue

        severity = "info"
        if mae > 100:
            severity = "warning"
        elif mae < 30:
            severity = "notice"

        insights.append(Insight(
            id=hashlib.md5(f"diag_{row['model_name']}_{mae}".encode()).hexdigest()[:12],
            detector="diagnostic",
            subject=f"{row['model_name']} model accuracy",
            type="diagnostic",
            direction="down" if mae < 50 else "up",
            magnitude="large" if mae > 80 else "moderate",
            severity=severity,
            evidence={
                "model": row["model_name"],
                "layer": row["layer"],
                "mae": round(mae, 2),
                "mape": metrics.get("mape"),
            },
            tags=["diagnostic", "forecast", row["layer"] or "model"],
        ))

    return insights
