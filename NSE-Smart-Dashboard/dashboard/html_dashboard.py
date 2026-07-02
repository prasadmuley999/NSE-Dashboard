"""
HTML Dashboard Generator
Produces index.html — mobile-friendly, publishable via GitHub Pages.
"""

import json
import logging
from datetime import date, datetime
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

SIGNAL_CSS = {
    "🟢 Strong Bullish": "sig-strong-bull",
    "🟩 Weak Bullish":   "sig-weak-bull",
    "⬜ Neutral":         "sig-neutral",
    "🟥 Weak Bearish":   "sig-weak-bear",
    "🔴 Strong Bearish": "sig-strong-bear",
}


def _badge(label: str) -> str:
    css = SIGNAL_CSS.get(label, "sig-neutral")
    return f'<span class="signal-badge {css}">{label}</span>'


def _chg_span(val: float, fmt=".2f") -> str:
    cls = "pos" if val >= 0 else "neg"
    prefix = "+" if val >= 0 else ""
    return f'<span class="{cls}">{prefix}{val:{fmt}}</span>'


def generate_html(
    signals_df:  pd.DataFrame,
    fii_series:  pd.Series,
    sector_df:   pd.DataFrame,
    hist_df:     pd.DataFrame,
    fii_hist:    pd.DataFrame,
    market_date: date,
    output_path: str,
):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    run_time   = datetime.now().strftime("%d %b %Y %I:%M %p IST")
    date_str   = market_date.strftime("%d %b %Y")
    fii_net    = float(fii_series.get("fii_net",  0)) if not fii_series.empty else 0
    dii_net    = float(fii_series.get("dii_net",  0)) if not fii_series.empty else 0
    fii_buy    = float(fii_series.get("fii_buy",  0)) if not fii_series.empty else 0
    fii_sell   = float(fii_series.get("fii_sell", 0)) if not fii_series.empty else 0
    dii_buy    = float(fii_series.get("dii_buy",  0)) if not fii_series.empty else 0
    dii_sell   = float(fii_series.get("dii_sell", 0)) if not fii_series.empty else 0

    counts     = signals_df["signal_label"].value_counts()
    avg_del    = signals_df["deliv_pct"].mean()
    bull_count = counts.get("🟢 Strong Bullish", 0) + counts.get("🟩 Weak Bullish", 0)
    bear_count = counts.get("🔴 Strong Bearish", 0) + counts.get("🟥 Weak Bearish", 0)

    bias_label = "Bullish" if bull_count > bear_count else ("Bearish" if bear_count > bull_count else "Neutral")
    bias_cls   = "pos" if bias_label == "Bullish" else ("neg" if bias_label == "Bearish" else "")

    # Opportunities (top 5 bullish)
    opps  = signals_df[signals_df["stars"] >= 4].head(5)
    avoid = signals_df[signals_df["stars"] <= 2].tail(5)

    # ── Sector rows ───────────────────────────────────────────────────────────
    sector_rows = ""
    for _, row in sector_df.iterrows():
        sig_css = SIGNAL_CSS.get(row.get("sector_signal", ""), "sig-neutral")
        sector_rows += f"""
        <tr>
          <td>{row.get('sector','')}</td>
          <td>{int(row.get('stocks',0))}</td>
          <td>{row.get('avg_del_pct',0):.1f}%</td>
          <td>{_chg_span(row.get('avg_chg_pct',0))}%</td>
          <td>{int(row.get('bullish',0))}</td>
          <td>{int(row.get('bearish',0))}</td>
          <td><span class="signal-badge {sig_css}">{row.get('sector_signal','')}</span></td>
        </tr>"""

    # ── Opportunities rows ────────────────────────────────────────────────────
    opp_rows = ""
    for _, row in opps.iterrows():
        opp_rows += f"""
        <tr>
          <td><strong>{row['symbol']}</strong></td>
          <td>{row['sector']}</td>
          <td>{row['close']:.2f}</td>
          <td>{_chg_span(row['chg_pct'])}%</td>
          <td>{row['deliv_pct']:.1f}%</td>
          <td>{_chg_span(row['oi_chg_pct'])}%</td>
          <td>{_badge(row['signal_label'])}</td>
          <td><strong>{row['score']:.0f}</strong></td>
        </tr>"""

    avoid_rows = ""
    for _, row in avoid.iterrows():
        avoid_rows += f"""
        <tr>
          <td><strong>{row['symbol']}</strong></td>
          <td>{row['sector']}</td>
          <td>{row['close']:.2f}</td>
          <td>{_chg_span(row['chg_pct'])}%</td>
          <td>{row['deliv_pct']:.1f}%</td>
          <td>{_chg_span(row['oi_chg_pct'])}%</td>
          <td>{_badge(row['signal_label'])}</td>
          <td><strong>{row['score']:.0f}</strong></td>
        </tr>"""

    # ── All stocks table ──────────────────────────────────────────────────────
    all_rows = ""
    for _, row in signals_df.iterrows():
        all_rows += f"""
        <tr>
          <td><strong>{row['symbol']}</strong></td>
          <td>{row['sector']}</td>
          <td>{row['close']:.2f}</td>
          <td>{_chg_span(row['chg_pct'])}%</td>
          <td>{row['deliv_pct']:.1f}%</td>
          <td>{_chg_span(row['oi_chg_pct'])}%</td>
          <td>{row.get('oi_signal','')}</td>
          <td>{_badge(row['signal_label'])}</td>
          <td><strong>{row['score']:.0f}</strong></td>
        </tr>"""

    # ── FII history rows ──────────────────────────────────────────────────────
    fii_hist_rows = ""
    for _, row in fii_hist.head(10).iterrows():
        fn = float(row.get("fii_net", 0))
        dn = float(row.get("dii_net", 0))
        fii_hist_rows += f"""
        <tr>
          <td>{row.get('date','')}</td>
          <td>{_chg_span(fn)}</td>
          <td>{_chg_span(dn)}</td>
          <td>{_chg_span(fn + dn)}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NSE Smart Dashboard · {date_str}</title>
  <style>
    :root {{
      --bg:       #0f0f1a;
      --card:     #1a1a2e;
      --border:   #2a2a4a;
      --accent:   #FFD700;
      --text:     #e0e0e0;
      --sub:      #9e9e9e;
      --green:    #00c851;
      --red:      #ff3d3d;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', sans-serif; font-size: 14px; }}
    a {{ color: var(--accent); }}
    header {{ background: var(--card); border-bottom: 2px solid var(--accent); padding: 14px 20px; }}
    header h1 {{ font-size: 18px; color: var(--accent); }}
    header .meta {{ font-size: 12px; color: var(--sub); margin-top: 4px; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}
    .grid-4 {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; }}
    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px; }}
    @media (max-width: 700px) {{ .grid-4 {{ grid-template-columns: repeat(2,1fr); }} .grid-2 {{ grid-template-columns: 1fr; }} }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }}
    .card-title {{ font-size: 11px; color: var(--sub); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 6px; }}
    .card-value {{ font-size: 22px; font-weight: bold; }}
    .card-sub {{ font-size: 12px; color: var(--sub); margin-top: 4px; }}
    .pos {{ color: var(--green); }}
    .neg {{ color: var(--red); }}
    section {{ margin-bottom: 24px; }}
    section h2 {{ font-size: 15px; color: var(--accent); border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 12px; }}
    .signal-summary {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px; }}
    .sig-pill {{ border-radius: 20px; padding: 6px 16px; font-weight: bold; font-size: 13px; text-align: center; }}
    .sig-strong-bull {{ background: #00c851; color: #fff; }}
    .sig-weak-bull   {{ background: #43a047; color: #fff; }}
    .sig-neutral     {{ background: #757575; color: #fff; }}
    .sig-weak-bear   {{ background: #e53935; color: #fff; }}
    .sig-strong-bear {{ background: #b71c1c; color: #fff; }}
    .signal-badge {{ border-radius: 4px; padding: 2px 8px; font-size: 12px; font-weight: bold; white-space: nowrap; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #0d47a1; color: #fff; padding: 8px 10px; text-align: center; white-space: nowrap; }}
    td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); text-align: center; }}
    tr:hover td {{ background: #1e2a4a; }}
    .bias-tag {{ font-size: 24px; font-weight: bold; margin-top: 6px; }}
    footer {{ text-align: center; color: var(--sub); font-size: 12px; padding: 20px; border-top: 1px solid var(--border); margin-top: 20px; }}
  </style>
</head>
<body>
<header>
  <h1>📊 NSE NIFTY 50 · Smart Decision Dashboard</h1>
  <div class="meta">Market Date: <strong>{date_str}</strong> &nbsp;|&nbsp; Generated: {run_time}</div>
</header>

<div class="container">

  <!-- Signal Summary Pills -->
  <div class="signal-summary" style="margin-top:16px;">
    <div class="sig-pill sig-strong-bull">🟢 Strong Bullish: {counts.get("🟢 Strong Bullish",0)}</div>
    <div class="sig-pill sig-weak-bull">🟩 Weak Bullish: {counts.get("🟩 Weak Bullish",0)}</div>
    <div class="sig-pill sig-neutral">⬜ Neutral: {counts.get("⬜ Neutral",0)}</div>
    <div class="sig-pill sig-weak-bear">🟥 Weak Bearish: {counts.get("🟥 Weak Bearish",0)}</div>
    <div class="sig-pill sig-strong-bear">🔴 Strong Bearish: {counts.get("🔴 Strong Bearish",0)}</div>
  </div>

  <!-- Market Overview Cards -->
  <div class="grid-4">
    <div class="card">
      <div class="card-title">Market Bias</div>
      <div class="bias-tag {bias_cls}">{bias_label}</div>
      <div class="card-sub">{bull_count} Bull · {bear_count} Bear</div>
    </div>
    <div class="card">
      <div class="card-title">FII Net (₹ Cr)</div>
      <div class="card-value {'pos' if fii_net>=0 else 'neg'}">{fii_net:+.2f}</div>
      <div class="card-sub">B: {fii_buy:.0f} S: {fii_sell:.0f}</div>
    </div>
    <div class="card">
      <div class="card-title">DII Net (₹ Cr)</div>
      <div class="card-value {'pos' if dii_net>=0 else 'neg'}">{dii_net:+.2f}</div>
      <div class="card-sub">B: {dii_buy:.0f} S: {dii_sell:.0f}</div>
    </div>
    <div class="card">
      <div class="card-title">Avg Delivery %</div>
      <div class="card-value">{avg_del:.1f}%</div>
      <div class="card-sub">NIFTY50 Average</div>
    </div>
  </div>

  <!-- Top Opportunities -->
  <section>
    <h2>🚀 Top Opportunities</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Symbol</th><th>Sector</th><th>Close</th><th>Chg%</th><th>Del%</th><th>OI Chg%</th><th>Signal</th><th>Score</th></tr></thead>
        <tbody>{opp_rows if opp_rows else '<tr><td colspan="8">No strong buy opportunities today</td></tr>'}</tbody>
      </table>
    </div>
  </section>

  <!-- Stocks to Avoid -->
  <section>
    <h2>⚠️ Stocks to Avoid</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Symbol</th><th>Sector</th><th>Close</th><th>Chg%</th><th>Del%</th><th>OI Chg%</th><th>Signal</th><th>Score</th></tr></thead>
        <tbody>{avoid_rows if avoid_rows else '<tr><td colspan="8">No strong avoid signals today</td></tr>'}</tbody>
      </table>
    </div>
  </section>

  <!-- Sector Strength -->
  <section>
    <h2>🏭 Sector-wise Strength</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sector</th><th>Stocks</th><th>Avg Del%</th><th>Avg Chg%</th><th>Bullish</th><th>Bearish</th><th>Signal</th></tr></thead>
        <tbody>{sector_rows}</tbody>
      </table>
    </div>
  </section>

  <!-- FII/DII Trend -->
  <section>
    <h2>💹 FII / DII Recent Trend</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Date</th><th>FII Net</th><th>DII Net</th><th>Combined</th></tr></thead>
        <tbody>{fii_hist_rows if fii_hist_rows else '<tr><td colspan="4">No historical data yet</td></tr>'}</tbody>
      </table>
    </div>
  </section>

  <!-- All Stocks -->
  <section>
    <h2>📋 All NIFTY50 Stocks</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Symbol</th><th>Sector</th><th>Close</th><th>Chg%</th><th>Del%</th><th>OI Chg%</th><th>OI Signal</th><th>Signal</th><th>Score</th></tr></thead>
        <tbody>{all_rows}</tbody>
      </table>
    </div>
  </section>

</div>
<footer>NSE Smart Dashboard · Auto-generated · Data from NSE India Archives · Not investment advice</footer>
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")
    log.info(f"HTML saved: {output_path}")
