import threading
from flask import Flask
import time
import requests
import pandas as pd

# =============== تنظیمات ===============
BOT_TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
CHAT_ID = '7628418093'
SYMBOLS = ['BTC-USDT', 'DOGE-USDT', 'SHIB-USDT', 'DOT-USDT', 'PEPE-USDT']
TIMEFRAME = '5min'
RSI_PERIOD = 36
CHECK_INTERVAL = 300  # هر 5 دقیقه

# =============== توابع تحلیل ===============
def get_kucoin_candles(symbol, timeframe):
    url = f'https://api.kucoin.com/api/v1/market/candles?type={timeframe}&symbol={symbol}&limit=100'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data['code'] != '200000':
            print(f"❌ خطا در گرفتن داده: {data}")
            return None
        df = pd.DataFrame(data['data'], columns=['time','open','close','high','low','volume','turnover'])
        df = df.iloc[::-1]
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"⚠️ خطا: {e}")
        return None

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        resp = requests.post(url, data=payload)
        if resp.status_code != 200:
            print(f"❌ خطا در ارسال پیام تلگرام: {resp.text}")
    except Exception as e:
        print(f"⚠️ استثنا در ارسال پیام تلگرام: {e}")

def check_signals():
    for symbol in SYMBOLS:
        print(f"📊 بررسی: {symbol}")
        df = get_kucoin_candles(symbol, TIMEFRAME)
        if df is None or len(df) < RSI_PERIOD:
            print(f"⚠️ داده کافی برای {symbol} نیست.")
            continue
        df['rsi'] = compute_rsi(df['close'], RSI_PERIOD)
        last_rsi = df['rsi'].iloc[-1]
        print(f"RSI آخر {symbol}: {last_rsi:.2f}")

        if last_rsi <= 30:
            send_telegram_message(f"📈 سیگنال لانگ برای {symbol} | RSI: {last_rsi:.2f}")
        elif last_rsi >= 70:
            send_telegram_message(f"📉 سیگنال شورت برای {symbol} | RSI: {last_rsi:.2f}")

def main_loop():
    while True:
        print("✅ شروع چک کردن...")
        check_signals()
        print(f"⏳ منتظر {CHECK_INTERVAL/60} دقیقه...")
        time.sleep(CHECK_INTERVAL)

# =============== Flask سرور برای Render ===============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

# =============== اجرای همزمان دو thread ===============
if __name__ == '__main__':
    # اجرای حلقه چک سیگنال‌ها در Thread جدا
    signal_thread = threading.Thread(target=main_loop)
    signal_thread.start()

    # اجرای سرور Flask برای زنده ماندن در Render
    app.run(host="0.0.0.0", port=10000)
