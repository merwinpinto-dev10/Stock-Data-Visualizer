#  StockViz Pro — App Configuration
#  All colour tokens live in utils/theme.py
#  and are accessed via ThemeManager.current()

APP_TITLE           = "StockViz Pro"
DEFAULT_TICKER      = "AAPL"
REFRESH_INTERVAL_MS = 60_000   # ms between auto-refresh ticks

#  Timeframes 
TIMEFRAMES = {
    "1 Day":    {"period": "1d",  "interval": "5m"},
    "1 Week":   {"period": "5d",  "interval": "30m"},
    "1 Month":  {"period": "1mo", "interval": "1d"},
    "3 Months": {"period": "3mo", "interval": "1d"},
    "1 Year":   {"period": "1y",  "interval": "1wk"},
}

CHART_TYPES = ["Line", "Candlestick"]

INDICATORS = ["SMA 20", "SMA 50", "EMA 20", "Bollinger Bands"]
