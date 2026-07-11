"""Layer 5: GARCH / EGARCH volatility modeling."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

try:
    from arch import arch_model
    HAS_ARCH = True
except ImportError:
    HAS_ARCH = False


def fit_garch_volatility(
    series: pd.Series,
    model_type: str = "GARCH",
    horizon: int = 7,
) -> dict[str, Any]:
    """
    Fit GARCH(1,1) or EGARCH(1,1) on log returns.
    Returns conditional volatility forecast and asymmetry metrics.
    """
    if not HAS_ARCH:
        return {"error": "arch package not installed", "model": model_type}

    s = series.dropna().astype(float)
    if len(s) < 60:
        return {"error": "Need at least 60 observations for GARCH"}

    returns = 100 * np.log(s / s.shift(1)).dropna()
    if len(returns) < 30:
        return {"error": "Insufficient returns for GARCH"}

    try:
        if model_type.upper() == "EGARCH":
            am = arch_model(returns, vol="EGARCH", p=1, q=1, rescale=False)
        else:
            am = arch_model(returns, vol="GARCH", p=1, q=1, rescale=False)

        res = am.fit(disp="off", show_warning=False)
        forecast = res.forecast(horizon=horizon)
        variance = forecast.variance.values[-1]
        vol_pct = np.sqrt(variance)

        # Historical baseline volatility
        hist_vol = float(returns.std())
        current_vol = float(vol_pct[0]) if len(vol_pct) else hist_vol
        vol_ratio = current_vol / hist_vol if hist_vol > 0 else 1.0

        result = {
            "model": model_type.upper(),
            "layer": "layer5",
            "conditional_volatility_pct": vol_pct.tolist(),
            "current_volatility_pct": current_vol,
            "historical_volatility_pct": hist_vol,
            "volatility_ratio": round(vol_ratio, 3),
            "aic": float(res.aic),
            "params": {k: float(v) for k, v in res.params.items()},
        }

        if model_type.upper() == "EGARCH" and "gamma[1]" in res.params:
            gamma = float(res.params["gamma[1]"])
            result["asymmetry_gamma"] = gamma
            result["bad_news_multiplier"] = round(np.exp(abs(gamma)), 2)

        return result
    except Exception as e:
        return {"error": str(e), "model": model_type}
