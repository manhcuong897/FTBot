from abc import ABC, abstractmethod
import pandas as pd


class BaseStrategy(ABC):
    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Tính toán các chỉ báo kỹ thuật, trả về df với cột mới."""

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, idx: int, tick_size: float) -> dict | None:
        """
        Trả về signal dict hoặc None.
        Signal dict: {'direction': 'LONG'|'SHORT', 'sl_price': float}
        """
