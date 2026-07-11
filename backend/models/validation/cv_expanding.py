"""Expanding-window time series cross-validation."""
from typing import Callable

import numpy as np
import pandas as pd

from models.validation.metrics import compute_all_metrics


def expanding_cv(
    series: pd.Series,
    fit_predict_fn: Callable[[pd.Series, int], np.ndarray],
    horizon: int = 7,
    initial_train: int = 60,
    step: int = 7,
    max_folds: int = 10,
) -> dict:
    s = series.dropna().astype(float)
    n = len(s)
    if n < initial_train + horizon:
        return {"error": f"Need at least {initial_train + horizon} observations", "folds": []}

    folds = []
    train_end = initial_train
    fold_idx = 0
    while train_end + horizon <= n and fold_idx < max_folds:
        train = s.iloc[:train_end]
        test = s.iloc[train_end:train_end + horizon]
        try:
            preds = fit_predict_fn(train, horizon)
            preds = np.asarray(preds)[:horizon]
            fold_metrics = compute_all_metrics(test.values, preds, in_sample=train.values)
            folds.append({"fold": fold_idx, "train_size": len(train), "metrics": fold_metrics})
        except Exception as e:
            folds.append({"fold": fold_idx, "error": str(e)})
        train_end += step
        fold_idx += 1

    valid = [f for f in folds if "metrics" in f]
    if not valid:
        return {"folds": folds, "summary": {}}

    keys = valid[0]["metrics"].keys()
    summary = {k: float(np.mean([f["metrics"][k] for f in valid if not np.isnan(f["metrics"].get(k, float("nan")))]))
               for k in keys}
    return {"folds": folds, "summary": summary, "n_folds": len(valid)}
