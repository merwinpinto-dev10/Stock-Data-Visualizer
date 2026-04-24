import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.indicators import compute_sma, compute_ema, compute_bollinger, compute_rsi
from utils.theme import ThemeManager


def _style_ax(ax, t):
    ax.set_facecolor(t.chart_bg)
    ax.tick_params(colors=t.subtext, labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    for spine in ax.spines.values():
        spine.set_edgecolor(t.border)
    ax.grid(True, color=t.border, linewidth=0.5, alpha=0.7)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def build_line_figure(df: pd.DataFrame, indicators: list,
                      show_rsi: bool = False, ticker: str = "") -> Figure:
    """Build a themed matplotlib line chart. Theme is read from ThemeManager."""
    t = ThemeManager.current()

    nrows  = 2 if show_rsi else 1
    ratios = [3, 1] if show_rsi else [1]

    fig, axes = plt.subplots(
        nrows, 1, figsize=(10, 6),
        gridspec_kw={"height_ratios": ratios},
        facecolor=t.chart_bg,
    )
    if nrows == 1:
        axes = [axes]

    ax = axes[0]
    _style_ax(ax, t)

    # Price line + gradient fill
    ax.plot(df.index, df["Close"], color=t.accent, linewidth=1.8,
            label="Close", zorder=3)
    ax.fill_between(df.index, df["Close"], df["Close"].min(),
                    alpha=0.08, color=t.accent)

    #  Overlays 
    c = t.ind_colors

    if "SMA 20" in indicators:
        ax.plot(df.index, compute_sma(df, 20),
                color=c["SMA 20"], lw=1.2, ls="--", label="SMA 20")

    if "SMA 50" in indicators:
        ax.plot(df.index, compute_sma(df, 50),
                color=c["SMA 50"], lw=1.2, ls="--", label="SMA 50")

    if "EMA 20" in indicators:
        ax.plot(df.index, compute_ema(df, 20),
                color=c["EMA 20"], lw=1.2, ls="-.", label="EMA 20")

    if "Bollinger Bands" in indicators:
        upper, mid, lower = compute_bollinger(df)
        bc = c["Bollinger Bands"]
        ax.plot(df.index, upper, color=bc, lw=0.8, ls=":")
        ax.plot(df.index, lower, color=bc, lw=0.8, ls=":")
        ax.fill_between(df.index, upper, lower, alpha=0.07, color=bc,
                        label="BB Bands")

    ax.set_title(f"{ticker}  —  Price Chart", color=t.text,
                 fontsize=12, fontweight="bold", pad=8)
    ax.set_ylabel("Price", color=t.subtext, fontsize=9)
    ax.legend(loc="upper left", facecolor=t.chart_bg,
              edgecolor=t.border, labelcolor=t.text, fontsize=8)

    #  RSI panel  
    if show_rsi:
        rsi = compute_rsi(df)
        ax2 = axes[1]
        _style_ax(ax2, t)
        valid = rsi.dropna()
        if not valid.empty:
            ax2.plot(df.index, rsi, color=c["SMA 20"], lw=1.2, label="RSI 14")
            ax2.axhline(70, color=t.accent2, lw=0.8, ls="--", alpha=0.7)
            ax2.axhline(30, color=t.accent,  lw=0.8, ls="--", alpha=0.7)
            mask_ob = rsi.notna() & (rsi >= 70)
            mask_os = rsi.notna() & (rsi <= 30)
            ax2.fill_between(df.index, rsi, 70, where=mask_ob,
                             alpha=0.18, color=t.accent2)
            ax2.fill_between(df.index, rsi, 30, where=mask_os,
                             alpha=0.18, color=t.accent)
        else:
            ax2.text(0.5, 0.5, "Not enough data for RSI",
                     transform=ax2.transAxes, ha="center", va="center",
                     color=t.subtext, fontsize=9)
        ax2.set_ylim(0, 100)
        ax2.set_ylabel("RSI", color=t.subtext, fontsize=9)
        ax2.legend(loc="upper left", facecolor=t.chart_bg,
                   edgecolor=t.border, labelcolor=t.text, fontsize=8)

    fig.tight_layout(pad=1.5)
    return fig
