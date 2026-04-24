"""
StockViz Pro — GUI v3 (Light/Dark theme support)
Theme switching is powered by utils/theme.py (user-defined module).
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime
import sys, os

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (APP_TITLE, DEFAULT_TICKER, REFRESH_INTERVAL_MS,
                    TIMEFRAMES, CHART_TYPES, INDICATORS)
from utils.theme import ThemeManager
from data.fetch_data import fetch_stock_data, get_ticker_info
from visualization.line_chart import build_line_figure
from visualization.candle_chart import build_candle_figure
from utils.helpers import run_in_thread, format_currency
from utils.watchlist import load_watchlist, wl_add, wl_remove


class StockVizApp:

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1300x800")
        self.root.minsize(1000, 650)

        # ── State ────────────────────────────────────────────────────────────
        self.current_df      = None
        self.current_fig     = None
        self.current_ticker  = ""
        self.canvas_widget   = None
        self.auto_refresh_id = None
        self.clock_after_id  = None
        self.is_loading      = False
        self._active_btn    = None   # currently highlighted preset/watchlist btn
        self._watchlist     = load_watchlist()
        self._wl_frame      = None   # container rebuilt on each add/remove

        # ── Tkinter Variables ────────────────────────────────────────────────
        self.ticker_var       = tk.StringVar(value=DEFAULT_TICKER)
        self.timeframe_var    = tk.StringVar(value="1 Month")
        self.chart_type_var   = tk.StringVar(value="Line")
        self.indicator_vars   = {ind: tk.BooleanVar(value=False) for ind in INDICATORS}
        self.show_rsi_var     = tk.BooleanVar(value=False)

        # Auto re-render when any indicator or chart type changes
        for var in self.indicator_vars.values():
            var.trace_add("write", lambda *_: self._on_indicator_change())
        self.show_rsi_var.trace_add("write",   lambda *_: self._on_indicator_change())
        self.chart_type_var.trace_add("write", lambda *_: self._on_indicator_change())

        # Timeframe change → full re-fetch (new data needed, not just re-render)
        self.timeframe_var.trace_add("write", lambda *_: self.fetch_data())

        # ── Widget registry for theme switching ──────────────────────────────
        # Each entry: (widget, {tkinter_option: theme_attribute_name})
        self._tw = []

        self._setup_ttk_styles()
        self._build_ui()
        self._apply_theme()       # initial paint
        self._start_clock()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(700, self.fetch_data)

    # ── Theme helpers ─────────────────────────────────────────────────────────

    def _t(self):
        """Shorthand: return current Theme object."""
        return ThemeManager.current()

    def _reg(self, widget, **options):
        """
        Register a widget for automatic re-theming.
        options maps tkinter option → Theme attribute name.
        Example:  self._reg(lbl, bg="card_bg", fg="text")
        """
        self._tw.append((widget, options))
        return widget

    def _apply_theme(self):
        """Re-colour every registered widget from the current theme."""
        t = self._t()
        # Update root background
        self.root.configure(bg=t.bg)

        for widget, options in self._tw:
            # Skip sentinel attrs (e.g. fixed hex fg colours that have no theme key)
            cfg = {opt: getattr(t, attr)
                   for opt, attr in options.items()
                   if hasattr(t, attr)}
            try:
                widget.config(**cfg)
            except tk.TclError:
                pass

        # TTK styles must be rebuilt per theme
        self._setup_ttk_styles()

        # Update theme toggle button label
        if hasattr(self, "theme_btn"):
            self.theme_btn.config(
                text="☀️  Light Mode" if ThemeManager.is_dark() else "🌙  Dark Mode",
                bg=t.card_bg, fg=t.text,
            )

        # Re-colour toolbar icons strip without a full chart re-render
        self._update_toolbar_theme()

        # Re-render chart with new palette if data is loaded
        if self.current_df is not None and self.current_ticker:
            self._render_chart(self.current_df, self.current_ticker)

    def _toggle_theme(self):
        ThemeManager.toggle()
        self._apply_theme()

    def _setup_ttk_styles(self):
        t = self._t()
        s = ttk.Style()
        s.theme_use("clam")
        s.configure(".", background=t.bg, foreground=t.text, font=("Segoe UI", 10))
        s.configure("TCombobox",
                    fieldbackground=t.card_bg, background=t.card_bg,
                    foreground=t.text, selectbackground=t.accent,
                    arrowcolor=t.accent, padding=6)
        s.map("TCombobox",
              fieldbackground=[("readonly", t.card_bg)],
              foreground=[("readonly", t.text)])
        for style in ("TCheckbutton", "TRadiobutton"):
            s.configure(style, background=t.sidebar_bg, foreground=t.text,
                        font=("Segoe UI", 10))
            s.map(style,
                  background=[("active", t.sidebar_bg)],
                  foreground=[("active", t.accent)])

    # ── Window close ──────────────────────────────────────────────────────────

    def _on_close(self):
        if self.clock_after_id:
            self.root.after_cancel(self.clock_after_id)
        if self.auto_refresh_id:
            self.root.after_cancel(self.auto_refresh_id)
        self.root.destroy()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        t = self._t()
        self._build_header()
        body = self._reg(tk.Frame(self.root, bg=t.bg), bg="bg")
        body.pack(fill="both", expand=True)
        self._build_sidebar(body)
        self._build_main(body)
        self._build_statusbar()

    # ── Header ────────────────────────────────────────────────────────────────

    def _build_header(self):
        t = self._t()
        hdr = self._reg(tk.Frame(self.root, bg=t.header_bg, height=62), bg="header_bg")
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        left = self._reg(tk.Frame(hdr, bg=t.header_bg), bg="header_bg")
        left.pack(side="left", padx=22, pady=10)

        self._reg(tk.Label(left, text="📈", bg=t.header_bg,
                           font=("Segoe UI", 20)), bg="header_bg")
        self._reg(tk.Label(left, text="  StockViz Pro", bg=t.header_bg,
                           fg=t.accent, font=("Segoe UI", 18, "bold")),
                  bg="header_bg", fg="accent").pack(side="left")
        self._reg(tk.Label(left, text="  Real-time Market Visualizer",
                           bg=t.header_bg, fg=t.subtext,
                           font=("Segoe UI", 10)), bg="header_bg", fg="subtext").pack(
            side="left", pady=(6, 0))

        # Right cluster
        right = self._reg(tk.Frame(hdr, bg=t.header_bg), bg="header_bg")
        right.pack(side="right", padx=22, pady=8)

        # Theme toggle button
        self.theme_btn = tk.Button(
            right,
            text="☀️  Light Mode",
            command=self._toggle_theme,
            font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2",
            padx=12, pady=5,
        )
        self.theme_btn.pack(side="top", anchor="e", pady=(0, 4))
        self._reg(self.theme_btn, bg="card_bg", fg="text")

        self.clock_lbl = self._reg(
            tk.Label(right, text="", font=("Segoe UI", 9)),
            bg="header_bg", fg="subtext",
        )
        self.clock_lbl.pack(anchor="e")

        self.header_price_lbl = self._reg(
            tk.Label(right, text="", font=("Segoe UI", 11, "bold")),
            bg="header_bg",
        )
        self.header_price_lbl.pack(anchor="e")

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent):
        t = self._t()
        sb_outer = self._reg(tk.Frame(parent, bg=t.sidebar_bg, width=265),
                             bg="sidebar_bg")
        sb_outer.pack(side="left", fill="y")
        sb_outer.pack_propagate(False)

        self._sb_canvas = self._reg(
            tk.Canvas(sb_outer, bg=t.sidebar_bg, highlightthickness=0, bd=0),
            bg="sidebar_bg",
        )
        cv = self._sb_canvas
        scrollbar = ttk.Scrollbar(sb_outer, orient="vertical", command=cv.yview)
        self.sb_inner = self._reg(tk.Frame(cv, bg=t.sidebar_bg), bg="sidebar_bg")

        # Update scroll region whenever inner frame resizes
        self.sb_inner.bind(
            "<Configure>",
            lambda e: cv.configure(scrollregion=cv.bbox("all")),
        )
        # Keep inner frame width = canvas width (prevents horizontal gap)
        cv.bind(
            "<Configure>",
            lambda e: cv.itemconfig(self._sb_win_id, width=e.width),
        )

        self._sb_win_id = cv.create_window((0, 0), window=self.sb_inner, anchor="nw")
        cv.configure(yscrollcommand=scrollbar.set)

        cv.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # ── Mouse-wheel scrolling (Windows + Linux) ───────────────────────────
        def _on_mousewheel(event):
            cv.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def _on_mousewheel_linux(event):
            cv.yview_scroll(-1 if event.num == 4 else 1, "units")

        cv.bind_all("<MouseWheel>",   _on_mousewheel)        # Windows / macOS
        cv.bind_all("<Button-4>",     _on_mousewheel_linux)  # Linux scroll up
        cv.bind_all("<Button-5>",     _on_mousewheel_linux)  # Linux scroll down

        self._build_sidebar_content(self.sb_inner)

    def _build_sidebar_content(self, sb):
        t = self._t()

        # ── TICKER ───────────────────────────────────────────────────────────
        self._section_header(sb, "🔍  TICKER SYMBOL")

        ticker_card = self._reg(
            tk.Frame(sb, bg=t.card_bg, padx=12, pady=10,
                     highlightbackground=t.border, highlightthickness=1),
            bg="card_bg",
        )
        ticker_card.pack(fill="x", padx=14, pady=(0, 4))

        # Entry + "+" watchlist add button side by side
        entry_row = self._reg(tk.Frame(ticker_card, bg=t.card_bg), bg="card_bg")
        entry_row.pack(fill="x")

        self.ticker_entry = self._reg(
            tk.Entry(entry_row, textvariable=self.ticker_var,
                     font=("Segoe UI", 16, "bold"), relief="flat", width=8),
            bg="card_bg", fg="accent", insertbackground="accent",
        )
        self.ticker_entry.pack(side="left", fill="x", expand=True)
        self.ticker_entry.bind("<Return>", lambda _: self.fetch_data())

        add_btn = tk.Button(
            entry_row, text="＋", command=self._add_to_watchlist,
            bg=t.accent, fg="#000000", font=("Segoe UI", 12, "bold"),
            relief="flat", cursor="hand2", padx=8, pady=2,
            activebackground=t.btn_hover, activeforeground="#000000",
        )
        add_btn.pack(side="right", padx=(6, 0))
        self._reg(add_btn, bg="accent")

        self._reg(
            tk.Label(ticker_card, text="Press Enter or ＋ to add to watchlist",
                     font=("Segoe UI", 8)),
            bg="card_bg", fg="subtext",
        ).pack(anchor="w", pady=(3, 0))

        # ── FETCH button right below entry ────────────────────────────────────
        self.fetch_btn = self._make_btn(
            sb, "⚡   Fetch Data", self.fetch_data,
            bg_attr="accent", fg="#000000",
        )
        self.fetch_btn.pack(fill="x", padx=14, pady=(6, 2))

        # ── Divider ──────────────────────────────────────────────────────────
        self._reg(tk.Frame(sb, height=1), bg="border").pack(fill="x", padx=14, pady=10)

        # ── QUICK ACCESS presets ──────────────────────────────────────────────
        self._section_header(sb, "⚡  QUICK ACCESS")
        presets_frame = self._reg(tk.Frame(sb, bg=t.sidebar_bg), bg="sidebar_bg")
        presets_frame.pack(fill="x", padx=14, pady=(0, 6))

        self._preset_btns = {}
        PRESETS = ["MSFT", "AAPL", "GOOGL", "TSLA", "AMZN", "NVDA"]
        for i, sym in enumerate(PRESETS):
            btn = tk.Button(
                presets_frame, text=sym,
                font=("Segoe UI", 8, "bold"),
                relief="flat", cursor="hand2",
                padx=6, pady=5,
            )
            btn.config(command=lambda s=sym, b=btn: self._on_preset_click(s, b))
            btn.grid(row=i // 3, column=i % 3, padx=3, pady=3, sticky="ew")
            presets_frame.columnconfigure(i % 3, weight=1)
            self._preset_btns[sym] = btn
            self._style_quick_btn(btn, active=False)

        # ── Divider ──────────────────────────────────────────────────────────
        self._reg(tk.Frame(sb, height=1), bg="border").pack(fill="x", padx=14, pady=10)

        # ── WATCHLIST ─────────────────────────────────────────────────────────
        self._section_header(sb, "📋  WATCHLIST")
        self._wl_container = self._reg(tk.Frame(sb, bg=t.sidebar_bg), bg="sidebar_bg")
        self._wl_container.pack(fill="x", padx=14, pady=(0, 10))
        self._rebuild_watchlist_ui()

        # ── Divider ──────────────────────────────────────────────────────────
        self._reg(tk.Frame(sb, height=1), bg="border").pack(fill="x", padx=14, pady=10)

        # ── TIMEFRAME ────────────────────────────────────────────────────────
        self._section_header(sb, "📅  TIMEFRAME")
        self.tf_combo = ttk.Combobox(
            sb, textvariable=self.timeframe_var,
            values=list(TIMEFRAMES.keys()), state="readonly",
            width=22, font=("Segoe UI", 10),
        )
        self.tf_combo.pack(fill="x", padx=14, pady=(0, 10))

        # ── CHART TYPE ───────────────────────────────────────────────────────
        self._section_header(sb, "📊  CHART TYPE")
        ct_frame = self._reg(tk.Frame(sb, bg=t.sidebar_bg), bg="sidebar_bg")
        ct_frame.pack(fill="x", padx=14, pady=(0, 10))
        for ct in CHART_TYPES:
            ttk.Radiobutton(ct_frame, text=f"  {ct}",
                            variable=self.chart_type_var, value=ct).pack(anchor="w", pady=3)

        # ── INDICATORS ───────────────────────────────────────────────────────
        self._section_header(sb, "🧮  INDICATORS")
        ind_frame = self._reg(tk.Frame(sb, bg=t.sidebar_bg), bg="sidebar_bg")
        ind_frame.pack(fill="x", padx=14, pady=(0, 4))

        descs = {
            "SMA 20": "Simple MA (fast)",  "SMA 50": "Simple MA (slow)",
            "EMA 20": "Exponential MA",    "Bollinger Bands": "Volatility bands",
        }
        for ind, var in self.indicator_vars.items():
            row = self._reg(tk.Frame(ind_frame, bg=t.sidebar_bg), bg="sidebar_bg")
            row.pack(fill="x", pady=2)
            ttk.Checkbutton(row, text=f"  {ind}", variable=var).pack(side="left")
            self._reg(tk.Label(row, text=descs.get(ind, ""),
                               font=("Segoe UI", 8)),
                      bg="sidebar_bg", fg="subtext").pack(side="left", padx=(4, 0))

        rsi_row = self._reg(tk.Frame(ind_frame, bg=t.sidebar_bg), bg="sidebar_bg")
        rsi_row.pack(fill="x", pady=2)
        ttk.Checkbutton(rsi_row, text="  RSI (14)",
                        variable=self.show_rsi_var).pack(side="left")
        self._reg(tk.Label(rsi_row, text="Momentum oscillator",
                           font=("Segoe UI", 8)),
                  bg="sidebar_bg", fg="subtext").pack(side="left", padx=(4, 0))

        # ── Divider ──────────────────────────────────────────────────────────
        self._reg(tk.Frame(sb, height=1), bg="border").pack(fill="x", padx=14, pady=10)

        # ── ACTIONS ──────────────────────────────────────────────────────────
        self._section_header(sb, "⚙️  ACTIONS")

        self.refresh_btn = self._make_btn(
            sb, "🔄   Auto Refresh: OFF", self.toggle_auto_refresh,
            bg_attr="card_bg", fg_attr="text",
        )
        self.refresh_btn.pack(fill="x", padx=14, pady=(0, 6))

        self._make_btn(sb, "💾   Save Chart", self.save_chart,
                       bg_attr="card_bg", fg_attr="text",
                       ).pack(fill="x", padx=14, pady=(0, 6))

        # ── Tips ─────────────────────────────────────────────────────────────
        self._reg(tk.Frame(sb, height=1), bg="border").pack(fill="x", padx=14, pady=10)
        tips_card = self._reg(tk.Frame(sb, padx=10, pady=8), bg="card_bg")
        tips_card.pack(fill="x", padx=14, pady=(0, 14))
        self._reg(tk.Label(tips_card, text="💡 Tips",
                           font=("Segoe UI", 9, "bold")),
                  bg="card_bg", fg="accent").pack(anchor="w")
        for tip in [
            "Indian stocks: add .NS\n(e.g. RELIANCE.NS)",
            "Zoom: drag on chart\nReset: Home button",
            "SMA 50 needs ≥ 50\ndata points to appear",
        ]:
            self._reg(tk.Label(tips_card, text=f"• {tip}",
                               font=("Segoe UI", 8), justify="left"),
                      bg="card_bg", fg="subtext").pack(anchor="w", pady=2)

    # ── Preset / Watchlist helpers ────────────────────────────────────────────

    def _style_quick_btn(self, btn, active: bool):
        """Apply active or inactive style to a preset/watchlist button."""
        t = self._t()
        if active:
            btn.config(bg=t.accent, fg="#000000",
                       activebackground=t.btn_hover, activeforeground="#000000")
        else:
            btn.config(bg=t.card_bg, fg=t.accent,
                       activebackground=t.border, activeforeground=t.accent)

    def _set_active_btn(self, btn):
        """Highlight *btn* as active and deactivate all others."""
        if self._active_btn and self._active_btn is not btn:
            try:
                self._style_quick_btn(self._active_btn, active=False)
            except tk.TclError:
                pass
        self._active_btn = btn
        self._style_quick_btn(btn, active=True)

    def _on_preset_click(self, symbol: str, btn):
        self.ticker_var.set(symbol)
        self._set_active_btn(btn)
        self.fetch_data()

    def _on_watchlist_click(self, symbol: str, btn):
        self.ticker_var.set(symbol)
        self._set_active_btn(btn)
        self.fetch_data()

    def _add_to_watchlist(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            return
        added = wl_add(self._watchlist, ticker)
        if added:
            self._rebuild_watchlist_ui()
        self._set_status(
            f"✔  '{ticker}' added to watchlist" if added
            else f"ℹ  '{ticker}' is already in watchlist"
        )

    def _remove_from_watchlist(self, ticker: str):
        wl_remove(self._watchlist, ticker)
        # If this was the active ticker, clear active btn
        if (self._active_btn is not None and
                getattr(self._active_btn, "_wl_ticker", None) == ticker):
            self._active_btn = None
        self._rebuild_watchlist_ui()

    def _rebuild_watchlist_ui(self):
        """Destroy and rebuild the watchlist button list."""
        if not hasattr(self, "_wl_container") or self._wl_container is None:
            return
        t = self._t()
        for w in self._wl_container.winfo_children():
            w.destroy()

        if not self._watchlist:
            tk.Label(self._wl_container, text="No items yet — press ＋",
                     bg=t.sidebar_bg, fg=t.subtext,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=4)
            return

        for sym in self._watchlist:
            row = tk.Frame(self._wl_container, bg=t.sidebar_bg)
            row.pack(fill="x", pady=2)

            btn = tk.Button(
                row, text=sym,
                font=("Segoe UI", 9, "bold"),
                relief="flat", cursor="hand2",
                padx=8, pady=5, anchor="w",
            )
            # Tag button so we can identify it later
            btn._wl_ticker = sym
            btn.config(command=lambda s=sym, b=btn: self._on_watchlist_click(s, b))
            self._style_quick_btn(btn, active=False)
            btn.pack(side="left", fill="x", expand=True)

            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=t.border))
            btn.bind("<Leave>",
                     lambda e, b=btn: self._style_quick_btn(
                         b, active=(b is self._active_btn)))

            # × remove button
            rm = tk.Button(
                row, text="×",
                font=("Segoe UI", 10, "bold"),
                relief="flat", cursor="hand2",
                padx=6, pady=4,
                bg=t.sidebar_bg, fg=t.subtext,
                activebackground=t.accent2, activeforeground="#ffffff",
                command=lambda s=sym: self._remove_from_watchlist(s),
            )
            rm.pack(side="right")

    # ── Main Area ─────────────────────────────────────────────────────────────

    def _build_main(self, parent):
        t = self._t()
        main = self._reg(tk.Frame(parent), bg="bg")
        main.pack(side="left", fill="both", expand=True)

        # Stats bar
        self.stats_bar = self._reg(
            tk.Frame(main, pady=10,
                     highlightbackground=t.border, highlightthickness=1),
            bg="card_bg",
        )
        self.stats_bar.pack(fill="x", padx=12, pady=(10, 6))

        self.name_lbl = self._reg(
            tk.Label(self.stats_bar, text="Select a ticker →",
                     font=("Segoe UI", 14, "bold")),
            bg="card_bg", fg="text",
        )
        self.name_lbl.pack(side="left", padx=16)

        self.price_lbl = self._reg(
            tk.Label(self.stats_bar, text="",
                     font=("Segoe UI", 18, "bold")),
            bg="card_bg", fg="accent",
        )
        self.price_lbl.pack(side="left", padx=6)

        self.change_lbl = self._reg(
            tk.Label(self.stats_bar, text="",
                     font=("Segoe UI", 13)),
            bg="card_bg", fg="text",
        )
        self.change_lbl.pack(side="left", padx=6)

        self._reg(tk.Frame(self.stats_bar), bg="card_bg").pack(side="left", expand=True)

        self.ticker_badge = tk.Label(self.stats_bar, text="",
                                      font=("Segoe UI", 10, "bold"),
                                      padx=10, pady=3)
        self.ticker_badge.pack(side="right", padx=16)

        # Chart frame
        self.chart_frame = self._reg(
            tk.Frame(main, highlightbackground=t.border, highlightthickness=1),
            bg="chart_bg",
        )
        self.chart_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        self._show_placeholder()

    # ── Status Bar ───────────────────────────────────────────────────────────

    def _build_statusbar(self):
        t = self._t()
        sb = self._reg(tk.Frame(self.root, height=30), bg="header_bg")
        sb.pack(fill="x", side="bottom")
        sb.pack_propagate(False)

        self.dot_lbl = self._reg(
            tk.Label(sb, text="●", font=("Segoe UI", 10)),
            bg="header_bg", fg="subtext",
        )
        self.dot_lbl.pack(side="left", padx=(12, 4), fill="y")

        self.status_lbl = self._reg(
            tk.Label(sb, text="Ready  —  Enter a ticker and press ⚡ Fetch Data",
                     font=("Segoe UI", 9), anchor="w"),
            bg="header_bg", fg="subtext",
        )
        self.status_lbl.pack(side="left", fill="y")

        self.loading_lbl = self._reg(
            tk.Label(sb, text="", font=("Segoe UI", 9)),
            bg="header_bg", fg="accent",
        )
        self.loading_lbl.pack(side="right", padx=14)

    # ── Widget Helpers ────────────────────────────────────────────────────────

    def _section_header(self, parent, text):
        t = self._t()
        lbl = self._reg(
            tk.Label(parent, text=text, font=("Segoe UI", 9, "bold")),
            bg="sidebar_bg", fg="section_fg",
        )
        lbl.pack(anchor="w", padx=14, pady=(14, 4))

    def _make_btn(self, parent, text, cmd,
                  bg_attr="card_bg", fg_attr=None, fg="#000000"):
        t = self._t()
        bg = getattr(t, bg_attr)
        fg = getattr(t, fg_attr) if fg_attr else fg
        hover = t.btn_hover if bg_attr == "accent" else t.border
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=bg, fg=fg, activebackground=hover, activeforeground=fg,
                        font=("Segoe UI", 10, "bold"), relief="flat",
                        cursor="hand2", padx=10, pady=10, anchor="w")
        btn.bind("<Enter>", lambda _: btn.config(bg=hover))
        btn.bind("<Leave>", lambda _: btn.config(bg=getattr(self._t(), bg_attr)))
        # Register for re-theming
        # Only register fg if it maps to a theme attribute
        reg_opts = {"bg": bg_attr}
        if fg_attr:
            reg_opts["fg"] = fg_attr
        self._reg(btn, **reg_opts)
        return btn

    def _show_placeholder(self):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        t = self._t()
        ph = tk.Frame(self.chart_frame, bg=t.chart_bg)
        ph.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(ph, text="📊", bg=t.chart_bg,
                 font=("Segoe UI", 48)).pack()
        tk.Label(ph, text="No data loaded yet",
                 bg=t.chart_bg, fg=t.text,
                 font=("Segoe UI", 16, "bold")).pack(pady=(8, 4))
        tk.Label(ph,
                 text="Enter a ticker symbol (e.g. AAPL, TSLA, RELIANCE.NS)\nand click  ⚡ Fetch Data  to begin.",
                 bg=t.chart_bg, fg=t.subtext,
                 font=("Segoe UI", 11), justify="center").pack()

    def _start_clock(self):
        try:
            now = datetime.datetime.now().strftime("%a, %d %b %Y   %H:%M:%S")
            self.clock_lbl.config(text=now)
            self.clock_after_id = self.root.after(1000, self._start_clock)
        except tk.TclError:
            pass

    def _set_status(self, msg, color=None):
        t = self._t()
        c = color or t.subtext
        try:
            self.status_lbl.config(text=msg, fg=c)
            self.dot_lbl.config(fg=c)
        except tk.TclError:
            pass

    def _set_loading(self, loading: bool):
        t = self._t()
        self.is_loading = loading
        if loading:
            self.loading_lbl.config(text="⏳  Fetching data…")
            self.fetch_btn.config(state="disabled", text="⏳  Loading…", bg=t.border)
        else:
            self.loading_lbl.config(text="")
            self.fetch_btn.config(state="normal", text="⚡   Fetch Data", bg=t.accent)

    def _on_indicator_change(self):
        """Called whenever a checkbox or chart-type radio is toggled."""
        if self.current_df is not None and self.current_ticker and not self.is_loading:
            self._validate_indicators(self.current_df)
            self._render_chart(self.current_df, self.current_ticker)

    def _validate_indicators(self, df):
        """Warn the user if there's not enough data for a selected indicator."""
        t = self._t()
        warnings = []
        n = len(df)

        if self.indicator_vars.get("SMA 50", tk.BooleanVar()).get() and n < 50:
            warnings.append(f"SMA 50 needs ≥50 pts (have {n})")
        if self.indicator_vars.get("SMA 20", tk.BooleanVar()).get() and n < 20:
            warnings.append(f"SMA 20 needs ≥20 pts (have {n})")
        if self.indicator_vars.get("Bollinger Bands", tk.BooleanVar()).get() and n < 20:
            warnings.append(f"Bollinger Bands needs ≥20 pts (have {n})")
        if self.show_rsi_var.get() and n < 14:
            warnings.append(f"RSI needs ≥14 pts (have {n})")

        if warnings:
            self._set_status("⚠  " + "   |   ".join(warnings), t.accent2)

    # ── Fetch & Render ────────────────────────────────────────────────────────

    def fetch_data(self):
        if self.is_loading:
            return
        run_in_thread(self._fetch_worker)

    def _fetch_worker(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            self.root.after(0, lambda: self._set_status(
                "⚠  Please enter a ticker symbol.", self._t().error))
            return

        self.root.after(0, lambda: self._set_loading(True))
        self.root.after(0, lambda: self._set_status(
            f"Fetching data for  {ticker}…", self._t().accent))

        try:
            tf   = TIMEFRAMES[self.timeframe_var.get()]
            df   = fetch_stock_data(ticker, period=tf["period"], interval=tf["interval"])
            info = get_ticker_info(ticker)
            self.current_df     = df
            self.current_ticker = ticker
            self.root.after(0, lambda: self._update_ui(df, ticker, info))
        except Exception as exc:
            msg = str(exc)
            self.root.after(0, lambda: self._set_status(f"❌  {msg}", self._t().error))
            self.root.after(0, lambda: self._set_loading(False))

    def _update_ui(self, df, ticker, info):
        t = self._t()
        self.name_lbl.config(text=info.get("name", ticker))
        self.ticker_badge.config(text=f" {ticker} ", bg=t.accent, fg="#000000")

        if info.get("price"):
            self.price_lbl.config(text=format_currency(info["price"]))
            pct   = info.get("change", 0) or 0
            color = t.success if pct >= 0 else t.error
            arrow = "▲" if pct >= 0 else "▼"
            self.change_lbl.config(text=f"{arrow}  {abs(pct):.2f}%", fg=color)
            self.header_price_lbl.config(
                text=f"{ticker}   {format_currency(info['price'])}   {arrow} {abs(pct):.2f}%",
                fg=color,
            )

        self._render_chart(df, ticker)
        try:
            last = df.index[-1].strftime("%Y-%m-%d  %H:%M")
        except Exception:
            last = "—"
        self._set_status(
            f"✔  {len(df)} candles loaded for  {ticker}   │   Last: {last}",
            t.success,
        )
        self._set_loading(False)

    def _toolbar_bg(self) -> str:
        """
        Pick a toolbar strip background that keeps the dark bitmap icons
        visible in both themes.
          dark  mode → slightly lighter than card_bg so icons pop
          light mode → sidebar_bg (neutral light grey)
        """
        t = self._t()
        return "#2e2e52" if ThemeManager.is_dark() else t.sidebar_bg

    def _update_toolbar_theme(self):
        """Re-colour the matplotlib toolbar strip in-place (no chart re-render)."""
        bg = self._toolbar_bg()
        t  = self._t()
        if hasattr(self, "_toolbar_frame") and self._toolbar_frame:
            try:
                self._toolbar_frame.config(bg=bg)
            except tk.TclError:
                pass
        if hasattr(self, "_toolbar") and self._toolbar:
            try:
                self._toolbar.config(background=bg)
            except tk.TclError:
                return
            for child in self._toolbar.winfo_children():
                try:
                    child.config(background=bg, foreground=t.text,
                                 activebackground=t.border,
                                 activeforeground=t.text)
                except tk.TclError:
                    pass

    def _render_chart(self, df, ticker):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        self._toolbar       = None
        self._toolbar_frame = None

        indicators = [ind for ind, var in self.indicator_vars.items() if var.get()]
        show_rsi   = self.show_rsi_var.get()
        chart_type = self.chart_type_var.get()

        try:
            fig = (build_line_figure(df, indicators, show_rsi, ticker)
                   if chart_type == "Line"
                   else build_candle_figure(df, indicators, show_rsi, ticker))
            self.current_fig = fig

            # ── Toolbar strip ───────────────────────────────────────────────
            tbar_bg = self._toolbar_bg()
            t = self._t()

            self._toolbar_frame = tk.Frame(self.chart_frame, bg=tbar_bg)
            self._toolbar_frame.pack(side="bottom", fill="x")

            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            self._toolbar = NavigationToolbar2Tk(canvas, self._toolbar_frame)
            self._toolbar.config(background=tbar_bg)
            for child in self._toolbar.winfo_children():
                try:
                    child.config(background=tbar_bg, foreground=t.text,
                                 activebackground=t.border,
                                 activeforeground=t.text)
                except Exception:
                    pass
            self._toolbar.update()
            self.canvas_widget = canvas

        except Exception as exc:
            self._set_status(f"❌  Chart error: {exc}", self._t().error)

    # ── Auto-refresh ──────────────────────────────────────────────────────────

    def toggle_auto_refresh(self):
        t = self._t()
        if self.auto_refresh_id is not None:
            self.root.after_cancel(self.auto_refresh_id)
            self.auto_refresh_id = None
            self.refresh_btn.config(text="🔄   Auto Refresh: OFF",
                                     bg=t.card_bg, fg=t.text)
            self._set_status("Auto-refresh paused.")
        else:
            self._schedule_refresh()
            self.refresh_btn.config(text="⏹   Auto Refresh: ON",
                                     bg=t.accent2, fg="#ffffff")
            self._set_status(
                f"⟳  Auto-refresh active — updates every {REFRESH_INTERVAL_MS//1000}s",
                t.accent,
            )

    def _schedule_refresh(self):
        self.auto_refresh_id = self.root.after(REFRESH_INTERVAL_MS, self._auto_tick)

    def _auto_tick(self):
        self.fetch_data()
        self._schedule_refresh()

    # ── Save chart ────────────────────────────────────────────────────────────

    def save_chart(self):
        if self.current_fig is None:
            messagebox.showwarning("No Chart", "Please fetch data before saving.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF File", "*.pdf"), ("SVG Vector", "*.svg")],
            title="Save Chart As…",
        )
        if path:
            self.current_fig.savefig(path, dpi=150, bbox_inches="tight",
                                     facecolor=self._t().chart_bg)
            self._set_status(f"✔  Chart saved →  {path}", self._t().success)
