"""Structural break detection: Chow test and rolling variance."""
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats


def chow_test(series: pd.Series, break_idx: int) -> dict[str, Any]:
    """Chow test for structural break at break_idx."""
    s = series.dropna().astype(float)
    n = len(s)
    if break_idx < 10 or break_idx > n - 10:
        return {"error": "Break point too close to series boundaries"}

    y = s.values
    x = np.arange(n)

    # Full sample regression
    coef_full = np.polyfit(x, y, 1)
    resid_full = y - np.polyval(coef_full, x)
    ssr_full = np.sum(resid_full ** 2)

    # Split regressions
    x1, y1 = x[:break_idx], y[:break_idx]
    x2, y2 = x[break_idx:], y[break_idx:]
    coef1 = np.polyfit(x1, y1, 1)
    coef2 = np.polyfit(x2, y2, 1)
    ssr1 = np.sum((y1 - np.polyval(coef1, x1)) ** 2)
    ssr2 = np.sum((y2 - np.polyval(coef2, x2)) ** 2)
    ssr_split = ssr1 + ssr2

    k = 2  # number of parameters per segment
    chow_stat = ((ssr_full - ssr_split) / k) / (ssr_split / (n - 2 * k))
    p_value = 1 - stats.f.cdf(chow_stat, k, n - 2 * k)

    break_date = s.index[break_idx] if hasattr(s.index[break_idx], "isoformat") else break_idx

    return {
        "test": "chow",
        "break_index": break_idx,
        "break_date": str(break_date),
        "chow_statistic": float(chow_stat),
        "p_value": float(p_value),
        "has_break": p_value < 0.05,
        "coef_before": {"slope": float(coef1[0]), "intercept": float(coef1[1])},
        "coef_after": {"slope": float(coef2[0]), "intercept": float(coef2[1])},
    }


def detect_structural_breaks(series: pd.Series, min_segment: int = 20) -> dict[str, Any]:
    """Scan for most likely structural break via grid search on Chow statistic."""
    s = series.dropna().astype(float)
    n = len(s)
    if n < min_segment * 3:
        return {"error": "Insufficient data for break detection"}

    best = None
    candidates = []
    for idx in range(min_segment, n - min_segment, max(1, n // 20)):
        result = chow_test(s, idx)
        if "error" in result:
            continue
        candidates.append(result)
        if best is None or result["chow_statistic"] > best["chow_statistic"]:
            best = result

    return {
        "best_break": best,
        "all_candidates": sorted(candidates, key=lambda x: -x["chow_statistic"])[:5],
        "has_break": best["has_break"] if best else False,
    }
