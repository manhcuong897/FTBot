from collections import defaultdict
from datetime import date
from backtest.engine import Trade


def print_report(trades: list[Trade], instrument: str = '') -> None:
    if not trades:
        print("No trades found.")
        return

    total = len(trades)
    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]
    total_pnl = sum(t.pnl_usd for t in trades)
    total_ticks = sum(t.pnl_ticks for t in trades)

    win_rate = len(wins) / total * 100
    avg_win = sum(t.pnl_usd for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t.pnl_usd for t in losses) / len(losses) if losses else 0
    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss = abs(sum(t.pnl_usd for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    by_reason = defaultdict(int)
    for t in trades:
        by_reason[t.exit_reason] += 1

    # Max drawdown (equity curve)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in trades:
        equity += t.pnl_usd
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)

    # Daily P&L
    daily_pnl: dict[date, float] = defaultdict(float)
    for t in trades:
        daily_pnl[t.entry_time.date()] += t.pnl_usd
    worst_day = min(daily_pnl.values()) if daily_pnl else 0
    daily_cap_hits = sum(1 for v in daily_pnl.values() if v <= -500)

    title = f"FTBot Backtest Report -- {instrument}" if instrument else "FTBot Backtest Report"
    sep = "=" * 58
    print(f"\n{sep}")
    print(f"  {title}")
    print(sep)
    print(f"  Total Trades     : {total}")
    print(f"  Wins             : {len(wins)} ({win_rate:.1f}%)")
    print(f"  Losses           : {len(losses)} ({100 - win_rate:.1f}%)")
    print(sep)
    print(f"  Total P&L (USD)  : ${total_pnl:,.2f}")
    print(f"  Total P&L (Ticks): {total_ticks:,.1f}")
    print(f"  Avg Win          : ${avg_win:,.2f}")
    print(f"  Avg Loss         : ${avg_loss:,.2f}")
    print(f"  Profit Factor    : {profit_factor:.2f}")
    print(sep)
    print(f"  Max Drawdown     : ${max_dd:,.2f}")
    print(f"  Worst Day        : ${worst_day:,.2f}")
    print(f"  Daily Cap Hits   : {daily_cap_hits} days")
    print(sep)
    print(f"  Exit Reasons:")
    for reason, count in sorted(by_reason.items()):
        print(f"    {reason:<10}: {count}")
    print(sep)


def save_trade_log(trades: list[Trade], filepath: str) -> None:
    import csv
    if not trades:
        return
    fields = ['instrument', 'direction', 'entry_time', 'entry_price',
              'exit_time', 'exit_price', 'exit_reason', 'contracts',
              'sl_distance_ticks', 'pnl_ticks', 'pnl_usd']
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for t in trades:
            writer.writerow({k: getattr(t, k) for k in fields})
    print(f"Trade log saved: {filepath}")
