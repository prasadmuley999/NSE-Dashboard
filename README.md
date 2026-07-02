# 📊 NSE Smart Decision Dashboard

Fully automated post-market intelligence dashboard for NIFTY 50 stocks.
Runs every weekday at **7:15 PM IST** via GitHub Actions.

## What it does

- Downloads NSE archive files (equity bhavcopy, MTO delivery, FO bhavcopy, FII/DII)
- Computes per-stock composite bullish/bearish scores
- Generates an Excel dashboard (`output/NSE_Dashboard.xlsx`)
- Generates a mobile-friendly HTML page (`output/index.html`) hosted on GitHub Pages
- Stores history in SQLite for multi-day averages and trend analysis

## Sheets in Excel

| Sheet | Contents |
|---|---|
| 📊 Dashboard | Signal summary, Top 5 gainers/losers, Sector analysis |
| 📋 Stock Detail | Full NIFTY50 table with 4-day delivery/price history |
| 💹 FII-DII | Today's FII/DII figures + 10-day trend |
| 📈 Signals | Composite scores and component breakdown |
| 🗒️ Logs | Run history |

## Signal Engine

Composite score (0–100) weighted across 8 factors:

| Factor | Weight |
|---|---|
| Price Trend | 20% |
| Delivery % | 20% |
| OI Buildup | 20% |
| Volume | 10% |
| FII Activity | 10% |
| Sector Strength | 10% |
| Momentum | 5% |
| PCR | 5% |

| Score | Signal | Recommendation |
|---|---|---|
| ≥80 | 🟢 Strong Bullish | ★★★★★ Strong Buy |
| ≥60 | 🟩 Weak Bullish | ★★★★ Buy Watch |
| ≥40 | ⬜ Neutral | ★★★ Neutral |
| ≥20 | 🟥 Weak Bearish | ★★ Avoid |
| <20 | 🔴 Strong Bearish | ★ Strong Avoid |

## Setup

### 1. Fork / clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/NSE-Smart-Dashboard.git
cd NSE-Smart-Dashboard
```

### 2. Enable GitHub Pages

Go to **Settings → Pages → Source → GitHub Actions**

### 3. Enable GitHub Actions

The workflow runs automatically on weekdays at 7:15 PM IST.
You can also trigger it manually: **Actions → NSE Smart Dashboard → Run workflow**

### 4. Run locally

```bash
pip install -r requirements.txt
python main.py
```

## Data Sources

All data from NSE India static archives (no API key needed):

| File | URL Pattern |
|---|---|
| Equity Bhavcopy | `nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date}.csv` |
| MTO Delivery | `nsearchives.nseindia.com/archives/equities/mto/MTO_{date}.DAT` |
| FO Bhavcopy | `nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{date}_F_0000.csv.zip` |
| FII/DII | `www.nseindia.com/api/fiidiiTradeReact` |
| Participant OI | `nsearchives.nseindia.com/content/nsccl/fao_participant_oi_{date}.csv` |

## Project Structure

```
NSE-Smart-Dashboard/
├── config/config.py          # URLs, constants, NIFTY50 list
├── downloader/
│   ├── market_date.py        # Smart date detection
│   └── archive_downloader.py # Download with retry
├── parser/
│   ├── bhavcopy_parser.py    # Equity CSV + MTO DAT
│   ├── oi_parser.py          # FO bhavcopy (UDiFF + old format)
│   └── fii_parser.py         # FII/DII JSON + participant files
├── signals/composite.py      # Signal engine
├── dashboard/
│   ├── excel_dashboard.py    # Excel generator
│   └── html_dashboard.py     # HTML generator
├── storage/sqlite.py         # Historical DB
├── output/                   # Generated files (committed by Actions)
├── history/                  # SQLite DB + logs
├── main.py                   # Orchestrator
└── .github/workflows/        # GitHub Actions
```

## Disclaimer

This dashboard is for informational purposes only. Not investment advice.
