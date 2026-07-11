"""Layer 5: Markov-switching autoregression (simplified)."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression
    HAS_MS = True
except ImportError:
    HAS_MS = False


def fit_markov_switching(series: pd.Series, k_regimes: int = 2) -> dict[str, Any]:
    """Markov-switching AR(1) for regime-dependent dynamics."""
    if not HAS_MS:
        return {"error": "MarkovAutoregression not available", "model": "MarkovSwitching"}

    s = series.dropna().astype(float)
    if len(s) < 80:
        return {"error": "Need at least 80 observations for Markov switching"}

    try:
        model = MarkovAutoregression(s, k_regimes=k_regimes, order=1, switching_ar=True)
        res = model.fit(disp=False, maxiter=200)
        probs = res.smoothed_marginal_probabilities
        current_probs = probs.iloc[-1].tolist() if probs is not None else []
        current_regime = int(np.argmax(current_probs)) if current_probs else 0

        return {
            "model": "MarkovSwitching",
            "layer": "layer5",
            "k_regimes": k_regimes,
            "current_regime": current_regime,
            "regime_probabilities": [round(p, 3) for p in current_probs],
            "aic": float(res.aic),
            "bic": float(res.bic),
        }
    except Exception as e:
        return {"error": str(e), "model": "MarkovSwitching"}
