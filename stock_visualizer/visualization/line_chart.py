import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.indicators import compute_sma, compute_ema, compute_bollinger, compute_rsi
from config import (CHART_BG, ACCENT, ACCENT2, TEXT_COLOR, SUBTEXT_COLOR,
                    BORDER_COLOR, IND_COLORS)


def _style_ax(ax):
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=SUBTEXT_COLOR, labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER_COLOR)
    ax.grid(True, color=BORDER_COLOR, linewidth=0.5, alpha=0.7)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def build_line_figure(df: pd.DataFrame, indicators: list,
                      show_rsi: bool = False, ticker: str = "") -> Figure:
    nrows  = 2 if show_rsi else 1
    ratios = [3, 1] if show_rsi else [1]

    fig, axes = plt.subplots(
        nrows, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": ratios},
        facecolor=CHART_BG,
    )
    if nrows == 1:
        axes = [axes]

    ax = axes[0]
    _style_ax(ax)

    # Price line + fill
    ax.plot(df.index, df["Close"], color=ACCENT, linewidth=1.8,
            label="Close", zorder=3)
    ax.fill_between(df.index, df["Close"], df["Close"].min(),
                    alpha=0.08, color=ACCENT)

    # ── Overlays ──────────────────────────────────────────────────────────
    if "SMA 20" in indicators:
        ax.plot(df.index, compute_sma(df, 20),
                color=IND_COLORS["SMA 20"], lw=1.2, ls="--", label="SMA 20")

    if "SMA 50" in indicators:
        ax.plot(df.index, compute_sma(df, 50),
                color=IND_COLORS["SMA 50"], lw=1.2, ls="--", label="SMA 50")

    if "EMA 20" in indicators:
        ax.plot(df.index, compute_ema(df, 20),
                color=IND_COLORS["EMA 20"], lw=1.2, ls="-.", label="EMA 20")

    if "Bollinger Bands" in indicators:
        upper, mid, lower = compute_bollinger(df)
        c = IND_COLORS["Bollinger Bands"]
        ax.plot(df.index, upper, color=c, lw=0.8, ls=":")
        ax.plot(df.index, lower, color=c, lw=0.8, ls=":")
        ax.fill_between(df.index, upper, lower, alpha=0.07, color=c,
                        label="BB Bands")

    ax.set_title(f"{ticker}  —  Price Chart", color=TEXT_COLOR,
                 fontsize=12, fontweight="bold", pad=8)
    ax.set_ylabel("Price", color=SUBTEXT_COLOR, fontsize=9)
    ax.legend(loc="upper left", facecolor=CHART_BG,
              edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR, fontsize=8)

    # ── RSI panel ─────────────────────────────────────────────────────────
    if show_rsi:
        rsi = compute_rsi(df)
        ax2 = axes[1]
        _style_ax(ax2)
        ax2.plot(df.index, rsi, color=IND_COLORS["SMA 20"], lw=1.2, label="RSI 14")
        ax2.axhline(70, color=ACCENT2, lw=0.8, ls="--", alpha=0.7)
        ax2.axhline(30, color=ACCENT,  lw=0.8, ls="--", alpha=0.7)
        ax2.fill_between(df.index, rsi, 70, where=(rsi >= 70),
                         alpha=0.18, color=ACCENT2)
        ax2.fill_between(df.index, rsi, 30, where=(rsi <= 30),
                         alpha=0.18, color=ACCENT)
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI", color=SUBTEXT_COLOR, fontsize=9)
        ax2.legend(loc="upper left", facecolor=CHART_BG,
                   edgecolor=BORDER_COLOR, labelcolor=TEXT_COLOR, fontsize=8)

    fig.tight_layout(pad=1.5)
    return fig
