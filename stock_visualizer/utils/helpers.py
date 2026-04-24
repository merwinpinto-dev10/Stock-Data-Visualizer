import threading


def run_in_thread(fn, *args, **kwargs):
    """Run *fn* in a daemon background thread so the GUI stays responsive."""
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t


def format_currency(val: float, symbol: str = "$") -> str:
    if val >= 1_000_000_000:
        return f"{symbol}{val / 1_000_000_000:.2f}B"
    elif val >= 1_000_000:
        return f"{symbol}{val / 1_000_000:.2f}M"
    elif val >= 1_000:
        return f"{symbol}{val:,.2f}"
    return f"{symbol}{val:.2f}"


def format_pct(val: float) -> str:
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"
