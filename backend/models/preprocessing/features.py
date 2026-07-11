"""Feature engineering for time series."""
import numpy as np
import pandas as pd


def build_lag_features(series: pd.Series, lags: list[int] | None = None) -> pd.DataFrame:
    lags = lags or [1, 2, 3, 7, 14, 30]
    df = pd.DataFrame({"y": series})
    for lag in lags:
        df[f"lag_{lag}"] = series.shift(lag)
    return df


def build_rolling_features(series: pd.Series, windows: list[int] | None = None) -> pd.DataFrame:
    windows = windows or [7, 14, 30]
    df = pd.DataFrame({"y": series})
    for w in windows:
        df[f"roll_mean_{w}"] = series.rolling(w).mean()
        df[f"roll_std_{w}"] = series.rolling(w).std()
        df[f"roll_min_{w}"] = series.rolling(w).min()
        df[f"roll_max_{w}"] = series.rolling(w).max()
    return df


def build_calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame({
        "dow": index.dayofweek,
        "dom": index.day,
        "month": index.month,
        "quarter": index.quarter,
        "is_month_end": index.is_month_end.astype(int),
    }, index=index)


def build_log_returns(series: pd.Series) -> pd.Series:
    return np.log(series / series.shift(1)).dropna()
