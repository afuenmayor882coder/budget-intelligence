"""Plain-language explainer engine — Phase 3."""
from services.explainer.templates import (
    explain_stationarity,
    explain_cointegration,
    explain_granger,
    explain_forecast,
    explain_metrics,
    explain_diebold_mariano,
    explain_irf,
    explain_structural_break,
    explain_pipeline,
)

__all__ = [
    "explain_stationarity",
    "explain_cointegration",
    "explain_granger",
    "explain_forecast",
    "explain_metrics",
    "explain_diebold_mariano",
    "explain_irf",
    "explain_structural_break",
    "explain_pipeline",
]
