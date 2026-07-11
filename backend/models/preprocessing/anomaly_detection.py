"""Anomaly detection: Isolation Forest + STL residuals."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

try:
    from statsmodels.tsa.seasonal import STL
    HAS_STL = True
except ImportError:
    HAS_STL = False


def detect_anomalies_isolation_forest(
    series: pd.Series,
    contamination: float = 0.05,
) -> dict[str, Any]:
    """Flag outliers using Isolation Forest on lag features."""
    s = series.dropna().astype(float)
    if len(s) < 20:
        return {"error": "Need at least 20 observations", "method": "isolation_forest"}

    values = s.values.reshape(-1, 1)
    clf = IsolationForest(contamination=contamination, random_state=42)
    labels = clf.fit_predict(values)
    scores = clf.decision_function(values)

    anomaly_idx = np.where(labels == -1)[0]
    anomalies = []
    for i in anomaly_idx:
        idx = s.index[i]
        anomalies.append({
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "value": float(s.iloc[i]),
            "score": float(scores[i]),
        })

    return {
        "method": "isolation_forest",
        "n_anomalies": len(anomalies),
        "anomalies": anomalies[:20],
        "contamination": contamination,
    }


def detect_anomalies_stl(series: pd.Series, period: int = 7) -> dict[str, Any]:
    """Detect anomalies via STL residual z-scores."""
    if not HAS_STL:
        return {"error": "STL not available", "method": "stl"}

    s = series.dropna().astype(float)
    if len(s) < period * 3:
        return {"error": f"Need at least {period * 3} observations", "method": "stl"}

    try:
        stl = STL(s, period=period, robust=True)
        result = stl.fit()
        resid = result.resid
        mad = np.median(np.abs(resid - np.median(resid)))
        threshold = 3.5 * mad * 1.4826 if mad > 0 else resid.std() * 2

        anomaly_mask = np.abs(resid) > threshold
        anomalies = []
        for i in np.where(anomaly_mask)[0]:
            idx = s.index[i]
            anomalies.append({
                "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
                "value": float(s.iloc[i]),
                "residual": float(resid.iloc[i]),
            })

        return {
            "method": "stl",
            "n_anomalies": len(anomalies),
            "anomalies": anomalies[:20],
            "residual_std": float(resid.std()),
        }
    except Exception as e:
        return {"error": str(e), "method": "stl"}


def run_anomaly_detection(series: pd.Series) -> dict[str, Any]:
    """Run both anomaly detectors."""
    return {
        "isolation_forest": detect_anomalies_isolation_forest(series),
        "stl": detect_anomalies_stl(series),
    }
