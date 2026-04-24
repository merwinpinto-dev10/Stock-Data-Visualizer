import pandas as pd
import numpy as np


def compute_sma(df: pd.DataFrame, window: int, col: str = "Close") -> pd.Series:
    return df[col].rolling(window=window).mean()


def compute_ema(df: pd.DataFrame, window: int, col: str = "Close") -> pd.Series:
    return df[col].ewm(span=window, adjust=False).mean()


def compute_rsi(df: pd.DataFrame, window: int = 14, col: str = "Close") -> pd.Series:
    delta = df[col].diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi


def compute_bollinger(df: pd.DataFrame, window: int = 20,
                      num_std: float = 2.0, col: str = "Close"):
    """Returns (upper, mid, lower) as three pd.Series."""
    mid   = df[col].rolling(window=window).mean()
    std   = df[col].rolling(window=window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower
