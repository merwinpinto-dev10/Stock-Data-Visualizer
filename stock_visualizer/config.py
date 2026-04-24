# ─────────────────────────────────────────────
#  StockViz Pro — App Configuration
# ─────────────────────────────────────────────

APP_TITLE = "StockViz Pro"
DEFAULT_TICKER = "AAPL"
REFRESH_INTERVAL_MS = 60_000  # 60 seconds

# ── Color Palette ─────────────────────────────
BG_COLOR     = "#0d0d1a"
SIDEBAR_BG   = "#13132b"
CARD_BG      = "#1a1a35"
CHART_BG     = "#0d0d1a"
ACCENT       = "#00d4aa"   # teal-green (bullish)
ACCENT2      = "#e94560"   # red (bearish / danger)
TEXT_COLOR   = "#e0e0f0"
SUBTEXT_COLOR = "#6666aa"
BORDER_COLOR = "#2a2a4a"

# ── Chart indicator colours ───────────────────
IND_COLORS = {
    "SMA 20":          "#f7c59f",
    "SMA 50":          "#efefd0",
    "EMA 20":          "#ff6b6b",
    "Bollinger Bands": "#a8dadc",
}

# ── Timeframes ────────────────────────────────
TIMEFRAMES = {
    "1 Day":    {"period": "1d",  "interval": "5m"},
    "1 Week":   {"period": "5d",  "interval": "30m"},
    "1 Month":  {"period": "1mo", "interval": "1d"},
    "3 Months": {"period": "3mo", "interval": "1d"},
    "1 Year":   {"period": "1y",  "interval": "1wk"},
}

CHART_TYPES = ["Line", "Candlestick"]

INDICATORS = ["SMA 20", "SMA 50", "EMA 20", "Bollinger Bands"]
