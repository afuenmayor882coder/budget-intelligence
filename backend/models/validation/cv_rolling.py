"""Rolling-window time series cross-validation."""
from typing import Callable

import numpy as np
import pandas as pd

from models.validation.metrics import compute_all_metrics


def rolling_cv(
    series: pd.Series,
    fit_predict_fn: Callable[[pd.Series, int], np.ndarray],
    horizon: int = 7,
    initial_train: int = 60,
    step: int = 7,
    max_folds: int = 10,
) -> dict:
    """
    Rolling-origin CV. fit_predict_fn(train_series, horizon) -> predictions array.
    """
    s = series.dropna().astype(float)
    n = len(s)
    if n < initial_train + horizon:
        return {"error": f"Need at least {initial_train + horizon} observations", "folds": []}

    folds = []
    start = initial_train
    fold_idx = 0
    while start + horizon <= n and fold_idx < max_folds:
        train = s.iloc[:start]
        test = s.iloc[start:start + horizon]
        try:
            preds = fit_predict_fn(train, horizon)
            preds = np.asarray(preds)[:horizon]
            actual = test.values
            fold_metrics = compute_all_metrics(actual, preds, in_sample=train.values)
            folds.append({
                "fold": fold_idx,
                "train_end": str(s.index[start - 1]) if hasattr(s.index[start - 1], "isoformat") else start - 1,
                "test_start": start,
                "horizon": horizon,
                "metrics": fold_metrics,
            })
        except Exception as e:
            folds.append({"fold": fold_idx, "error": str(e)})
        start += step
        fold_idx += 1

    valid = [f for f in folds if "metrics" in f]
    if not valid:
        return {"folds": folds, "summary": {}}

    keys = valid[0]["metrics"].keys()
    summary = {}
    for k in keys:
        vals = [f["metrics"][k] for f in valid if k in f["metrics"] and not np.isnan(f["metrics"][k])]
        summary[k] = float(np.mean(vals)) if vals else None

    return {"folds": folds, "summary": summary, "n_folds": len(valid)}
