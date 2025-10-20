#!/usr/bin/env python3
"""
Parses data/hub.log produced by sensorhub and creates visualizations and a CSV summary.

Usage:
    python3 tools/parse_logs.py data/hub.log --outdir outputs --window 5

Outputs:
    summary.csv
    summary_table.png
    temp_timeseries.png, hum_timeseries.png, press_timeseries.png
    temp_hist.png, hum_hist.png, press_hist.png
    alerts_timeline.png
"""
from pathlib import Path
import argparse
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib as mpl
import sys
import numpy as np

mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 12,
    "axes.titlesize": 16,
    "axes.labelsize": 13,
    "legend.fontsize": 11,
    "figure.dpi": 300,
    "figure.facecolor": "white",
    "axes.grid": True,
    "grid.color": "#e6e6e6",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "axes.edgecolor": "#333333",
    "xtick.color": "#333333",
    "ytick.color": "#333333",
})

PALETTE = {
    "TEMP": "#1f77b4",   # blue
    "HUM":  "#ff7f0e",   # orange
    "PRESS":"#2ca02c",   # green
    "ALERT":"#d62728"    # red
}

# Log parsing
def parse_log(path):
    samples = []
    alerts = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split('|')
            if parts[0] == 'SAMPLE' and len(parts) >= 4:
                try:
                    typ = parts[1]
                    val = float(parts[2])
                    ts_ms = int(float(parts[3]))
                    samples.append({'type': typ, 'value': val, 'ts_ms': ts_ms})
                except Exception:
                    continue
            elif parts[0] == 'ALERT' and len(parts) >= 5:
                try:
                    typ = parts[1]
                    val = float(parts[2])
                    ts_ms = int(float(parts[3]))
                    info = parts[4] if len(parts) > 4 else ''
                    alerts.append({'type': typ, 'value': val, 'ts_ms': ts_ms, 'info': info})
                except Exception:
                    continue
    df_samples = pd.DataFrame(samples)
    df_alerts = pd.DataFrame(alerts)
    return df_samples, df_alerts

# Helper functions
def ensure_outdir(p):
    p = Path(p)
    p.mkdir(parents=True, exist_ok=True)
    return p

def to_datetime_series(df, col='ts_ms'):
    return pd.to_datetime(df[col], unit='ms')

# Summary CSV
def summary_csv(df_samples, df_alerts, outcsv):
    sensors = sorted(df_samples['type'].unique().tolist())
    rows = []
    for s in sensors:
        d = df_samples[df_samples['type'] == s]['value']
        row = {
            'sensor': s,
            'count': int(d.count()),
            'min': float(d.min()) if not d.empty else None,
            'max': float(d.max()) if not d.empty else None,
            'mean': float(d.mean()) if not d.empty else None,
            'std': float(d.std()) if not d.empty else None,
            'alert_count': int(df_alerts[df_alerts['type'] == s].shape[0])
        }
        rows.append(row)
    df_summary = pd.DataFrame(rows)
    df_summary.to_csv(outcsv, index=False)
    return df_summary

# Render a DataFrame as an image
def render_table_image(df, outpath, title="Summary"):
    fig, ax = plt.subplots(figsize=(8, 0.6 + 0.4*len(df)))
    ax.axis('off')
    ax.set_title(title, fontsize=16, pad=10)
    # round numeric columns for readability
    df_display = df.copy()
    for c in df_display.columns:
        if pd.api.types.is_float_dtype(df_display[c]) or pd.api.types.is_integer_dtype(df_display[c]):
            df_display[c] = df_display[c].apply(lambda x: f"{x:.3f}" if isinstance(x, float) else x)
    table = ax.table(cellText=df_display.values, colLabels=df_display.columns, cellLoc='center', loc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.2)
    plt.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return outpath

# Timeseries plot (raw values + moving average)
def plot_timeseries(df, sensor, window, outpath):
    d = df[df['type'] == sensor].copy()
    if d.empty:
        print(f"[warn] no samples for {sensor}, skipping timeseries")
        return None
    d = d.sort_values('ts_ms').reset_index(drop=True)
    d['ts'] = to_datetime_series(d)
    # moving average (sample count window)
    d['ma'] = d['value'].rolling(window=window, min_periods=1).mean()

    fig, ax = plt.subplots(figsize=(10, 3.5))
    color = PALETTE.get(sensor, None)

    # plot raw line (thin) and moving average (thicker)
    ax.plot(d['ts'], d['value'], linewidth=1.0, linestyle='-', label='raw', alpha=0.9, color=color)
    ax.plot(d['ts'], d['ma'], linewidth=2.4, linestyle='-', label=f'moving avg ({window})', color=color)

    # add markers sparsely to avoid clutter (approx 30 markers max)
    N = len(d)
    max_markers = 30
    if N > 0:
        step = max(1, int(np.ceil(N / max_markers)))
        ax.plot(d['ts'][::step], d['value'].iloc[::step], linestyle='None', marker='o', markersize=4, alpha=0.9, color=color)

    # stats box in top right corner
    mean = d['value'].mean()
    std = d['value'].std()
    stats_txt = f"count: {len(d)}\nmean: {mean:.2f}\nstd: {std:.2f}"
    ax.text(0.99, 0.95, stats_txt, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#cccccc', alpha=0.9))

    ax.set_xlabel('Time')
    ax.set_ylabel(f'{sensor} value')
    ax.set_title(f'{sensor} — samples and moving average', pad=8)
    ax.legend(loc='upper left')
    ax.grid(True, which='major', axis='both', alpha=0.6)
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return outpath

# Histogram
def plot_histogram(df, sensor, outpath, bins=30):
    vals = df[df['type'] == sensor]['value'].dropna()
    if vals.empty:
        print(f"[warn] no samples for {sensor}, skipping histogram")
        return None
    fig, ax = plt.subplots(figsize=(6,4))
    color = PALETTE.get(sensor, None)
    ax.hist(vals, bins=bins, alpha=0.85, edgecolor='black', linewidth=0.6, color=color)
    ax.set_xlabel(f'{sensor} value')
    ax.set_ylabel('Frequency')
    ax.set_title(f'{sensor} distribution')
    ax.grid(False)
    plt.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return outpath

# Alerts timeline (one point per alert, along with vertical markers and counts)
def plot_alerts_timeline(df_alerts, outpath):
    if df_alerts.empty:
        print("[warn] no ALERT lines found, skipping alerts_timeline")
        return None
    df_alerts = df_alerts.sort_values('ts_ms').reset_index(drop=True)
    df_alerts['ts'] = to_datetime_series(df_alerts)
    types = sorted(df_alerts['type'].unique().tolist())
    type_to_y = {t: i for i, t in enumerate(types)}
    ys = df_alerts['type'].map(type_to_y)

    fig, ax = plt.subplots(figsize=(10, 2.8 + 0.4*len(types)))
    # vertical lines for each alert
    for _, row in df_alerts.iterrows():
        ax.axvline(x=row['ts'], ymin=0.05, ymax=0.95, color='#f0f0f0', linewidth=0.6, zorder=0)
    # scatter points
    for t in types:
        sel = df_alerts[df_alerts['type'] == t]
        ax.scatter(sel['ts'], [type_to_y[t]]*len(sel), s=60, label=f"{t} ({len(sel)})", color=PALETTE.get(t, None), edgecolor='black', linewidth=0.4, zorder=2)
    ax.set_yticks(list(type_to_y.values()))
    ax.set_yticklabels(list(type_to_y.keys()))
    ax.set_xlabel('Time')
    ax.set_title('Alerts timeline (one point per ALERT)')
    ax.legend(loc='upper right')
    plt.tight_layout()
    fig.savefig(outpath, dpi=300, bbox_inches='tight')
    plt.close(fig)
    return outpath

def main():
    parser = argparse.ArgumentParser(description="Parse data/hub.log and create PPT-ready charts + summary.")
    parser.add_argument('logfile', help='Path to data/hub.log')
    parser.add_argument('--outdir', default='outputs', help='Directory to write outputs (default: outputs)')
    parser.add_argument('--window', type=int, default=5, help='moving-average window (samples)')
    parser.add_argument('--bins', type=int, default=30, help='histogram bin count')
    args = parser.parse_args()

    p_log = Path(args.logfile)
    if not p_log.exists():
        print(f"[error] logfile not found: {p_log}", file=sys.stderr)
        sys.exit(2)

    outdir = ensure_outdir(args.outdir)
    df_samples, df_alerts = parse_log(p_log)

    if df_samples.empty:
        print("[error] no SAMPLE lines parsed from logfile", file=sys.stderr)
        sys.exit(3)

    # Save CSV summary and table image
    csv_path = outdir / 'summary.csv'
    df_summary = summary_csv(df_samples, df_alerts, csv_path)
    print(f"Saved summary CSV: {csv_path}")

    table_img = outdir / 'summary_table.png'
    render_table_image(df_summary, table_img, title="Sensor Summary")
    print(f"Saved summary table image: {table_img}")

    # Charts for each sensor
    sensors = sorted(df_samples['type'].unique().tolist())
    for s in sensors:
        ts_path = outdir / f"{s.lower()}_timeseries.png"
        h_path  = outdir / f"{s.lower()}_hist.png"
        p1 = plot_timeseries(df_samples, s, args.window, ts_path)
        p2 = plot_histogram(df_samples, s, h_path, bins=args.bins)
        if p1: print(f"Saved timeseries: {p1}")
        if p2: print(f"Saved histogram: {p2}")

    # Alerts timeline
    alerts_path = outdir / "alerts_timeline.png"
    p_alerts = plot_alerts_timeline(df_alerts, alerts_path)
    if p_alerts:
        print(f"Saved alerts timeline: {p_alerts}")

    print(f"Files written to: {outdir.resolve()}")

if __name__ == '__main__':
    main()