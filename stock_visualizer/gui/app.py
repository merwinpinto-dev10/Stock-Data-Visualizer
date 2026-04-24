"""
StockViz Pro — GUI (Tkinter + embedded matplotlib)
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import sys
import os

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# Make sure root package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    APP_TITLE, DEFAULT_TICKER, REFRESH_INTERVAL_MS,
    BG_COLOR, SIDEBAR_BG, CARD_BG, CHART_BG,
    ACCENT, ACCENT2, TEXT_COLOR, SUBTEXT_COLOR, BORDER_COLOR,
    TIMEFRAMES, CHART_TYPES, INDICATORS,
)
from data.fetch_data import fetch_stock_data, get_ticker_info
from visualization.line_chart import build_line_figure
from visualization.candle_chart import build_candle_figure
from utils.helpers import run_in_thread, format_currency


# ─────────────────────────────────────────────────────────────────────────────
class StockVizApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x780")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(960, 620)

        # ── State ────────────────────────────────────────────────────────────
        self.current_df    = None
        self.current_fig   = None
        self.canvas_widget = None
        self.toolbar       = None
        self.auto_refresh_id = None
        self.is_loading    = False

        # ── Tkinter Variables ────────────────────────────────────────────────
        self.ticker_var    = tk.StringVar(value=DEFAULT_TICKER)
        self.timeframe_var = tk.StringVar(value="1 Month")
        self.chart_type_var = tk.StringVar(value="Line")
        self.indicator_vars = {ind: tk.BooleanVar(value=False) for ind in INDICATORS}
        self.show_rsi_var  = tk.BooleanVar(value=False)
        self.auto_refresh_var = tk.BooleanVar(value=False)

        self._setup_styles()
        self._build_ui()
        self._start_clock()

        # Load default ticker on startup
        self.root.after(600, self.fetch_data)

    # ── Styles ────────────────────────────────────────────────────────────────
    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".",
                     background=BG_COLOR, foreground=TEXT_COLOR,
                     font=("Segoe UI", 9))
        s.configure("Sidebar.TFrame",  background=SIDEBAR_BG)
        s.configure("Card.TFrame",     background=CARD_BG)
        s.configure("TCombobox",
                     fieldbackground=CARD_BG, background=CARD_BG,
                     foreground=TEXT_COLOR, selectbackground=ACCENT,
                     arrowcolor=TEXT_COLOR)
        s.map("TCombobox", fieldbackground=[("readonly", CARD_BG)])
        for style, bg, fg in [
            ("TCheckbutton", SIDEBAR_BG, TEXT_COLOR),
            ("TRadiobutton", SIDEBAR_BG, TEXT_COLOR),
        ]:
            s.configure(style, background=bg, foreground=fg,
                        font=("Segoe UI", 9))
            s.map(style, background=[("active", SIDEBAR_BG)])

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        body = tk.Frame(self.root, bg=BG_COLOR)
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_main(body)
        self._build_statusbar()

    # Header ──────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self.root, bg="#0b0b1f", height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        tk.Label(hdr, text="📈  StockViz Pro",
                 bg="#0b0b1f", fg=ACCENT,
                 font=("Segoe UI", 17, "bold")).pack(side="left", padx=22, pady=10)

        self.clock_lbl = tk.Label(hdr, text="", bg="#0b0b1f",
                                   fg=SUBTEXT_COLOR, font=("Segoe UI", 10))
        self.clock_lbl.pack(side="right", padx=22)

        # Live price tag (updates after fetch)
        self.header_price_lbl = tk.Label(hdr, text="", bg="#0b0b1f",
                                          fg=TEXT_COLOR, font=("Segoe UI", 12, "bold"))
        self.header_price_lbl.pack(side="right", padx=10)

    # Sidebar ─────────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        sb = tk.Frame(parent, bg=SIDEBAR_BG, width=230)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)

        # ── Ticker ───────────────────────────────────────────────────────────
        self._slabel(sb, "TICKER SYMBOL")
        tf = tk.Frame(sb, bg=CARD_BG, padx=10, pady=6)
        tf.pack(fill="x", padx=14, pady=(0, 6))
        self.ticker_entry = tk.Entry(
            tf, textvariable=self.ticker_var,
            bg=CARD_BG, fg=ACCENT, insertbackground=ACCENT,
            font=("Segoe UI", 14, "bold"), relief="flat", width=12,
        )
        self.ticker_entry.pack(fill="x")
        self.ticker_entry.bind("<Return>", lambda _: self.fetch_data())

        # ── Timeframe ────────────────────────────────────────────────────────
        self._slabel(sb, "TIMEFRAME")
        self.tf_combo = ttk.Combobox(
            sb, textvariable=self.timeframe_var,
            values=list(TIMEFRAMES.keys()), state="readonly", width=20,
        )
        self.tf_combo.pack(fill="x", padx=14, pady=(0, 10))

        # ── Chart Type ───────────────────────────────────────────────────────
        self._slabel(sb, "CHART TYPE")
        ct_frame = tk.Frame(sb, bg=SIDEBAR_BG)
        ct_frame.pack(fill="x", padx=14, pady=(0, 10))
        for ct in CHART_TYPES:
            ttk.Radiobutton(ct_frame, text=ct,
                            variable=self.chart_type_var, value=ct).pack(anchor="w", pady=2)

        # ── Indicators ───────────────────────────────────────────────────────
        self._slabel(sb, "INDICATORS")
        ind_frame = tk.Frame(sb, bg=SIDEBAR_BG)
        ind_frame.pack(fill="x", padx=14, pady=(0, 4))
        for ind, var in self.indicator_vars.items():
            ttk.Checkbutton(ind_frame, text=ind, variable=var).pack(anchor="w", pady=1)
        ttk.Checkbutton(ind_frame, text="RSI (14)",
                        variable=self.show_rsi_var).pack(anchor="w", pady=1)

        # ── Divider ──────────────────────────────────────────────────────────
        tk.Frame(sb, bg=BORDER_COLOR, height=1).pack(fill="x", padx=14, pady=12)

        # ── Fetch Button ─────────────────────────────────────────────────────
        self.fetch_btn = tk.Button(
            sb, text="⚡  Fetch Data",
            command=self.fetch_data,
            bg=ACCENT, fg="#000000",
            font=("Segoe UI", 9, "bold"), relief="flat",
            cursor="hand2", padx=10, pady=9,
            activebackground="#00b894", activeforeground="#000000",
        )
        self.fetch_btn.pack(fill="x", padx=14, pady=3)

        # ── Auto-Refresh ─────────────────────────────────────────────────────
        self.refresh_btn = tk.Button(
            sb, text="🔄  Auto Refresh: OFF",
            command=self.toggle_auto_refresh,
            bg=CARD_BG, fg=TEXT_COLOR,
            font=("Segoe UI", 9), relief="flat",
            cursor="hand2", padx=10, pady=9,
        )
        self.refresh_btn.pack(fill="x", padx=14, pady=3)

        # ── Save Chart ───────────────────────────────────────────────────────
        tk.Button(
            sb, text="💾  Save Chart",
            command=self.save_chart,
            bg=CARD_BG, fg=TEXT_COLOR,
            font=("Segoe UI", 9), relief="flat",
            cursor="hand2", padx=10, pady=9,
        ).pack(fill="x", padx=14, pady=3)

    # Main area ───────────────────────────────────────────────────────────────
    def _build_main(self, parent):
        main = tk.Frame(parent, bg=BG_COLOR)
        main.pack(side="left", fill="both", expand=True)

        # Stats bar
        self.stats_bar = tk.Frame(main, bg=BG_COLOR)
        self.stats_bar.pack(fill="x", padx=14, pady=(10, 6))

        self.name_lbl   = tk.Label(self.stats_bar, text="—",
                                    bg=BG_COLOR, fg=TEXT_COLOR,
                                    font=("Segoe UI", 15, "bold"))
        self.name_lbl.pack(side="left")

        self.price_lbl  = tk.Label(self.stats_bar, text="",
                                    bg=BG_COLOR, fg=ACCENT,
                                    font=("Segoe UI", 15, "bold"))
        self.price_lbl.pack(side="left", padx=18)

        self.change_lbl = tk.Label(self.stats_bar, text="",
                                    bg=BG_COLOR, fg=TEXT_COLOR,
                                    font=("Segoe UI", 12))
        self.change_lbl.pack(side="left")

        # Chart canvas frame
        self.chart_frame = tk.Frame(main, bg=CHART_BG)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._show_placeholder()

    # Status bar ──────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        sb = tk.Frame(self.root, bg="#08081a", height=28)
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self.status_lbl = tk.Label(sb, text="Ready — enter a ticker and press ⚡ Fetch Data",
                                    bg="#08081a", fg=SUBTEXT_COLOR,
                                    font=("Segoe UI", 8), anchor="w")
        self.status_lbl.pack(side="left", padx=14, fill="y")

        self.loading_lbl = tk.Label(sb, text="", bg="#08081a",
                                     fg=ACCENT, font=("Segoe UI", 8))
        self.loading_lbl.pack(side="right", padx=14)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _slabel(self, parent, text):
        tk.Label(parent, text=text, bg=SIDEBAR_BG, fg=SUBTEXT_COLOR,
                 font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=14, pady=(12, 2))

    def _show_placeholder(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        tk.Label(
            self.chart_frame,
            text="Enter a ticker symbol and press\n⚡  Fetch Data to begin",
            bg=CHART_BG, fg=SUBTEXT_COLOR,
            font=("Segoe UI", 13),
        ).pack(expand=True)

    def _start_clock(self):
        self.clock_lbl.config(
            text=datetime.datetime.now().strftime("%Y-%m-%d   %H:%M:%S"))
        self.root.after(1000, self._start_clock)

    def _set_status(self, msg, color=None):
        self.status_lbl.config(text=msg, fg=color or SUBTEXT_COLOR)

    def _set_loading(self, loading: bool):
        self.is_loading = loading
        if loading:
            self.loading_lbl.config(text="⏳  Fetching…")
            self.fetch_btn.config(state="disabled", text="Loading…")
        else:
            self.loading_lbl.config(text="")
            self.fetch_btn.config(state="normal", text="⚡  Fetch Data")

    # ── Fetch + Render ────────────────────────────────────────────────────────
    def fetch_data(self):
        if self.is_loading:
            return
        run_in_thread(self._fetch_worker)

    def _fetch_worker(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            self.root.after(0, lambda: self._set_status("⚠  Please enter a ticker symbol.", ACCENT2))
            return

        self.root.after(0, lambda: self._set_loading(True))
        self.root.after(0, lambda: self._set_status(f"Fetching {ticker}…"))

        try:
            tf  = TIMEFRAMES[self.timeframe_var.get()]
            df  = fetch_stock_data(ticker, period=tf["period"], interval=tf["interval"])
            info = get_ticker_info(ticker)
            self.current_df = df
            self.root.after(0, lambda: self._update_ui(df, ticker, info))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda: self._set_status(f"❌  {msg}", ACCENT2))
            self.root.after(0, lambda: self._set_loading(False))

    def _update_ui(self, df, ticker, info):
        # Stats bar
        self.name_lbl.config(text=info["name"])
        if info["price"]:
            self.price_lbl.config(text=format_currency(info["price"]))
            pct   = info["change"]
            color = ACCENT if pct >= 0 else ACCENT2
            arrow = "▲" if pct >= 0 else "▼"
            self.change_lbl.config(text=f"{arrow} {abs(pct):.2f}%", fg=color)
            self.header_price_lbl.config(
                text=f"{ticker}  {format_currency(info['price'])}  {arrow} {abs(pct):.2f}%",
                fg=color,
            )

        self._render_chart(df, ticker)
        last = df.index[-1].strftime("%Y-%m-%d %H:%M") if hasattr(df.index[-1], "strftime") else ""
        self._set_status(
            f"✔  {len(df)} data points loaded for {ticker}   |   Last: {last}")
        self._set_loading(False)

    def _render_chart(self, df, ticker):
        # Tear down previous canvas
        for w in self.chart_frame.winfo_children():
            w.destroy()
        self.canvas_widget = None
        self.toolbar = None

        indicators = [ind for ind, var in self.indicator_vars.items() if var.get()]
        show_rsi   = self.show_rsi_var.get()
        chart_type = self.chart_type_var.get()

        try:
            if chart_type == "Line":
                fig = build_line_figure(df, indicators, show_rsi, ticker)
            else:
                fig = build_candle_figure(df, indicators, show_rsi, ticker)

            self.current_fig = fig

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()

            # Navigation toolbar (zoom/pan)
            toolbar_frame = tk.Frame(self.chart_frame, bg=BG_COLOR)
            toolbar_frame.pack(side="bottom", fill="x")
            toolbar = NavigationToolbar2Tk(canvas, toolbar_frame)
            toolbar.config(background=BG_COLOR)
            for child in toolbar.winfo_children():
                try:
                    child.config(background=BG_COLOR, foreground=TEXT_COLOR)
                except Exception:
                    pass
            toolbar.update()

            canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvas_widget = canvas

        except Exception as exc:
            self._set_status(f"❌  Chart error: {exc}", ACCENT2)

    # ── Auto-Refresh ──────────────────────────────────────────────────────────
    def toggle_auto_refresh(self):
        if self.auto_refresh_id is not None:
            self.root.after_cancel(self.auto_refresh_id)
            self.auto_refresh_id = None
            self.refresh_btn.config(text="🔄  Auto Refresh: OFF", bg=CARD_BG, fg=TEXT_COLOR)
            self._set_status("Auto-refresh disabled.")
        else:
            self._schedule_refresh()
            self.refresh_btn.config(text="⏹  Auto Refresh: ON", bg=ACCENT2, fg="#ffffff")
            self._set_status(f"Auto-refresh enabled (every {REFRESH_INTERVAL_MS//1000}s).")

    def _schedule_refresh(self):
        self.auto_refresh_id = self.root.after(REFRESH_INTERVAL_MS, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        self.fetch_data()
        self._schedule_refresh()

    # ── Save Chart ────────────────────────────────────────────────────────────
    def save_chart(self):
        if self.current_fig is None:
            messagebox.showwarning("No Chart", "Please fetch data first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")],
            title="Save Chart As…",
        )
        if path:
            self.current_fig.savefig(path, dpi=150, bbox_inches="tight",
                                     facecolor=CHART_BG)
            self._set_status(f"✔  Chart saved → {path}")
