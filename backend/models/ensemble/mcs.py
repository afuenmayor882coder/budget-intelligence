"""Model Confidence Set (MCS) — simplified Hansen-style implementation."""
from __future__ import annotations

from typing import Any

import numpy as np
from scipy import stats

from models.ensemble.model_selection import diebold_mariano


def model_confidence_set(
    loss_matrix: dict[str, np.ndarray],
    alpha: float = 0.10,
) -> dict[str, Any]:
    """
    Identify the set of models not statistically worse than the best.

    loss_matrix: {model_name: array of per-fold losses (e.g. MAE)}
    Uses pairwise Diebold-Mariano elimination heuristic.
    """
    models = list(loss_matrix.keys())
    if len(models) < 2:
        return {"confidence_set": models, "best_model": models[0] if models else None, "method": "MCS"}

    mean_losses = {m: float(np.nanmean(loss_matrix[m])) for m in models}
    best_model = min(mean_losses, key=mean_losses.get)
    confidence_set = set(models)

    for challenger in list(confidence_set):
        if challenger == best_model:
            continue
        dm = diebold_mariano(
            loss_matrix[best_model],
            loss_matrix[challenger],
            loss="absolute",
        )
        if dm.get("significant") and dm.get("winner") == "model_a":
            confidence_set.discard(challenger)

    # Also eliminate models significantly worse than any remaining member
    changed = True
    while changed and len(confidence_set) > 1:
        changed = False
        for m in list(confidence_set):
            if m == best_model:
                continue
            for ref in confidence_set:
                if ref == m:
                    continue
                dm = diebold_mariano(loss_matrix[ref], loss_matrix[m], loss="absolute")
                if dm.get("significant") and dm.get("winner") == "model_a":
                    confidence_set.discard(m)
                    changed = True
                    break

    ranked = sorted(confidence_set, key=lambda m: mean_losses[m])

    return {
        "method": "MCS",
        "alpha": alpha,
        "confidence_set": ranked,
        "best_model": best_model,
        "mean_losses": mean_losses,
        "n_models_tested": len(models),
        "n_in_set": len(confidence_set),
    }
