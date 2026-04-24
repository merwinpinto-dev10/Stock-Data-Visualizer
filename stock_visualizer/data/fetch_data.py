import ssl
import os

# Must happen before any network import -> more stable python path
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["YFINANCE_USE_CURL"] = "False" #compactibility issues 

# Disable SSL verification & InsecureRequestWarning
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import yfinance as yf #fetch stock data 
import pandas as pd


def fetch_stock_data(ticker: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
    """Download OHLCV data and return a clean, flat DataFrame."""
    try:
        tk = yf.Ticker(ticker.upper()) # ticker object
        df = tk.history(period=period, interval=interval)

        if df is None or df.empty:
            raise ValueError(f"No data returned for '{ticker}'. Check the symbol or timeframe.")

        # Flatten MultiIndex columns (yfinance sometimes returns them)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.droplevel(1)

        # Keep only OHLCV columns that exist
        wanted = ["Open", "High", "Low", "Close", "Volume"]
        df = df[[c for c in wanted if c in df.columns]].copy()

        df.index = pd.to_datetime(df.index)
        # Strip timezone so matplotlib doesn't complain
        if df.index.tz is not None:
            df.index = df.index.tz_localize(None)

        df.sort_index(inplace=True)
        df.dropna(subset=["Close"], inplace=True)
        return df

    except Exception as exc:
        raise RuntimeError(str(exc)) from exc


def get_ticker_info(ticker: str) -> dict:
    """Fetch basic metadata for a ticker (name, price, % change)."""
    try:
        info = yf.Ticker(ticker.upper()).info
        return {
            "name":     info.get("longName") or ticker.upper(),
            "currency": info.get("currency", "USD"),
            "price":    info.get("currentPrice") or info.get("regularMarketPrice") or 0.0,
            "change":   info.get("regularMarketChangePercent") or 0.0,
        }
    except Exception:
        return {"name": ticker.upper(), "currency": "USD", "price": 0.0, "change": 0.0}
