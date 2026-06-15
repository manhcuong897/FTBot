"""
Script tải dữ liệu lịch sử 5 phút từ Tradovate và lưu vào data/

Cách dùng:
    python scripts/download_historical.py --instrument MNQ --months 6
    python scripts/download_historical.py --instrument MGC --start 2023-01-01 --end 2023-12-31
    python scripts/download_historical.py --instrument ALL --months 12

Yêu cầu: file .env chứa TRADOVATE_USERNAME và TRADOVATE_PASSWORD
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Thêm root vào path để import brokers
sys.path.insert(0, str(Path(__file__).parent.parent))
from brokers.tradovate import TradovateClient

load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"
INSTRUMENTS = ["MNQ", "MGC"]
BARS_PER_REQUEST = 5000     # Tradovate cho phép tối đa ~5000 bars/request
REQUEST_DELAY_SEC = 1.0     # Tránh rate limit


def parse_args():
    parser = argparse.ArgumentParser(description="Download lịch sử 5 phút từ Tradovate")
    parser.add_argument("--instrument", choices=["MNQ", "MGC", "ALL"], default="ALL")
    parser.add_argument("--months", type=int, default=6,
                        help="Số tháng dữ liệu cần lấy (tính từ hôm nay về trước)")
    parser.add_argument("--start", default=None, help="Ngày bắt đầu YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="Ngày kết thúc YYYY-MM-DD (mặc định: hôm nay)")
    parser.add_argument("--demo", action="store_true", default=True,
                        help="Dùng Tradovate demo account (mặc định)")
    parser.add_argument("--live", action="store_true",
                        help="Dùng Tradovate live account")
    return parser.parse_args()


def get_credentials() -> tuple[str, str]:
    username = os.getenv("TRADOVATE_USERNAME")
    password = os.getenv("TRADOVATE_PASSWORD")
    if not username or not password:
        print("[ERROR] Thiếu TRADOVATE_USERNAME hoặc TRADOVATE_PASSWORD trong file .env")
        print("  Tạo file .env từ .env.example và điền thông tin đăng nhập.")
        sys.exit(1)
    return username, password


def date_range_chunks(start: datetime, end: datetime) -> list[tuple[str, str]]:
    """
    Chia khoảng thời gian thành các chunk nhỏ (~30 ngày mỗi chunk)
    vì Tradovate giới hạn số bar mỗi request.
    5-min bars/ngày trading: ~84 bars (7 giờ RTH) → 30 ngày ≈ 2520 bars < 5000
    """
    chunks = []
    chunk_days = 30
    cursor = start
    while cursor < end:
        chunk_end = min(cursor + timedelta(days=chunk_days), end)
        chunks.append((
            cursor.strftime("%Y-%m-%dT%H:%M:%SZ"),
            chunk_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))
        cursor = chunk_end
    return chunks


def download_instrument(client: TradovateClient, instrument: str,
                        start: datetime, end: datetime) -> int:
    out_path = DATA_DIR / f"{instrument}_5min.csv"
    existing_rows: dict[str, dict] = {}

    # Đọc file cũ nếu có (để merge, tránh duplicate)
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_rows[row["datetime"]] = row
        print(f"[{instrument}] File cũ: {len(existing_rows)} nến đã có")

    chunks = date_range_chunks(start, end)
    new_bars: list[dict] = []

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        print(f"[{instrument}] Chunk {i+1}/{len(chunks)}: {chunk_start[:10]} → {chunk_end[:10]}")
        try:
            raw = client.get_chart_range(instrument, chunk_start, chunk_end, element_size=5)
            bars = client.parse_bars(raw)
            print(f"  → {len(bars)} nến nhận được")
            new_bars.extend(bars)
        except Exception as e:
            print(f"  [WARN] Lỗi chunk {chunk_start}: {e}")
        time.sleep(REQUEST_DELAY_SEC)

    if not new_bars:
        print(f"[{instrument}] Không nhận được dữ liệu mới.")
        return 0

    # Merge với dữ liệu cũ
    for bar in new_bars:
        existing_rows[bar["datetime"]] = bar

    # Sort theo thời gian và lưu
    sorted_bars = sorted(existing_rows.values(), key=lambda x: x["datetime"])
    DATA_DIR.mkdir(exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["datetime", "open", "high", "low", "close", "volume"])
        writer.writeheader()
        writer.writerows(sorted_bars)

    print(f"[{instrument}] Đã lưu {len(sorted_bars)} nến → {out_path}")
    return len(new_bars)


def main():
    args = parse_args()
    use_demo = not args.live

    # Tính khoảng thời gian
    end_dt = datetime.now(timezone.utc)
    if args.end:
        end_dt = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)

    if args.start:
        start_dt = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    else:
        start_dt = end_dt - timedelta(days=args.months * 30)

    print(f"[Config] {'DEMO' if use_demo else 'LIVE'} | {start_dt.date()} → {end_dt.date()}")

    # Authenticate
    username, password = get_credentials()
    client = TradovateClient(demo=use_demo)
    print(f"[Auth] Đăng nhập với {username} ...")
    client.authenticate(username, password)

    if not client.verify_connection():
        print("[ERROR] Xác minh kết nối thất bại sau authenticate.")
        sys.exit(1)

    # Download
    instruments = INSTRUMENTS if args.instrument == "ALL" else [args.instrument]
    total_new = 0
    for inst in instruments:
        count = download_instrument(client, inst, start_dt, end_dt)
        total_new += count

    print(f"\n[Done] Tổng cộng {total_new} nến mới đã tải.")
    print(f"  File lưu tại: {DATA_DIR}/")
    print(f"  Chạy backtest: python main.py --instrument ALL")


if __name__ == "__main__":
    main()
