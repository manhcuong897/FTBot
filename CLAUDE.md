# FTBot — Funded Trading Bot

Bot giao dịch tự động cho các tài khoản prop firm: Bulenox 50k, TopStep 50k, Lucid Trading 50k.

---

## Tổng quan dự án

| Hạng mục | Chi tiết |
|---|---|
| Instruments | MNQ (Micro Nasdaq), MGC (Micro Gold) |
| Timeframe | 5 phút |
| Broker API | Tradovate (REST + WebSocket) |
| Ngôn ngữ | Python |
| Khung giờ | 06:00–09:00 SA (UTC+7 / Việt Nam) |
| Khối lượng | 5 contracts/lệnh |
| GitHub | https://github.com/manhcuong897/FTBot.git |

---

## Chiến lược giao dịch

### Chỉ báo sử dụng
- **EMA 200** — Xác định xu hướng lớn
- **EMA 21** — Xác định vùng giá trị (value zone / retest zone)

### Mô hình nến Engulfing

**Bullish Engulfing (tín hiệu Long):**
- Nến [1] giảm: `Close[1] < Open[1]`
- Nến [0] tăng: `Close[0] > Open[0]`
- Thân [0] bao trọn thân [1]: `Close[0] > Open[1]` VÀ `Open[0] < Close[1]`

**Bearish Engulfing (tín hiệu Short):**
- Nến [1] tăng: `Close[1] > Open[1]`
- Nến [0] giảm: `Close[0] < Open[0]`
- Thân [0] bao trọn thân [1]: `Close[0] < Open[1]` VÀ `Open[0] > Close[1]`

### Điều kiện vào lệnh (Confluence Entry)

**LONG — vào khi Bullish Engulfing đóng cửa, đồng thời:**
1. `Close[0] > EMA200` — xu hướng tăng
2. Trong 3–5 nến trước [0], có ít nhất 1 nến có Low chạm/tiệm cận EMA 21
3. Nến Engulfing xuất hiện tại vùng EMA 21 đó

**SHORT — vào khi Bearish Engulfing đóng cửa, đồng thời:**
1. `Close[0] < EMA200` — xu hướng giảm
2. Trong 3–5 nến trước [0], có ít nhất 1 nến có High chạm/tiệm cận EMA 21
3. Nến Engulfing xuất hiện tại vùng EMA 21 đó

---

## Quản trị rủi ro

### SL / TP

| | Long | Short |
|---|---|---|
| **SL** | Low của cụm 2 nến Engulfing − 2 ticks | High của cụm 2 nến Engulfing + 2 ticks |
| **SL hard cap** | Tối đa 50 ticks — bỏ qua trade nếu structure SL > 50 ticks | |
| **TP** | Entry + (SL distance × 3) | Entry − (SL distance × 3) |
| **R:R** | 1:3 cố định | |

### Breakeven / Trailing SL
- Khi lợi nhuận đạt **X ticks** → dời SL về Entry + **Y ticks** (Long) / Entry − Y ticks (Short)
- SL mới giữ cố định, không dời ngược lại
- **Tham số mặc định hiện tại:** X = 30 ticks, Y = 5 ticks
- **Cần điều chỉnh:** X = 50 ticks, Y = 15 ticks (backtest cho thấy BE quá sớm gây avg win chỉ $25)

### Daily Loss Cap
- Tổng lỗ tối đa trong ngày: **$500** (cộng gồm cả MNQ + MGC)
- Bot tự động dừng giao dịch khi đạt ngưỡng này

---

## Kiến trúc đã xây dựng

```
FTBot/
├── core/
│   ├── account_state.py    # Theo dõi P&L, daily loss theo ngày
│   └── risk_guard.py       # Kiểm tra daily cap, SL hard cap
├── brokers/
│   └── tradovate.py        # REST client: auth, getChart, parse_bars
├── strategies/
│   ├── base_strategy.py    # Abstract base class
│   └── ema_engulfing.py    # EMA 200/21 + Engulfing + EMA21 retest
├── backtest/
│   ├── data_loader.py      # Đọc CSV, convert timezone sang VN
│   ├── engine.py           # Vòng lặp bar-by-bar, breakeven SL, daily cap
│   └── report.py           # Win rate, profit factor, max drawdown, trade log
├── scripts/
│   ├── download_historical.py  # Tải từ Tradovate API (cần đăng ký app)
│   └── download_yfinance.py    # Tải từ yfinance (không cần API key, 59 ngày)
├── config/
│   ├── settings.yaml       # Tất cả tham số
│   ├── bulenox.yaml
│   ├── topstep.yaml
│   └── lucid.yaml
├── data/                   # Đặt file CSV vào đây (không commit)
├── requirements.txt
└── main.py                 # CLI entry point
```

---

## Cách chạy

```bash
# Cài dependencies
pip install -r requirements.txt

# Tải dữ liệu (59 ngày gần nhất, không cần API key)
python scripts/download_yfinance.py --instrument ALL

# Chạy backtest
python main.py --instrument ALL --save-log

# Chạy từng instrument
python main.py --instrument MNQ --start 2026-01-01
```

---

## Thứ tự xây dựng

1. ✅ **Backtest engine** — validate strategy trước khi kết nối broker thật
2. ⬜ **Cải thiện tham số** — điều chỉnh BE trigger/lock, lấy thêm dữ liệu 6–12 tháng
3. ⬜ **Risk Guard + Daily cap** — hoàn thiện cho live trading
4. ⬜ **Tradovate adapter** — kết nối, đọc giá realtime, đặt lệnh
5. ⬜ **Strategy engine** — chạy live với signal từ Tradovate feed
6. ⬜ **Dashboard** — monitor P&L 3 quỹ, chỉ làm sau khi strategy đã profit

---

## Kết quả backtest sơ bộ (59 ngày, 04/2026–06/2026)

| Instrument | Trades | Win% | P&L | Ghi chú |
|---|---|---|---|---|
| MNQ | 0 | — | — | Cần thêm dữ liệu, khung giờ overnight ít signal |
| MGC | 5 | 60% | -$274.98 | Sample quá nhỏ, BE params cần chỉnh |

**Vấn đề phát hiện:**
- BE trigger 30 ticks quá sớm → avg win chỉ $25 (5 ticks), avg loss $175 (35 ticks)
- 3/5 trade thoát tại BE_SL — cho thấy price thường hit 30 ticks rồi quay đầu
- Cần tối thiểu 6–12 tháng dữ liệu để kết luận có nghĩa

**Tham số cần thử trong lần backtest tiếp:**
- BE trigger: 50 ticks | BE lock: 15 ticks
- Lấy dữ liệu dài hơn qua Polygon.io free (2 năm)

---

## Lưu ý quan trọng về khung giờ

Khung 06:00–09:00 SA VN tương đương **6:00–9:00 PM ET (mùa đông)**:
- Đây là phiên tối Mỹ / Asian overnight — không phải RTH
- **MNQ:** Volume thấp, ít signal trong khung này
- **MGC:** Phù hợp hơn vì Tokyo session mở lúc 7:00 AM VN

---

## Tham số cần xác nhận

- [ ] Điều chỉnh BE trigger X và lock Y (đề xuất: 50 / 15)
- [ ] Lấy dữ liệu 6–12 tháng (Polygon.io free hoặc nguồn khác)
- [ ] Xem xét thêm phiên RTH (9:30–12:00 ET = 8:30–11:00 PM VN)
- [ ] Volume filter trên nến Engulfing

---

## Prop Firm Rules tham khảo (50k account)

| Quỹ | Daily Loss Limit | Max Trailing Drawdown | Profit Target |
|---|---|---|---|
| Bulenox 50k | ~$1,000 | ~$2,000 | ~$3,000 |
| TopStep 50k | ~$1,000 | ~$2,000 | ~$3,000 |
| Lucid Trading 50k | Xem tài liệu quỹ | Xem tài liệu quỹ | Xem tài liệu quỹ |

Bot hard cap: **$500/ngày** (50% buffer so với limit quỹ).

---

## Ghi chú kỹ thuật

- **Windows terminal:** Dùng ASCII trong print() — Windows cp1252 không hỗ trợ UTF-8 console
- **Tradovate API:** Endpoint `/md/getChart` cần đăng ký App CID/SEC riêng — chưa hoạt động
- **yfinance:** MNQ=F và MGC=F cho giá giống hệt MNQ/MGC, giới hạn 59 ngày 5-min
- **Data timezone:** yfinance trả về UTC, script tự convert sang VN time khi filter session
