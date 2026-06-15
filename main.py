import argparse
from pathlib import Path
import yaml

from backtest.data_loader import load_ohlcv, filter_session
from backtest.engine import BacktestEngine
from backtest.report import print_report, save_trade_log
from strategies.ema_engulfing import EMAEngulfingStrategy


def load_config(path: str = 'config/settings.yaml') -> dict:
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


def run_backtest(instrument: str, config: dict, data_dir: Path,
                 start: str | None, end: str | None, save_log: bool) -> list:
    data_path = data_dir / f'{instrument}_5min.csv'
    if not data_path.exists():
        print(f"[SKIP] Không tìm thấy file: {data_path}")
        return []

    print(f"\n[{instrument}] Đang load dữ liệu từ {data_path} ...")
    df = load_ohlcv(str(data_path), config['trading']['data_timezone'])
    df = filter_session(df, config['trading']['session_start_vn'], config['trading']['session_end_vn'])

    if start:
        df = df[df['datetime_vn'].dt.date.astype(str) >= start]
    if end:
        df = df[df['datetime_vn'].dt.date.astype(str) <= end]

    df = df.reset_index(drop=True)
    print(f"[{instrument}] {len(df)} nến trong session, chạy backtest ...")

    strategy = EMAEngulfingStrategy(config['strategy'])
    engine = BacktestEngine(config, instrument)
    trades = engine.run(df, strategy)

    print_report(trades, instrument)

    if save_log and trades:
        log_path = f'results_{instrument}.csv'
        save_trade_log(trades, log_path)

    return trades


def main():
    parser = argparse.ArgumentParser(description='FTBot Backtest Engine')
    parser.add_argument('--instrument', choices=['MNQ', 'MGC', 'ALL'], default='ALL',
                        help='Instrument cần backtest')
    parser.add_argument('--data-dir', default='data', help='Thư mục chứa CSV')
    parser.add_argument('--start', default=None, help='Ngày bắt đầu YYYY-MM-DD')
    parser.add_argument('--end', default=None, help='Ngày kết thúc YYYY-MM-DD')
    parser.add_argument('--save-log', action='store_true', help='Lưu trade log ra CSV')
    parser.add_argument('--config', default='config/settings.yaml')
    args = parser.parse_args()

    config = load_config(args.config)
    data_dir = Path(args.data_dir)

    instruments = ['MNQ', 'MGC'] if args.instrument == 'ALL' else [args.instrument]
    all_trades = []

    for inst in instruments:
        trades = run_backtest(inst, config, data_dir, args.start, args.end, args.save_log)
        all_trades.extend(trades)

    if len(instruments) > 1 and all_trades:
        print_report(all_trades, 'MNQ + MGC (Combined)')


if __name__ == '__main__':
    main()
