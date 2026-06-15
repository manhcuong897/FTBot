from datetime import date
from core.account_state import AccountState


class RiskGuard:
    def __init__(self, config: dict, account: AccountState):
        self.sl_max_ticks = config['risk']['sl_max_ticks']
        self.account = account

    def can_trade(self, trading_date: date) -> bool:
        return not self.account.is_daily_cap_reached(trading_date)

    def validate_sl(self, sl_distance_ticks: float) -> bool:
        return sl_distance_ticks <= self.sl_max_ticks
