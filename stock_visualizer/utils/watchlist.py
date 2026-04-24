

import json
import os

_WL_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "watchlist.json",
)

_DEFAULTS = ["MSFT", "AAPL", "GOOGL"]


def load_watchlist() -> list:
    """Load from JSON; return defaults if file is missing or corrupt."""
    try:
        if os.path.exists(_WL_FILE):
            with open(_WL_FILE, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(s).strip().upper() for s in data if s]
    except Exception:
        pass
    return _DEFAULTS.copy()


def save_watchlist(symbols: list) -> None:
    """Persist the current list to JSON."""
    try:
        with open(_WL_FILE, "w") as f:
            json.dump(symbols, f, indent=2)
    except Exception:
        pass


def wl_add(symbols: list, ticker: str) -> bool:
    """
    Add *ticker* if not already in *symbols*.
    Saves automatically.
    Returns True if added, False if duplicate.
    """
    ticker = ticker.strip().upper()
    if ticker and ticker not in symbols:
        symbols.append(ticker)
        save_watchlist(symbols)
        return True
    return False


def wl_remove(symbols: list, ticker: str) -> None:
    """Remove *ticker* from *symbols* and save."""
    ticker = ticker.strip().upper()
    if ticker in symbols:
        symbols.remove(ticker)
        save_watchlist(symbols)
