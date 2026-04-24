import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import mplfinance as mpf
from matplotlib.figure import Figure
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.indicators import compute_sma, compute_ema, compute_rsi
from config import (CHART_BG, ACCENT, ACCENT2, TEXT_COLOR, SUBTEXT_COLOR,
                    BORDER_COLOR, IND_COLORS)

# ── Custom dark mplfinance style ──────────────────────────────────────────────
_DARK_STYLE = mpf.make_mpf_style(
    base_mpf_style="charles",
    marketcolors=mpf.make_marketcolors(
        up=ACCENT, down=ACCENT2,
        edge="inherit", wick="inherit",
        volume={"up": ACCENT, "down": ACCENT2},
    ),
    facecolor=CHART_BG,
    figcolor=CHART_BG,
    gridcolor=BORDER_COLOR,
    gridstyle="-",
    gridaxis="both",
    y_on_right=False,
    rc={
        "axes.labelcolor": SUBTEXT_COLOR,
        "xtick.color":     SUBTEXT_COLOR,
        "ytick.color":     SUBTEXT_COLOR,
        "axes.edgecolor":  BORDER_COLOR,
        "font.size": 8,
    },
)


def build_candle_figure(df: pd.DataFrame, indicators: list,
                        show_rsi: bool = False, ticker: str = "") -> Figure:
    """Build a mplfinance candlestick figure embedded-ready."""

    addplots = []

    if "SMA 20" in indicators:
        s = compute_sma(df, 20)
        addplots.append(mpf.make_addplot(s, color=IND_COLORS["SMA 20"],
                                         width=1.2, linestyle="--"))

    if "SMA 50" in indicators:
        s = compute_sma(df, 50)
        addplots.append(mpf.make_addplot(s, color=IND_COLORS["SMA 50"],
                                         width=1.2, linestyle="--"))

    if "EMA 20" in indicators:
        e = compute_ema(df, 20)
        addplots.append(mpf.make_addplot(e, color=IND_COLORS["EMA 20"],
                                         width=1.2, linestyle="-."))

    if show_rsi:
        rsi = compute_rsi(df)
        addplots.append(mpf.make_addplot(
            rsi, panel=2, color=IND_COLORS["SMA 20"],
            ylabel="RSI", ylim=(0, 100),
        ))

    panel_ratios = (4, 1, 1) if show_rsi else (4, 1)

    plot_kwargs = dict(
        type="candle",
        style=_DARK_STYLE,
        volume=True,
        returnfig=True,
        figsize=(10, 6),
        panel_ratios=panel_ratios,
        warn_too_much_data=9999,
    )
    if addplots:
        plot_kwargs["addplot"] = addplots

    fig, axes = mpf.plot(df, **plot_kwargs)

    # Title
    fig.suptitle(f"{ticker}  —  Candlestick Chart",
                 color=TEXT_COLOR, fontsize=12, fontweight="bold", y=0.99)
    fig.tight_layout(pad=1.5)
    return fig
