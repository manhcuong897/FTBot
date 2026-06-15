import pandas as pd
import pytz

VN_TZ = pytz.timezone('Asia/Ho_Chi_Minh')


def load_ohlcv(filepath: str, data_timezone: str = 'US/Eastern') -> pd.DataFrame:
    """
    Đọc file CSV OHLCV với cột: datetime,open,high,low,close,volume
    datetime có thể ở bất kỳ timezone nào (chỉ định qua data_timezone).
    Trả về DataFrame với index là UTC và cột 'datetime_vn' để lọc session.
    """
    df = pd.read_csv(filepath)
    df.columns = [c.strip().lower() for c in df.columns]

    # Hỗ trợ tên cột "date" + "time" riêng hoặc "datetime" gộp
    if 'datetime' not in df.columns and 'date' in df.columns and 'time' in df.columns:
        df['datetime'] = df['date'].astype(str) + ' ' + df['time'].astype(str)
        df.drop(columns=['date', 'time'], inplace=True)

    source_tz = pytz.timezone(data_timezone)
    df['datetime'] = pd.to_datetime(df['datetime'])

    if df['datetime'].dt.tz is None:
        df['datetime'] = df['datetime'].dt.tz_localize(source_tz)
    else:
        df['datetime'] = df['datetime'].dt.tz_convert(source_tz)

    df['datetime_vn'] = df['datetime'].dt.tz_convert(VN_TZ)
    df = df.sort_values('datetime').reset_index(drop=True)

    required = {'open', 'high', 'low', 'close'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV thiếu cột: {missing}")

    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    if 'volume' in df.columns:
        df['volume'] = df['volume'].astype(float)

    return df


def filter_session(df: pd.DataFrame, start_vn: str = "06:00", end_vn: str = "09:00") -> pd.DataFrame:
    """Lọc chỉ giữ các nến trong khung giờ VN."""
    start_h, start_m = map(int, start_vn.split(':'))
    end_h, end_m = map(int, end_vn.split(':'))
    start_minutes = start_h * 60 + start_m
    end_minutes = end_h * 60 + end_m

    def in_session(dt_vn):
        t = dt_vn.hour * 60 + dt_vn.minute
        return start_minutes <= t < end_minutes

    mask = df['datetime_vn'].apply(in_session)
    return df[mask].reset_index(drop=True)
