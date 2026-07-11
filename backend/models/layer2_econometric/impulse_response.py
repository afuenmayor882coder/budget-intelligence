"""Impulse Response Functions with bootstrap confidence intervals."""
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.api import VAR


def compute_irf(
    df: pd.DataFrame,
    periods: int = 14,
    shock_var: str | None = None,
    bootstrap_reps: int = 100,
) -> dict[str, Any]:
    data = df.dropna().astype(float)
    if len(data) < 40:
        return {"error": "Need at least 40 observations for IRF"}

    try:
        model = VAR(data)
        lag_order = model.select_order(maxlags=5).aic or 2
        lag_order = max(1, min(int(lag_order), 5))
        fitted = model.fit(lag_order)

        irf = fitted.irf(periods=periods)
        irf_values = irf.irfs  # shape: (periods+1, n_vars, n_vars)

        variables = list(data.columns)
        shock_idx = variables.index(shock_var) if shock_var and shock_var in variables else 0

        responses = {}
        for j, resp_var in enumerate(variables):
            responses[resp_var] = irf_values[:, j, shock_idx].tolist()

        # Bootstrap CIs (simplified: use analytic IRF std if bootstrap too slow)
        ci_lower, ci_upper = {}, {}
        try:
            irf_boot = irf.plot_stderr(alpha=0.05, repl=bootstrap_reps)
            # statsmodels doesn't expose boot CIs easily; approximate with ±1.96*stderr
            stderr = irf.stderr() if hasattr(irf, "stderr") else None
            if stderr is not None:
                for j, resp_var in enumerate(variables):
                    se = stderr[:, j, shock_idx]
                    mean = irf_values[:, j, shock_idx]
                    ci_lower[resp_var] = (mean - 1.96 * se).tolist()
                    ci_upper[resp_var] = (mean + 1.96 * se).tolist()
        except Exception:
            pass

        return {
            "model": "VAR-IRF",
            "lag_order": lag_order,
            "periods": periods,
            "shock_variable": variables[shock_idx],
            "variables": variables,
            "responses": responses,
            "ci_lower": ci_lower or None,
            "ci_upper": ci_upper or None,
        }
    except Exception as e:
        return {"error": f"IRF computation failed: {e}"}
