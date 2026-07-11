"""Stationarity tests: ADF, KPSS, Phillips-Perron."""
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss


def run_stationarity_tests(series: pd.Series, name: str = "series") -> dict[str, Any]:
    """Run ADF and KPSS tests on a series."""
    s = series.dropna().astype(float)
    if len(s) < 20:
        return {
            "name": name,
            "n_obs": len(s),
            "error": "Insufficient observations for stationarity tests (need >= 20)",
        }

    result: dict[str, Any] = {"name": name, "n_obs": len(s)}

    # ADF: H0 = unit root (non-stationary)
    try:
        adf_stat, adf_p, adf_lags, _, adf_crit, _ = adfuller(s, autolag="AIC")
        result["adf"] = {
            "statistic": float(adf_stat),
            "p_value": float(adf_p),
            "lags": int(adf_lags),
            "critical_values": {k: float(v) for k, v in adf_crit.items()},
            "is_stationary": adf_p < 0.05,
        }
    except Exception as e:
        result["adf"] = {"error": str(e)}

    # KPSS: H0 = stationary (opposite interpretation)
    try:
        kpss_stat, kpss_p, kpss_lags, kpss_crit = kpss(s, regression="c", nlags="auto")
        result["kpss"] = {
            "statistic": float(kpss_stat),
            "p_value": float(kpss_p),
            "lags": int(kpss_lags),
            "critical_values": {k: float(v) for k, v in kpss_crit.items()},
            "is_stationary": kpss_p >= 0.05,
        }
    except Exception as e:
        result["kpss"] = {"error": str(e)}

    adf_stationary = result.get("adf", {}).get("is_stationary")
    kpss_stationary = result.get("kpss", {}).get("is_stationary")
    if adf_stationary is not None and kpss_stationary is not None:
        if adf_stationary and kpss_stationary:
            result["consensus"] = "stationary"
        elif not adf_stationary and not kpss_stationary:
            result["consensus"] = "non_stationary"
        else:
            result["consensus"] = "mixed"
    else:
        result["consensus"] = "unknown"

    return result


def difference_if_needed(series: pd.Series, max_diff: int = 2) -> tuple[pd.Series, int]:
    """Difference series until ADF suggests stationarity or max_diff reached."""
    s = series.dropna().astype(float)
    d = 0
    for _ in range(max_diff + 1):
        test = run_stationarity_tests(s)
        if test.get("consensus") == "stationary":
            return s, d
        if d >= max_diff:
            break
        s = s.diff().dropna()
        d += 1
    return s, d
