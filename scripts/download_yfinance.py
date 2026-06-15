"""
Download 5-min OHLCV data via yfinance (no API key required).

Price data is identical to MNQ/MGC - only contract multiplier differs
(already handled in config/settings.yaml via tick_value).

Symbol mapping:
  MNQ -> MNQ=F (Micro E-mini Nasdaq, ~60 days of 5-min)
  MGC -> MGC=F (Micro Gold, ~60 days of 5-min)
  Fallback: NQ=F / GC=F (same price, different contract size)

Usage:
    python scripts/download_yfinance.py
    python scripts/download_yfinance.py --instrument MNQ
    python scripts/download_yfinance.py --instrument ALL --days 60
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

sys.path.insert(0, str(Path(__file__).parent.parent))

DATA_DIR = Path(__file__).parent.parent / "data"

SYMBOL_MAP = {
    "MNQ": ["MNQ=F", "NQ=F"],
    "MGC": ["MGC=F", "GC=F"],
}


def parse_args():
    parser = argparse.ArgumentParser(description="Download 5-min futures data via yfinance")
    parser.add_argument("--instrument", choices=["MNQ", "MGC", "ALL"], default="ALL")
    parser.add_argument("--days", type=int, default=59,
                        help="Number of days to download (max 59 for 5-min data)")
    return parser.parse_args()


def download_instrument(instrument: str, days: int) -> int:
    candidates = SYMBOL_MAP[instrument]
    df_raw = None
    used_symbol = None

    for symbol in candidates:
        print(f"[{instrument}] Trying symbol {symbol} ...")
        try:
            ticker = yf.Ticker(symbol)
            df_raw = ticker.history(period=f"{days}d", interval="5m", auto_adjust=True)
            if df_raw is not None and len(df_raw) > 0:
                used_symbol = symbol
                print(f"[{instrument}] Got {len(df_raw)} bars from {symbol}")
                break
        except Exception as e:
            print(f"[{instrument}] {symbol} failed: {e}")

    if df_raw is None or len(df_raw) == 0:
        print(f"[{instrument}] No data found from any source.")
        return 0

    # Normalize columns
    df_raw.index = pd.to_datetime(df_raw.index)
    if df_raw.index.tz is None:
        df_raw.index = df_raw.index.tz_localize("UTC")
    else:
        df_raw.index = df_raw.index.tz_convert("UTC")

    df = pd.DataFrame({
        "datetime": df_raw.index.strftime("%Y-%m-%d %H:%M:%S+00:00"),
        "open":     df_raw["Open"].round(4),
        "high":     df_raw["High"].round(4),
        "low":      df_raw["Low"].round(4),
        "close":    df_raw["Close"].round(4),
        "volume":   df_raw["Volume"].fillna(0).astype(int),
    })

    # Drop bars with zero OHLC (market closed / bad data)
    df = df[(df["open"] > 0) & (df["close"] > 0)]

    out_path = DATA_DIR / f"{instrument}_5min.csv"
    DATA_DIR.mkdir(exist_ok=True)

    # Merge with existing data
    if out_path.exists():
        existing = pd.read_csv(out_path)
        df = pd.concat([existing, df]).drop_duplicates(subset=["datetime"]).sort_values("datetime")
        df = df.reset_index(drop=True)

    df.to_csv(out_path, index=False)
    first = df["datetime"].iloc[0][:10]
    last  = df["datetime"].iloc[-1][:10]
    print(f"[{instrument}] Saved {len(df)} bars ({first} -> {last}) -> {out_path}")
    return len(df)


def main():
    args = parse_args()
    if args.days > 59:
        print("[WARN] yfinance 5-min data limited to 59 days. Setting --days 59.")
        args.days = 59

    instruments = ["MNQ", "MGC"] if args.instrument == "ALL" else [args.instrument]
    total = 0
    for inst in instruments:
        count = download_instrument(inst, args.days)
        total += count

    print(f"\n[Done] Total {total} bars saved in {DATA_DIR}/")
    print("Run backtest: python main.py --instrument ALL")


if __name__ == "__main__":
    main()
