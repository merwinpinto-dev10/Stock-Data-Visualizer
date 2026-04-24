"""
StockViz Pro — Entry Point
Run: python main.py
"""
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from gui.app import StockVizApp


def main():
    root = tk.Tk()
    root.resizable(True, True)

    # App icon (ignore if not present)
    try:
        root.iconbitmap(default="")
    except Exception:
        pass

    app = StockVizApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
