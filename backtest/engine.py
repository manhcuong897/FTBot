from dataclasses import dataclass, field
from datetime import date
import pandas as pd

from core.account_state import AccountState
from core.risk_guard import RiskGuard
from strategies.base_strategy import BaseStrategy


@dataclass
class Position:
    instrument: str
    direction: str          # 'LONG' | 'SHORT'
    entry_time: pd.Timestamp
    entry_price: float
    sl_price: float
    tp_price: float
    contracts: int
    tick_size: float
    tick_value: float
    breakeven_triggered: bool = False


@dataclass
class Trade:
    instrument: str
    direction: str
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    exit_reason: str        # 'TP' | 'SL' | 'BE_SL' | 'EOD'
    contracts: int
    tick_size: float
    tick_value: float
    sl_distance_ticks: float
    pnl_ticks: float = field(init=False)
    pnl_usd: float = field(init=False)

    def __post_init__(self):
        if self.direction == 'LONG':
            self.pnl_ticks = (self.exit_price - self.entry_price) / self.tick_size
        else:
            self.pnl_ticks = (self.entry_price - self.exit_price) / self.tick_size
        self.pnl_usd = self.pnl_ticks * self.tick_value * self.contracts


class BacktestEngine:
    def __init__(self, config: dict, instrument: str):
        self.instrument = instrument
        self.contracts = config['trading']['contracts']
        self.rr_ratio = config['risk']['rr_ratio']
        self.sl_max_ticks = config['risk']['sl_max_ticks']
        self.be_trigger = config['risk']['breakeven_trigger_ticks']
        self.be_lock = config['risk']['breakeven_lock_ticks']
        self.close_on_session_end = config['trading']['close_on_session_end']

        inst_cfg = config['instruments'][instrument]
        self.tick_size = inst_cfg['tick_size']
        self.tick_value = inst_cfg['tick_value']

        self.account = AccountState(config['risk']['daily_loss_cap_usd'])
        self.risk_guard = RiskGuard(config, self.account)

    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> list[Trade]:
        df = strategy.calculate_indicators(df)
        trades: list[Trade] = []
        position: Position | None = None
        current_date: date | None = None

        for idx in range(len(df)):
            bar = df.iloc[idx]
            bar_date = bar['datetime_vn'].date()

            # Reset daily tracking khi sang ngày mới
            if bar_date != current_date:
                current_date = bar_date
                # Đóng lệnh cuối ngày nếu còn mở từ ngày hôm qua
                if position is not None:
                    trade = self._close_position(position, bar['open'], bar['datetime_vn'], 'EOD')
                    trades.append(trade)
                    self.account.record_trade(bar_date, trade.pnl_usd)
                    position = None

            # Cập nhật position đang mở
            if position is not None:
                exit_reason, exit_price = self._check_exit(position, bar)
                if exit_reason:
                    reason_label = 'BE_SL' if (exit_reason == 'SL' and position.breakeven_triggered) else exit_reason
                    trade = self._close_position(position, exit_price, bar['datetime_vn'], reason_label)
                    trades.append(trade)
                    self.account.record_trade(bar_date, trade.pnl_usd)
                    position = None

            # Đóng cuối session nếu là nến cuối của ngày
            if position is not None and self.close_on_session_end:
                next_idx = idx + 1
                if next_idx >= len(df) or df.iloc[next_idx]['datetime_vn'].date() != bar_date:
                    trade = self._close_position(position, bar['close'], bar['datetime_vn'], 'EOD')
                    trades.append(trade)
                    self.account.record_trade(bar_date, trade.pnl_usd)
                    position = None

            # Không mở lệnh mới nếu đã có position hoặc đạt daily cap
            if position is not None:
                continue
            if not self.risk_guard.can_trade(bar_date):
                continue

            signal = strategy.generate_signal(df, idx, self.tick_size)
            if signal is None:
                continue

            entry_price = bar['close']
            sl_price = signal['sl_price']
            sl_distance_ticks = abs(entry_price - sl_price) / self.tick_size

            if not self.risk_guard.validate_sl(sl_distance_ticks):
                continue

            tp_distance = sl_distance_ticks * self.rr_ratio * self.tick_size
            if signal['direction'] == 'LONG':
                tp_price = entry_price + tp_distance
            else:
                tp_price = entry_price - tp_distance

            position = Position(
                instrument=self.instrument,
                direction=signal['direction'],
                entry_time=bar['datetime_vn'],
                entry_price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
                contracts=self.contracts,
                tick_size=self.tick_size,
                tick_value=self.tick_value,
            )

        return trades

    def _check_exit(self, pos: Position, bar: pd.Series) -> tuple[str | None, float]:
        tick_size = pos.tick_size

        if pos.direction == 'LONG':
            # Kiểm tra breakeven trigger (dùng high của nến)
            if not pos.breakeven_triggered:
                profit_ticks = (bar['high'] - pos.entry_price) / tick_size
                if profit_ticks >= self.be_trigger:
                    new_sl = pos.entry_price + self.be_lock * tick_size
                    if new_sl > pos.sl_price:
                        pos.sl_price = new_sl
                        pos.breakeven_triggered = True

            if bar['low'] <= pos.sl_price:
                return 'SL', pos.sl_price
            if bar['high'] >= pos.tp_price:
                return 'TP', pos.tp_price

        else:  # SHORT
            if not pos.breakeven_triggered:
                profit_ticks = (pos.entry_price - bar['low']) / tick_size
                if profit_ticks >= self.be_trigger:
                    new_sl = pos.entry_price - self.be_lock * tick_size
                    if new_sl < pos.sl_price:
                        pos.sl_price = new_sl
                        pos.breakeven_triggered = True

            if bar['high'] >= pos.sl_price:
                return 'SL', pos.sl_price
            if bar['low'] <= pos.tp_price:
                return 'TP', pos.tp_price

        return None, 0.0

    def _close_position(self, pos: Position, exit_price: float,
                        exit_time: pd.Timestamp, reason: str) -> Trade:
        sl_distance = abs(pos.entry_price - pos.sl_price) / pos.tick_size
        return Trade(
            instrument=pos.instrument,
            direction=pos.direction,
            entry_time=pos.entry_time,
            entry_price=pos.entry_price,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=reason,
            contracts=pos.contracts,
            tick_size=pos.tick_size,
            tick_value=pos.tick_value,
            sl_distance_ticks=sl_distance,
        )
