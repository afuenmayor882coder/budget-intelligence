"""Forecast metrics."""
import numpy as np


def mae(actual: np.ndarray, predicted: np.ndarray) -> float:
    a, p = np.asarray(actual), np.asarray(predicted)
    mask = ~(np.isnan(a) | np.isnan(p))
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs(a[mask] - p[mask])))


def mape(actual: np.ndarray, predicted: np.ndarray) -> float:
    a, p = np.asarray(actual), np.asarray(predicted)
    mask = ~(np.isnan(a) | np.isnan(p)) & (np.abs(a) > 1e-9)
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100)


def rmse(actual: np.ndarray, predicted: np.ndarray) -> float:
    a, p = np.asarray(actual), np.asarray(predicted)
    mask = ~(np.isnan(a) | np.isnan(p))
    if mask.sum() == 0:
        return float("nan")
    return float(np.sqrt(np.mean((a[mask] - p[mask]) ** 2)))


def smape(actual: np.ndarray, predicted: np.ndarray) -> float:
    a, p = np.asarray(actual), np.asarray(predicted)
    mask = ~(np.isnan(a) | np.isnan(p))
    if mask.sum() == 0:
        return float("nan")
    denom = np.abs(a[mask]) + np.abs(p[mask])
    denom = np.where(denom < 1e-9, 1e-9, denom)
    return float(np.mean(2 * np.abs(a[mask] - p[mask]) / denom) * 100)


def mase(actual: np.ndarray, predicted: np.ndarray, in_sample: np.ndarray) -> float:
    """Mean Absolute Scaled Error vs naive seasonal diff."""
    err = mae(actual, predicted)
    if len(in_sample) < 2:
        return float("nan")
    naive = np.mean(np.abs(np.diff(in_sample)))
    if naive < 1e-9:
        return float("nan")
    return err / naive


def pinball_loss(actual: np.ndarray, predicted: np.ndarray, quantile: float = 0.5) -> float:
    a, p = np.asarray(actual), np.asarray(predicted)
    mask = ~(np.isnan(a) | np.isnan(p))
    if mask.sum() == 0:
        return float("nan")
    diff = a[mask] - p[mask]
    return float(np.mean(np.maximum(quantile * diff, (quantile - 1) * diff)))


def coverage(actual: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> float:
    a, lo, hi = np.asarray(actual), np.asarray(lower), np.asarray(upper)
    mask = ~(np.isnan(a) | np.isnan(lo) | np.isnan(hi))
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean((a[mask] >= lo[mask]) & (a[mask] <= hi[mask])) * 100)


def compute_all_metrics(
    actual: np.ndarray,
    predicted: np.ndarray,
    in_sample: np.ndarray | None = None,
    lower: np.ndarray | None = None,
    upper: np.ndarray | None = None,
) -> dict:
    metrics = {
        "mae": mae(actual, predicted),
        "mape": mape(actual, predicted),
        "rmse": rmse(actual, predicted),
        "smape": smape(actual, predicted),
    }
    if in_sample is not None:
        metrics["mase"] = mase(actual, predicted, in_sample)
    if lower is not None and upper is not None:
        metrics["coverage_95"] = coverage(actual, lower, upper)
    return metrics
