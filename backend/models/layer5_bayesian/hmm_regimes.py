"""Layer 5: Hidden Markov Model regime detection."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMM = True
except ImportError:
    HAS_HMM = False


def fit_hmm_regimes(series: pd.Series, n_states: int = 2) -> dict[str, Any]:
    """
    Detect calm vs volatile regimes from log returns using Gaussian HMM.
    """
    if not HAS_HMM:
        return {"error": "hmmlearn not installed", "model": "HMM"}

    s = series.dropna().astype(float)
    if len(s) < 60:
        return {"error": "Need at least 60 observations for HMM"}

    returns = np.log(s / s.shift(1)).dropna().values.reshape(-1, 1)
    if len(returns) < 30:
        return {"error": "Insufficient returns for HMM"}

    try:
        model = GaussianHMM(
            n_components=n_states,
            covariance_type="full",
            n_iter=200,
            random_state=42,
        )
        model.fit(returns)
        states = model.predict(returns)
        probs = model.predict_proba(returns)

        # Label states by volatility (higher var = volatile)
        state_vars = []
        for st in range(n_states):
            mask = states == st
            state_vars.append(float(np.var(returns[mask])) if mask.any() else 0.0)

        volatile_state = int(np.argmax(state_vars))
        calm_state = int(np.argmin(state_vars))

        current_state = int(states[-1])
        current_prob = float(probs[-1, current_state])
        regime = "volatile" if current_state == volatile_state else "calm"

        # Regime durations
        changes = np.where(np.diff(states) != 0)[0]
        last_change_idx = changes[-1] + 1 if len(changes) else 0
        days_in_regime = len(states) - last_change_idx

        return {
            "model": "HMM",
            "layer": "layer5",
            "n_states": n_states,
            "current_regime": regime,
            "current_state": current_state,
            "posterior_probability": round(current_prob, 3),
            "days_in_regime": days_in_regime,
            "volatile_state": volatile_state,
            "calm_state": calm_state,
            "state_volatilities": [round(v * 10000, 2) for v in state_vars],
            "states_history": states.tolist()[-60:],
            "transition_matrix": model.transmat_.tolist(),
        }
    except Exception as e:
        return {"error": str(e), "model": "HMM"}
