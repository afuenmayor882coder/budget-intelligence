"""Layer 2: Vector Error Correction Model (VECM)."""
from typing import Any

import numpy as np
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen


def fit_vecm(df: pd.DataFrame, horizon: int = 7, det_order: int = 0) -> dict[str, Any]:
    if len(df) < 50:
        return {"error": "Need at least 50 observations for VECM"}

    data = df.dropna().astype(float)
    try:
        joh = coint_johansen(data.values, det_order=det_order, k_ar_diff=2)
        rank = sum(joh.lr1 > joh.cvt[:, 1])  # 5% trace test
        coint_rank = max(1, min(rank, len(data.columns) - 1))

        model = VECM(data, k_ar_diff=2, coint_rank=coint_rank, deterministic="ci")
        fitted = model.fit()
        fc = fitted.predict(steps=horizon)

        forecasts = {}
        for i, col in enumerate(data.columns):
            forecasts[col] = fc[:, i].tolist()

        return {
            "model": "VECM",
            "coint_rank": int(coint_rank),
            "variables": list(data.columns),
            "forecast": forecasts,
            "johansen_trace": joh.lr1.tolist(),
            "johansen_crit_5pct": joh.cvt[:, 1].tolist(),
        }
    except Exception as e:
        return {"error": f"VECM fit failed: {e}"}
