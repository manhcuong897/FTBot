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

> **Lưu ý chưa xác định:** Ngưỡng "tiệm cận" EMA 21 (ticks) chưa được định nghĩa — cần xác nhận trước khi backtest.

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
- X và Y là tham số người dùng có thể tùy chỉnh

### Daily Loss Cap
- Tổng lỗ tối đa trong ngày: **$500** (cộng gồm cả MNQ + MGC)
- Bot tự động dừng giao dịch khi đạt ngưỡng này
- Ngưỡng $500 = 50% daily limit của prop firm (buffer an toàn)

---

## Kiến trúc dự kiến

```
FTBot/
├── core/
│   ├── risk_guard.py       # Hard rules: daily loss cap, prop firm limits
│   ├── account_state.py    # Theo dõi P&L, drawdown realtime
│   └── order_manager.py    # OCO, bracket, position tracking
├── brokers/
│   └── tradovate.py        # WebSocket feed + REST orders
├── strategies/
│   ├── base_strategy.py    # Interface chung
│   └── ema_engulfing.py    # Strategy EMA 200/21 + Engulfing
├── backtest/
│   └── engine.py           # Backtest engine offline
├── config/
│   ├── bulenox.yaml        # Rule limits từng quỹ
│   ├── topstep.yaml
│   └── lucid.yaml
└── main.py
```

---

## Thứ tự xây dựng

1. **Backtest engine** — validate strategy trước khi kết nối broker thật
2. **Risk Guard + Daily cap** — quan trọng nhất, bảo vệ prop firm account
3. **Tradovate adapter** — kết nối, đọc giá realtime, đặt lệnh
4. **Strategy engine** — chạy live với signal từ Tradovate feed
5. **Dashboard** — monitor P&L 3 quỹ, chỉ làm sau khi strategy đã profit

---

## Lưu ý quan trọng về khung giờ

Khung 06:00–09:00 SA VN tương đương **6:00–9:00 PM ET (mùa đông)**:
- Đây là phiên tối Mỹ / Asian overnight — không phải RTH
- **MNQ:** Volume thấp (10–20% RTH), dễ fake signal → cần volume filter, xem xét thêm phiên RTH
- **MGC:** Phù hợp hơn vì Tokyo session mở lúc 7:00 AM VN, gold có thanh khoản châu Á

Cần cân nhắc thêm phiên **8:30–9:30 PM VN** (pre-market Mỹ) cho MNQ.

---

## Tham số cần xác nhận trước backtest

- [ ] Ngưỡng "tiệm cận" EMA 21: bao nhiêu ticks?
- [ ] Breakeven trigger X (ticks) và lock Y (ticks)
- [ ] Có thêm phiên giao dịch nào ngoài 6h–9h SA không?
- [ ] Volume filter: điều kiện volume tối thiểu trên nến Engulfing?

---

## Prop Firm Rules tham khảo (50k account)

| Quỹ | Daily Loss Limit | Max Trailing Drawdown | Profit Target |
|---|---|---|---|
| Bulenox 50k | ~$1,000 | ~$2,000 | ~$3,000 |
| TopStep 50k | ~$1,000 | ~$2,000 | ~$3,000 |
| Lucid Trading 50k | Xem tài liệu quỹ | Xem tài liệu quỹ | Xem tài liệu quỹ |

Bot hard cap: **$500/ngày** (50% buffer so với limit quỹ).
