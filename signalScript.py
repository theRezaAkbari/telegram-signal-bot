# import time
# import requests
# import pandas as pd

# # پارامترها
# BOT_TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
# CHAT_ID = '7628418093'
# SYMBOLS = ['BTC-USDT', 'DOGE-USDT', 'SHIB-USDT', 'DOT-USDT', 'PEPE-USDT']
# TIMEFRAME = '5min'
# RSI_PERIOD = 36
# CHECK_INTERVAL = 30  # هر 5 دقیقه

# def get_kucoin_candles(symbol, timeframe):
#     url = f'https://api.kucoin.com/api/v1/market/candles?type={timeframe}&symbol={symbol}&limit=100'
#     try:
#         resp = requests.get(url, timeout=10)
#         data = resp.json()
#         if data['code'] != '200000':
#             print(f"❌ خطا در گرفتن داده: {data}")
#             return None
#         df = pd.DataFrame(data['data'], columns=['time','open','close','high','low','volume','turnover'])
#         df = df.iloc[::-1]  # معکوس برای ترتیب زمانی
#         df['close'] = df['close'].astype(float)
#         return df
#     except Exception as e:
#         print(f"⚠️ خطا: {e}")
#         return None

# def compute_rsi(series, period=14):
#     delta = series.diff()
#     gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
#     loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
#     rs = gain / loss
#     rsi = 100 - (100 / (1 + rs))
#     return rsi

# def send_telegram_message(message):
#     url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
#     payload = {'chat_id': CHAT_ID, 'text': message}
#     try:
#         resp = requests.post(url, data=payload)
#         if resp.status_code != 200:
#             print(f"❌ خطا در ارسال پیام تلگرام: {resp.text}")
#     except Exception as e:
#         print(f"⚠️ استثنا در ارسال پیام تلگرام: {e}")

# def check_signals():
#     for symbol in SYMBOLS:
#         print(f"📊 بررسی: {symbol}")
#         df = get_kucoin_candles(symbol, TIMEFRAME)
#         if df is None or len(df) < RSI_PERIOD:
#             print(f"⚠️ داده کافی برای {symbol} نیست.")
#             continue
#         df['rsi'] = compute_rsi(df['close'], RSI_PERIOD)
#         last_rsi = df['rsi'].iloc[-1]
#         print(f"RSI آخر {symbol}: {last_rsi:.2f}")

#         if last_rsi <= 30:
#             send_telegram_message(f"📈 سیگنال لانگ برای {symbol} | RSI: {last_rsi:.2f}")
#         elif last_rsi >= 70:
#             send_telegram_message(f"📉 سیگنال شورت برای {symbol} | RSI: {last_rsi:.2f}")

# def main_loop():
#     while True:
#         print("✅ شروع چک کردن...")
#         check_signals()
#         print(f"⏳ منتظر {CHECK_INTERVAL/60} دقیقه...")
#         time.sleep(CHECK_INTERVAL)

# if __name__ == '__main__':
#     main_loop()

import requests
import time
import datetime
import pandas as pd

# توکن ربات و چت آیدی تلگرام
TELEGRAM_BOT_TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
TELEGRAM_CHAT_ID = '7628418093'

# لیست نمادها در KuCoin
symbols = ['BTC-USDT', 'DOGE-USDT', 'SHIB-USDT', 'DOT-USDT', 'PEPE-USDT']

# تابع ارسال پیام به تلگرام
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    requests.post(url, data=data)

# تابع محاسبه RSI
def calculate_rsi(df, period=14):
    df['change'] = df['close'].diff()
    df['gain'] = df['change'].clip(lower=0)
    df['loss'] = -df['change'].clip(upper=0)
    avg_gain = df['gain'].rolling(window=period).mean()
    avg_loss = df['loss'].rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# تابع دریافت و بررسی RSI برای یک نماد
def check_rsi(symbol):
    try:
        url = f"https://api.kucoin.com/api/v1/market/candles?type=1min&symbol={symbol}"
        response = requests.get(url).json()

        if response.get('code') != '200000':
            return f"⚠️ خطا در دریافت داده برای {symbol}: {response}"

        # KuCoin returns data as [time, open, close, high, low, volume, turnover]
        data = response['data']
        df = pd.DataFrame(data, columns=['time', 'open', 'close', 'high', 'low', 'volume', 'turnover'])
        df['close'] = df['close'].astype(float)
        df = df.sort_values('time')  # مرتب‌سازی زمان

        rsi_series = calculate_rsi(df)
        last_rsi = rsi_series.iloc[-1]

        print(f"{symbol} → RSI: {last_rsi:.2f}")

        if last_rsi < 30:
            return f"📉 سیگنال خرید (RSI={last_rsi:.2f}) برای {symbol}"
        elif last_rsi > 70:
            return f"📈 سیگنال فروش (RSI={last_rsi:.2f}) برای {symbol}"
        else:
            return None
    except Exception as e:
        return f"❌ خطا در بررسی {symbol}: {e}"

# حلقه اصلی بررسی
while True:
    print(f"\n✅ شروع بررسی سیگنال‌ها - {datetime.datetime.now()}")
    send_telegram_message(f"✅ شروع بررسی سیگنال‌ها - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    for symbol in symbols:
        result = check_rsi(symbol)
        if result:
            send_telegram_message(result)

    # هر 5 دقیقه صبر کن
    print("⏳ صبر برای 5 دقیقه...")
    time.sleep(5 * 60)
