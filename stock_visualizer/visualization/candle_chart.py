import matplotlib
matplotlib.use("TkAgg")
import mplfinance as mpf
from matplotlib.figure import Figure
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.indicators import compute_sma, compute_ema, compute_rsi, compute_bollinger
from utils.theme import ThemeManager


def _build_mpf_style(t):
    """Build a fresh mplfinance style from the current theme."""
    return mpf.make_mpf_style(
        base_mpf_style="charles",
        marketcolors=mpf.make_marketcolors(
            up=t.accent, down=t.accent2,
            edge="inherit", wick="inherit",
            volume={"up": t.accent, "down": t.accent2},
        ),
        facecolor=t.chart_bg,
        figcolor=t.chart_bg,
        gridcolor=t.border,
        gridstyle="-",
        gridaxis="both",
        y_on_right=False,
        rc={
            "axes.labelcolor": t.subtext,
            "xtick.color":     t.subtext,
            "ytick.color":     t.subtext,
            "axes.edgecolor":  t.border,
            "font.size": 8,
        },
    )


def _safe_addplot(series, **kwargs):
    """Only build an addplot if the series has at least one non-NaN value."""
    if series.dropna().empty:
        return None
    return mpf.make_addplot(series, **kwargs)


def build_candle_figure(df: pd.DataFrame, indicators: list,
                        show_rsi: bool = False, ticker: str = "") -> Figure:
    """Build a themed mplfinance candlestick figure. Theme from ThemeManager."""
    t   = ThemeManager.current()
    sty = _build_mpf_style(t)
    c   = t.ind_colors

    addplots = []

    # ── Price overlays (panel 0) ───────────────────────────────────────────────
    if "SMA 20" in indicators:
        ap = _safe_addplot(compute_sma(df, 20),
                           color=c["SMA 20"], width=1.2, linestyle="--")
        if ap:
            addplots.append(ap)

    if "SMA 50" in indicators:
        ap = _safe_addplot(compute_sma(df, 50),
                           color=c["SMA 50"], width=1.2, linestyle="--")
        if ap:
            addplots.append(ap)

    if "EMA 20" in indicators:
        ap = _safe_addplot(compute_ema(df, 20),
                           color=c["EMA 20"], width=1.2, linestyle="-.")
        if ap:
            addplots.append(ap)

    if "Bollinger Bands" in indicators:
        upper, mid, lower = compute_bollinger(df)
        bc = c["Bollinger Bands"]
        for series, ls in [(upper, ":"), (mid, "--"), (lower, ":")]:
            ap = _safe_addplot(series, color=bc, width=0.8, linestyle=ls)
            if ap:
                addplots.append(ap)

    # ── RSI panel (panel 2) ────────────────────────────────────────────────────
    rsi_panel = 2
    if show_rsi:
        rsi = compute_rsi(df)
        if not rsi.dropna().empty:
            ap = _safe_addplot(rsi, panel=rsi_panel,
                               color=c["SMA 20"], ylabel="RSI", ylim=(0, 100))
            if ap:
                addplots.append(ap)
        else:
            show_rsi = False  # not enough data; skip the panel

    # Volume is always panel 1; RSI is panel 2
    panel_ratios = (4, 1, 1) if show_rsi else (4, 1)

    plot_kwargs = dict(
        type="candle",
        style=sty,
        volume=True,
        returnfig=True,
        figsize=(10, 6),
        panel_ratios=panel_ratios,
        warn_too_much_data=9999,
    )
    if addplots:
        plot_kwargs["addplot"] = addplots

    fig, axes = mpf.plot(df, **plot_kwargs)

    fig.suptitle(f"{ticker}  —  Candlestick Chart",
                 color=t.text, fontsize=12, fontweight="bold", y=0.99)
    # Do NOT call tight_layout on mplfinance figures — it conflicts with their
    # internal GridSpec and triggers a warning. Use subplots_adjust instead.
    fig.subplots_adjust(top=0.94, bottom=0.12, left=0.08, right=0.97,
                        hspace=0.06)
    return fig
