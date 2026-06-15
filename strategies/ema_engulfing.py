import pandas as pd
from strategies.base_strategy import BaseStrategy


class EMAEngulfingStrategy(BaseStrategy):
    def __init__(self, config: dict):
        self.ema_trend_period = config['ema_trend_period']    # 200
        self.ema_value_period = config['ema_value_period']    # 21
        self.proximity_ticks = config['ema_proximity_ticks']  # 10
        self.retest_lookback = config['retest_lookback']      # 5

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df['ema200'] = df['close'].ewm(span=self.ema_trend_period, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=self.ema_value_period, adjust=False).mean()
        return df

    def _is_bullish_engulfing(self, df: pd.DataFrame, idx: int) -> bool:
        b0 = df.iloc[idx]
        b1 = df.iloc[idx - 1]
        return (
            b1['close'] < b1['open']       # b1 giảm
            and b0['close'] > b0['open']   # b0 tăng
            and b0['close'] > b1['open']   # thân b0 bao trọn thân b1
            and b0['open'] < b1['close']
        )

    def _is_bearish_engulfing(self, df: pd.DataFrame, idx: int) -> bool:
        b0 = df.iloc[idx]
        b1 = df.iloc[idx - 1]
        return (
            b1['close'] > b1['open']       # b1 tăng
            and b0['close'] < b0['open']   # b0 giảm
            and b0['close'] < b1['open']   # thân b0 bao trọn thân b1
            and b0['open'] > b1['close']
        )

    def _has_ema21_retest(self, df: pd.DataFrame, idx: int, tick_size: float, direction: str) -> bool:
        """
        Kiểm tra trong retest_lookback nến trước idx có nến nào
        chạm/tiệm cận EMA 21 không (theo hướng giao dịch).
        """
        start = max(1, idx - self.retest_lookback)
        for i in range(start, idx):
            bar = df.iloc[i]
            ema21 = bar['ema21']
            proximity = self.proximity_ticks * tick_size
            if direction == 'LONG':
                # Low của nến tiệm cận EMA 21
                if abs(bar['low'] - ema21) <= proximity:
                    return True
            else:
                # High của nến tiệm cận EMA 21
                if abs(bar['high'] - ema21) <= proximity:
                    return True
        return False

    def generate_signal(self, df: pd.DataFrame, idx: int, tick_size: float) -> dict | None:
        min_bars = self.ema_trend_period + self.retest_lookback + 1
        if idx < min_bars:
            return None

        b0 = df.iloc[idx]
        b1 = df.iloc[idx - 1]
        ema200 = b0['ema200']

        if (self._is_bullish_engulfing(df, idx)
                and b0['close'] > ema200
                and self._has_ema21_retest(df, idx, tick_size, 'LONG')):
            sl_price = min(b0['low'], b1['low']) - 2 * tick_size
            return {'direction': 'LONG', 'sl_price': sl_price}

        if (self._is_bearish_engulfing(df, idx)
                and b0['close'] < ema200
                and self._has_ema21_retest(df, idx, tick_size, 'SHORT')):
            sl_price = max(b0['high'], b1['high']) + 2 * tick_size
            return {'direction': 'SHORT', 'sl_price': sl_price}

        return None
