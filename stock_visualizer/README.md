# Stock Data Visualizer 📈

A professional desktop stock market visualizer built with Python — dark-mode GUI, real-time data, and technical indicators.

## Features

- 📈 **Line Chart** with price + gradient fill
- 🕯️ **Candlestick Chart** (mplfinance dark theme)
- 📊 **Technical Indicators** — SMA 20/50, EMA 20, Bollinger Bands, RSI (14)
- ⚡ **Threaded data fetching** — no GUI freeze
- 🔄 **Auto-refresh** every 60 seconds
- 💾 **Save chart** as PNG / PDF / SVG
- 🔍 **Zoom & Pan** via built-in matplotlib toolbar

## Tech Stack

| Layer | Library |
|---|---|
| Data | `yfinance`, `pandas`, `numpy` |
| Charts | `matplotlib`, `mplfinance` |
| GUI | `tkinter` (built-in) |
| Networking | `requests`, `certifi` |

## Project Structure

```
stock_visualizer/
├── main.py                   # Entry point
├── config.py                 # Colors, settings, timeframes
├── requirements.txt
├── data/
│   └── fetch_data.py         # yfinance API + SSL fix
├── processing/
│   └── indicators.py         # SMA, EMA, RSI, Bollinger Bands
├── visualization/
│   ├── line_chart.py         # Matplotlib line chart
│   └── candle_chart.py       # mplfinance candlestick
├── gui/
│   └── app.py                # Tkinter GUI
└── utils/
    └── helpers.py            # Threading + formatters
```

## Installation

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

## Usage

1. Enter a ticker symbol (e.g. `AAPL`, `TSLA`, `INFY.NS`)
2. Select a timeframe: 1 Day / 1 Week / 1 Month / 3 Months / 1 Year
3. Choose chart type: **Line** or **Candlestick**
4. Toggle indicators via checkboxes
5. Click **⚡ Fetch Data**
