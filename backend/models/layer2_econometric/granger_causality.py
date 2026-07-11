"""Granger causality tests."""
from typing import Any

import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests


def granger_causality_test(df: pd.DataFrame, cause: str, effect: str, maxlag: int = 5) -> dict[str, Any]:
    if cause not in df.columns or effect not in df.columns:
        return {"error": f"Columns {cause} and/or {effect} not found"}

    data = df[[effect, cause]].dropna().astype(float)
    if len(data) < maxlag + 20:
        return {"error": "Insufficient data for Granger causality test"}

    try:
        results = grangercausalitytests(data, maxlag=maxlag, verbose=False)
        best_lag = None
        best_p = 1.0
        lag_results = {}

        for lag, res in results.items():
            f_test = res[0]["ssr_ftest"]
            p_val = float(f_test[1])
            lag_results[str(lag)] = {
                "f_statistic": float(f_test[0]),
                "p_value": p_val,
            }
            if p_val < best_p:
                best_p = p_val
                best_lag = lag

        return {
            "cause": cause,
            "effect": effect,
            "direction": f"{cause} → {effect}",
            "maxlag": maxlag,
            "best_lag": best_lag,
            "best_p_value": best_p,
            "causes": best_p < 0.05,
            "lag_results": lag_results,
        }
    except Exception as e:
        return {"error": f"Granger test failed: {e}"}


def granger_pairwise(df: pd.DataFrame, maxlag: int = 5) -> list[dict]:
    """Run Granger tests for all variable pairs."""
    cols = list(df.columns)
    results = []
    for cause in cols:
        for effect in cols:
            if cause == effect:
                continue
            r = granger_causality_test(df, cause, effect, maxlag=maxlag)
            if "error" not in r:
                results.append(r)
    return results
