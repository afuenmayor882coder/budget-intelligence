"""Diebold-Mariano test for forecast comparison."""
import numpy as np
from scipy import stats


def diebold_mariano(
    errors_a: np.ndarray,
    errors_b: np.ndarray,
    h: int = 1,
    loss: str = "squared",
) -> dict:
    """
    Test whether model A forecasts are significantly better than model B.
    errors = actual - forecast for each model.
    """
    ea = np.asarray(errors_a, dtype=float)
    eb = np.asarray(errors_b, dtype=float)
    n = min(len(ea), len(eb))
    ea, eb = ea[:n], eb[:n]
    mask = ~(np.isnan(ea) | np.isnan(eb))
    ea, eb = ea[mask], eb[mask]
    if len(ea) < 5:
        return {"error": "Need at least 5 paired forecast errors"}

    if loss == "absolute":
        d = np.abs(ea) - np.abs(eb)
    else:
        d = ea ** 2 - eb ** 2

    d_mean = np.mean(d)
    # Newey-West style variance adjustment for h-step ahead
    gamma0 = np.var(d, ddof=1)
    if h > 1:
        for k in range(1, h):
            w = 1 - k / h
            gamma_k = np.cov(d[k:], d[:-k], ddof=1)[0, 1] if len(d) > k else 0
            gamma0 += 2 * w * gamma_k
    se = np.sqrt(gamma0 / len(d)) if gamma0 > 0 else 1e-9
    dm_stat = d_mean / se
    p_value = 2 * (1 - stats.norm.cdf(abs(dm_stat)))

    if p_value < 0.05:
        winner = "model_a" if d_mean < 0 else "model_b"
        significant = True
    else:
        winner = "tie"
        significant = False

    return {
        "dm_statistic": float(dm_stat),
        "p_value": float(p_value),
        "mean_loss_diff": float(d_mean),
        "significant": significant,
        "winner": winner,
        "n_obs": len(d),
        "loss": loss,
    }
