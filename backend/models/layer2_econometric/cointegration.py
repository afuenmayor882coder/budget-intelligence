"""Cointegration tests: Johansen and Engle-Granger."""
from typing import Any

import pandas as pd
import numpy as np
from statsmodels.tsa.vector_ar.vecm import coint_johansen
from statsmodels.tsa.stattools import coint


def johansen_test(df: pd.DataFrame, det_order: int = 0, k_ar_diff: int = 2) -> dict[str, Any]:
    data = df.dropna().astype(float)
    if len(data) < 30:
        return {"error": "Need at least 30 observations for Johansen test"}

    try:
        result = coint_johansen(data.values, det_order=det_order, k_ar_diff=k_ar_diff)
        n_vars = data.shape[1]
        trace_stats = result.lr1.tolist()
        crit_90 = result.cvt[:, 0].tolist()
        crit_95 = result.cvt[:, 1].tolist()
        crit_99 = result.cvt[:, 2].tolist()

        rank_95 = 0
        for i in range(n_vars):
            if trace_stats[i] > crit_95[i]:
                rank_95 = i + 1

        return {
            "test": "johansen",
            "variables": list(data.columns),
            "trace_statistics": trace_stats,
            "critical_90": crit_90,
            "critical_95": crit_95,
            "critical_99": crit_99,
            "cointegrating_rank_95": rank_95,
            "has_cointegration": rank_95 > 0,
            "eigenvectors": result.evec.tolist(),
        }
    except Exception as e:
        return {"error": f"Johansen test failed: {e}"}


def engle_granger_test(y: pd.Series, x: pd.Series) -> dict[str, Any]:
    aligned = pd.concat([y, x], axis=1).dropna()
    if len(aligned) < 30:
        return {"error": "Need at least 30 observations for Engle-Granger test"}

    try:
        stat, p_value, crit = coint(aligned.iloc[:, 0], aligned.iloc[:, 1])
        return {
            "test": "engle_granger",
            "statistic": float(stat),
            "p_value": float(p_value),
            "critical_values": {f"{pct}%": float(v) for pct, v in zip(["1", "5", "10"], crit)},
            "has_cointegration": p_value < 0.05,
        }
    except Exception as e:
        return {"error": f"Engle-Granger test failed: {e}"}
