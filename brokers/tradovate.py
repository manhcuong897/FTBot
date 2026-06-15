import time
import requests

LIVE_URL = "https://api.tradovate.com/v1"
DEMO_URL = "https://demo-api-d.tradovate.com/v1"

# Timeframe mapping cho Tradovate
TIMEFRAME_MAP = {
    1: "MinuteBar",
    5: "MinuteBar",
    15: "MinuteBar",
    60: "MinuteBar",
}


class TradovateClient:
    def __init__(self, demo: bool = True):
        self.base_url = DEMO_URL if demo else LIVE_URL
        self.access_token: str | None = None
        self.token_expiry: float = 0

    def authenticate(self, username: str, password: str,
                     app_id: str = "Sample App", app_version: str = "1.0",
                     device_id: str = "ftbot-01",
                     cid: int = 0, sec: str = "") -> None:
        url = f"{self.base_url}/auth/accesstokenrequest"
        payload = {
            "name": username,
            "password": password,
            "appId": app_id,
            "appVersion": app_version,
            "deviceId": device_id,
            "cid": cid,
            "sec": sec,
        }
        resp = requests.post(url, json=payload, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if "errorText" in data:
            raise ValueError(f"Auth failed: {data['errorText']}")

        self.access_token = data["accessToken"]
        # token thường hết hạn sau 80 phút — buffer 5 phút
        self.token_expiry = time.time() + 75 * 60
        print(f"[Auth] OK — token valid for 75 minutes")

    def _headers(self) -> dict:
        if not self.access_token:
            raise RuntimeError("Chưa authenticate.")
        if time.time() > self.token_expiry:
            raise RuntimeError("Token đã hết hạn — authenticate lại.")
        return {"Authorization": f"Bearer {self.access_token}"}

    def get_chart(self, symbol: str, element_size: int = 5,
                  num_bars: int = 5000) -> dict:
        """
        Lấy dữ liệu nến lịch sử từ Tradovate.

        symbol      : 'MNQ' | 'MGC' | 'MNQH4' | ...
        element_size: timeframe (phút), ví dụ 5
        num_bars    : số nến muốn lấy (tối đa ~5000 mỗi request)
        """
        url = f"{self.base_url}/md/getChart"
        payload = {
            "symbol": symbol,
            "chartDescription": {
                "underlyingType": "MinuteBar",
                "elementSize": element_size,
                "elementSizeUnit": "UnderlyingUnits",
                "withHistogram": False,
            },
            "timeRange": {
                "asMuchAsElements": num_bars,
            },
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def get_chart_range(self, symbol: str, start_iso: str, end_iso: str,
                        element_size: int = 5) -> dict:
        """
        Lấy dữ liệu theo khoảng thời gian cụ thể.
        start_iso / end_iso: định dạng ISO 8601, ví dụ '2023-01-01T00:00:00Z'
        """
        url = f"{self.base_url}/md/getChart"
        payload = {
            "symbol": symbol,
            "chartDescription": {
                "underlyingType": "MinuteBar",
                "elementSize": element_size,
                "elementSizeUnit": "UnderlyingUnits",
                "withHistogram": False,
            },
            "timeRange": {
                "closestTimestamp": end_iso,
                "asFarAsTimestamp": start_iso,
            },
        }
        resp = requests.post(url, json=payload, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def parse_bars(self, raw: dict) -> list[dict]:
        """
        Parse response từ getChart thành list[dict] chuẩn OHLCV.
        Tradovate có thể trả về dạng 'bars' hoặc 'chart.bars'.
        """
        bars = []

        # Thử các format phổ biến của Tradovate response
        if "bars" in raw:
            source = raw["bars"]
        elif "chart" in raw and "bars" in raw["chart"]:
            source = raw["chart"]["bars"]
        elif isinstance(raw, list):
            source = raw
        else:
            raise ValueError(f"Không nhận ra format response: {list(raw.keys())}")

        for b in source:
            bars.append({
                "datetime": b.get("timestamp", b.get("t", "")),
                "open":     float(b.get("open",  b.get("o", 0))),
                "high":     float(b.get("high",  b.get("h", 0))),
                "low":      float(b.get("low",   b.get("l", 0))),
                "close":    float(b.get("close", b.get("c", 0))),
                "volume":   float(b.get("upVolume", 0) + b.get("downVolume", 0)),
            })

        return bars

    def verify_connection(self) -> bool:
        """Kiểm tra token hợp lệ bằng cách gọi /account/list."""
        try:
            resp = requests.get(f"{self.base_url}/account/list",
                                headers=self._headers(), timeout=10)
            return resp.status_code == 200
        except Exception:
            return False
