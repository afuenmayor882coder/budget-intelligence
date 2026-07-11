"""Hierarchical spending forecast with MinT reconciliation."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _mint_reconcile(
    base_forecasts: np.ndarray,
    summing_matrix: np.ndarray,
) -> np.ndarray:
    """
    MinT reconciliation (simplified diagonal covariance).
    base_forecasts: (n_series,) point forecasts at one horizon
    summing_matrix S: (n_total, n_bottom) maps bottom -> total
    """
    n_bottom = summing_matrix.shape[1]
    n_total = len(base_forecasts)

    # Diagonal covariance proxy from forecast magnitudes
    cov = np.diag(np.maximum(base_forecasts ** 2 * 0.01, 1e-6))
    s_cov_s = summing_matrix @ cov[:n_bottom, :n_bottom] @ summing_matrix.T
    try:
        inv = np.linalg.pinv(s_cov_s)
    except Exception:
        return base_forecasts

    reconciled = summing_matrix @ (
        cov[:n_bottom, :n_bottom] @ summing_matrix.T @ inv @ base_forecasts
    )
    return reconciled


def forecast_spending_hierarchy(
    category_monthly: dict[str, list[float]],
    horizon: int = 3,
) -> dict[str, Any]:
    """
    Forecast per-category spending and reconcile so categories sum to total.
    category_monthly: {category: [month1, month2, ...]} historical monthly totals
    """
    if not category_monthly:
        return {"error": "No category spending data"}

    categories = list(category_monthly.keys())
    forecasts = {}

    for cat, history in category_monthly.items():
        h = np.array(history, dtype=float)
        if len(h) < 2:
            forecasts[cat] = [float(h[-1])] * horizon if len(h) else [0.0] * horizon
            continue
        # Simple exponential smoothing
        alpha = 0.3
        level = h[0]
        for v in h[1:]:
            level = alpha * v + (1 - alpha) * level
        trend = (h[-1] - h[0]) / max(len(h) - 1, 1)
        fc = [max(0, level + trend * (i + 1)) for i in range(horizon)]
        forecasts[cat] = fc

    # Reconcile each horizon step
    n_cats = len(categories)
    S = np.ones((n_cats + 1, n_cats))
    S[-1, :] = 1  # total row
    S[:n_cats, :] = np.eye(n_cats)

    reconciled_by_horizon = []
    for step in range(horizon):
        bottom_fc = np.array([forecasts[c][step] for c in categories])
        total_fc = bottom_fc.sum()
        all_fc = np.append(bottom_fc, total_fc)
        rec = _mint_reconcile(all_fc, S)
        reconciled_by_horizon.append({
            "horizon_step": step + 1,
            "categories": {categories[i]: round(float(rec[i]), 2) for i in range(n_cats)},
            "total": round(float(rec[-1]), 2),
        })

    return {
        "method": "hierarchical_mint",
        "horizon": horizon,
        "base_forecasts": forecasts,
        "reconciled": reconciled_by_horizon,
        "categories": categories,
    }


def load_category_spending(conn) -> dict[str, list[float]]:
    """Load monthly spending by category from SQLite."""
    rows = conn.execute(
        """SELECT categoria,
                  CAST(strftime('%Y', fecha) AS INTEGER) as year,
                  CAST(strftime('%m', fecha) AS INTEGER) as month,
                  SUM(ABS(monto_usd)) as total
           FROM transactions
           WHERE tipo = 'Gasto' AND categoria IS NOT NULL
           GROUP BY categoria, year, month
           ORDER BY year, month"""
    ).fetchall()

    by_cat: dict[str, list[float]] = {}
    for r in rows:
        cat = r["categoria"]
        by_cat.setdefault(cat, []).append(float(r["total"] or 0))
    return by_cat
