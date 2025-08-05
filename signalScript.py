

import requests
import time
import pandas as pd
import threading
from flask import Flask

# ================== تنظیمات ==================
TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
CHAT_ID = '7628418093'
SYMBOLS = ['BTC-USDT', 'DOGE-USDT', 'SHIB-USDT', 'DOT-USDT', 'PEPE-USDT']
RSI_PERIOD = 36
TIMEFRAME = '5min'
RSI_LOWER = 30
RSI_UPPER = 70

# ================== ارسال پیام به تلگرام ==================
def send_message(message):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")

# ================== دریافت داده و محاسبه RSI ==================
def fetch_ohlcv(symbol, limit=800):
    url = f'https://api.kucoin.com/api/v1/market/candles?type={TIMEFRAME}&symbol={symbol}&limit={limit}'
    response = requests.get(url)
    data = response.json()
    if data['code'] != "200":
        print(f"❌ خطا در دریافت داده برای {symbol}")
        return None
    ohlcv = data['data']
    df = pd.DataFrame(ohlcv, columns=['time', 'open', 'close', 'high', 'low', 'volume'])
    df = df.iloc[::-1]  # ترتیب زمانی را برعکس کن
    df['close'] = pd.to_numeric(df['close'])
    return df

def compute_rsi(series, period):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ================== بررسی سیگنال و گزارش ==================
def check_signals():
    print("📊 شروع بررسی RSI و قیمت‌ها...")
    for symbol in SYMBOLS:
        df = fetch_ohlcv(symbol)
        if df is None or df.empty:
            continue

        last_close = df['close'].iloc[-1]
        rsi_series = compute_rsi(df['close'], RSI_PERIOD)
        last_rsi = rsi_series.iloc[-1]

        print(f"🔍 {symbol}: قیمت={last_close:.2f} | RSI={last_rsi:.2f}")
        send_message(f"📈 {symbol} | 💰 قیمت: {last_close:.2f} | 📟 RSI: {last_rsi:.2f}")

        # ارسال سیگنال در صورت عبور از آستانه
        if last_rsi < RSI_LOWER:
            send_message(f"✅ سیگنال خرید {symbol} (RSI = {last_rsi:.2f})")
        elif last_rsi > RSI_UPPER:
            send_message(f"⚠️ سیگنال فروش {symbol} (RSI = {last_rsi:.2f})")

# ================== حلقه‌ی اصلی اجرا در بک‌گراند ==================
def main_loop():
    while True:
        check_signals()
        print(f"⏳ منتظر 1 دقیقه...")
        time.sleep(60)  # هر 60 ثانیه (1 دقیقه)

# ================== راه‌اندازی Flask برای زنده نگه‌داشتن پروژه ==================
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot is running and checking RSI every 1 minute!"

if __name__ == '__main__':
    threading.Thread(target=main_loop).start()
    app.run(host='0.0.0.0', port=10000)


