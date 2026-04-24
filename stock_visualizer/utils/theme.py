"""
utils/theme.py
==============
User-defined theme module for StockViz Pro.

HOW TO USE
----------
- Switch theme at runtime:   ThemeManager.toggle()
- Get current theme:         ThemeManager.current()   → Theme object
- Set a specific theme:      ThemeManager.set("light")
- Add your own theme:        ThemeManager.register(my_theme)

HOW TO ADD A CUSTOM THEME
--------------------------
from utils.theme import Theme, ThemeManager

MY_THEME = Theme(
    name       = "ocean",
    bg         = "#0a1628",
    header_bg  = "#061020",
    sidebar_bg = "#0d1f3c",
    card_bg    = "#122444",
    chart_bg   = "#0a1628",
    border     = "#1e3a5f",
    text       = "#cce4ff",
    subtext    = "#5588aa",
    section_fg = "#44aaff",
    accent     = "#00aaff",
    accent2    = "#ff4444",
    btn_hover  = "#0088dd",
    success    = "#00ccaa",
    error      = "#ff4444",
    ind_sma20  = "#ffcc66",
    ind_sma50  = "#ffffaa",
    ind_ema20  = "#ff8888",
    ind_bb     = "#88ddff",
)

ThemeManager.register(MY_THEME)
ThemeManager.set("ocean")
"""

from dataclasses import dataclass


# ─────────────────────────────────────────────────────────────────────────────
#  Theme Data Class
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Theme:
    name: str

    # ── Window / Layout ───────────────────────────────────────────────────────
    bg:         str   # root window background
    header_bg:  str   # top header bar
    sidebar_bg: str   # left sidebar
    card_bg:    str   # input cards / combo backgrounds
    chart_bg:   str   # matplotlib figure background
    border:     str   # divider / highlight border

    # ── Typography ────────────────────────────────────────────────────────────
    text:       str   # primary text
    subtext:    str   # secondary / hint text
    section_fg: str   # sidebar section header labels

    # ── Accent Colours ────────────────────────────────────────────────────────
    accent:     str   # bullish / primary action (green / blue)
    accent2:    str   # bearish / danger (red)
    btn_hover:  str   # button hover state

    # ── Status Colours ────────────────────────────────────────────────────────
    success:    str
    error:      str

    # ── Chart Indicator Colours ───────────────────────────────────────────────
    ind_sma20:  str
    ind_sma50:  str
    ind_ema20:  str
    ind_bb:     str   # Bollinger Bands

    # ── Convenience props ─────────────────────────────────────────────────────
    @property
    def ind_colors(self) -> dict:
        return {
            "SMA 20":          self.ind_sma20,
            "SMA 50":          self.ind_sma50,
            "EMA 20":          self.ind_ema20,
            "Bollinger Bands": self.ind_bb,
        }


# ─────────────────────────────────────────────────────────────────────────────
#  Built-in Themes
# ─────────────────────────────────────────────────────────────────────────────

DARK = Theme(
    name       = "dark",
    bg         = "#0d0d1a",
    header_bg  = "#070714",
    sidebar_bg = "#13132b",
    card_bg    = "#1a1a35",
    chart_bg   = "#0d0d1a",
    border     = "#2a2a4a",
    text       = "#e0e0f0",
    subtext    = "#6666aa",
    section_fg = "#4488ff",
    accent     = "#00d4aa",
    accent2    = "#e94560",
    btn_hover  = "#00b894",
    success    = "#00d4aa",
    error      = "#e94560",
    ind_sma20  = "#f7c59f",
    ind_sma50  = "#efefd0",
    ind_ema20  = "#ff6b6b",
    ind_bb     = "#a8dadc",
)

LIGHT = Theme(
    name       = "light",
    bg         = "#f4f6fb",
    header_bg  = "#ffffff",
    sidebar_bg = "#eaecf8",
    card_bg    = "#ffffff",
    chart_bg   = "#ffffff",
    border     = "#c8cde8",
    text       = "#1a1a2e",
    subtext    = "#5566aa",
    section_fg = "#1144cc",
    accent     = "#0066cc",
    accent2    = "#dd2244",
    btn_hover  = "#0055aa",
    success    = "#006644",
    error      = "#dd2244",
    ind_sma20  = "#cc7700",
    ind_sma50  = "#6633aa",
    ind_ema20  = "#cc0033",
    ind_bb     = "#0066cc",
)


# ─────────────────────────────────────────────────────────────────────────────
#  ThemeManager  (singleton-style, no instantiation needed)
# ─────────────────────────────────────────────────────────────────────────────

class ThemeManager:
    """
    Central theme manager. All modules read colours from here at runtime
    so a single toggle() call propagates everywhere.

    Example
    -------
    >>> from utils.theme import ThemeManager
    >>> t = ThemeManager.current()
    >>> print(t.accent)       # "#00d4aa"
    >>> ThemeManager.toggle()
    >>> print(t.is_dark)      # False
    """

    _active:   str  = "dark"
    _registry: dict = {"dark": DARK, "light": LIGHT}

    # ── Public API ────────────────────────────────────────────────────────────

    @classmethod
    def current(cls) -> Theme:
        """Return the active Theme object."""
        return cls._registry[cls._active]

    @classmethod
    def toggle(cls) -> Theme:
        """Switch between dark and light. Returns the new theme."""
        cls._active = "light" if cls._active == "dark" else "dark"
        return cls.current()

    @classmethod
    def set(cls, name: str) -> Theme:
        """Set theme by name. Raises ValueError for unknown names."""
        if name not in cls._registry:
            raise ValueError(
                f"Unknown theme '{name}'. Available: {list(cls._registry)}"
            )
        cls._active = name
        return cls.current()

    @classmethod
    def is_dark(cls) -> bool:
        """True when the active theme is 'dark'."""
        return cls._active == "dark"

    @classmethod
    def register(cls, theme: Theme) -> None:
        """
        Register a custom Theme so it can be used via set() or toggle().

        Parameters
        ----------
        theme : Theme
            A Theme dataclass instance. theme.name is used as the key.
        """
        if not isinstance(theme, Theme):
            raise TypeError("theme must be an instance of utils.theme.Theme")
        cls._registry[theme.name] = theme

    @classmethod
    def available(cls) -> list:
        """List all registered theme names."""
        return list(cls._registry.keys())
