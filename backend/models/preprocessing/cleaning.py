"""Series cleaning utilities."""
import numpy as np
import pandas as pd


def winsorize(series: pd.Series, lower_pct: float = 0.01, upper_pct: float = 0.99) -> pd.Series:
    """Cap extreme values at given percentiles."""
    if series.empty:
        return series
    lo = series.quantile(lower_pct)
    hi = series.quantile(upper_pct)
    return series.clip(lower=lo, upper=hi)


def drop_na_consecutive(df: pd.DataFrame, min_length: int = 30) -> pd.DataFrame:
    """Drop rows with any NA and require minimum length."""
    cleaned = df.dropna()
    if len(cleaned) < min_length:
        raise ValueError(f"Insufficient data after cleaning: {len(cleaned)} rows (need {min_length})")
    return cleaned
