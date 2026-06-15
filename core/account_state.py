from dataclasses import dataclass, field
from datetime import date


@dataclass
class DailyState:
    trading_date: date
    realized_pnl_usd: float = 0.0
    trade_count: int = 0
    win_count: int = 0
    loss_count: int = 0

    def record_trade(self, pnl_usd: float) -> None:
        self.realized_pnl_usd += pnl_usd
        self.trade_count += 1
        if pnl_usd > 0:
            self.win_count += 1
        else:
            self.loss_count += 1


class AccountState:
    def __init__(self, daily_loss_cap_usd: float):
        self.daily_loss_cap_usd = daily_loss_cap_usd
        self._daily: dict[date, DailyState] = {}

    def _get_day(self, trading_date: date) -> DailyState:
        if trading_date not in self._daily:
            self._daily[trading_date] = DailyState(trading_date)
        return self._daily[trading_date]

    def record_trade(self, trading_date: date, pnl_usd: float) -> None:
        self._get_day(trading_date).record_trade(pnl_usd)

    def daily_pnl(self, trading_date: date) -> float:
        return self._get_day(trading_date).realized_pnl_usd

    def is_daily_cap_reached(self, trading_date: date) -> bool:
        return self.daily_pnl(trading_date) <= -self.daily_loss_cap_usd

    def get_day(self, trading_date: date) -> DailyState:
        return self._get_day(trading_date)

    @property
    def all_days(self) -> list[DailyState]:
        return list(self._daily.values())
