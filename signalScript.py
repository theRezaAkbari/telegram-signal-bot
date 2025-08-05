import threading
from flask import Flask
import time
import requests
import pandas as pd

# =============== تنظیمات ===============
BOT_TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
CHAT_ID = '7628418093'
SYMBOLS = ['BTC-USDT', 'DOGE-USDT', 'SHIB-USDT', 'DOT-USDT', 'PEPE-USDT']

INTERVAL = '5min'  # تایم فریم کوکوین
RSI_PERIOD = 36
CHECK_INTERVAL = 300  # هر 5 دقیقه برای سیگنال دهی
RSI_PRINT_INTERVAL = 60  # هر 1 دقیقه برای چاپ RSI در ترمینال
PRICE_SEND_INTERVAL = 600  # هر 10 دقیقه ارسال قیمت به تلگرام

# =============== توابع تحلیل ===============

def get_kucoin_candles(symbol, interval, limit=800):
    url = f'https://api.kucoin.com/api/v1/market/candles?symbol={symbol}&type={interval}&limit={limit}'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data['code'] != '200000':
            print(f"❌ خطا در گرفتن داده از کوکوین: {data}")
            return None
        candles = data['data']
        candles = candles[::-1]  # مرتب‌سازی زمانی (قدیمی به جدید)
        return candles
    except Exception as e:
        print(f"⚠️ خطا در دریافت داده از کوکوین: {e}")
        return None

def compute_rsi_from_closes(close_prices, period=36):
    series = pd.Series(close_prices)
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / avg_loss
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

# چک کردن سیگنال RSI هر 5 دقیقه و ارسال پیام در صورت سیگنال
def check_signals():
    print("✅ بررسی سیگنال‌ها شروع شد...")
    for symbol in SYMBOLS:
        try:
            candles = get_kucoin_candles(symbol, INTERVAL)
            if candles is None or len(candles) < RSI_PERIOD:
                print(f"⚠️ داده کافی برای {symbol} نیست.")
                continue
            close_prices = [float(c[2]) for c in candles if len(c) > 2]
            rsi_series = compute_rsi_from_closes(close_prices, RSI_PERIOD)
            last_rsi = rsi_series.iloc[-1]
            print(f"RSI آخر {symbol}: {last_rsi:.2f}")

            if last_rsi <= 30:
                send_telegram_message(f"📈 سیگنال لانگ برای {symbol} | RSI: {last_rsi:.2f}")
            elif last_rsi >= 70:
                send_telegram_message(f"📉 سیگنال شورت برای {symbol} | RSI: {last_rsi:.2f}")
        except Exception as e:
            print(f"⚠️ خطا در پردازش {symbol}: {e}")

# چاپ RSI هر دقیقه برای مقایسه
def print_rsi_values():
    while True:
        print("\n🔍 مقایسه RSI با TradingView:")
        for symbol in SYMBOLS:
            try:
                candles = get_kucoin_candles(symbol, INTERVAL)
                if candles is None or len(candles) < RSI_PERIOD:
                    print(f"⛔ داده کافی برای {symbol} موجود نیست.")
                    continue
                close_prices = [float(c[2]) for c in candles if len(c) > 2]
                rsi_series = compute_rsi_from_closes(close_prices, RSI_PERIOD)
                last_rsi = rsi_series.iloc[-1]
                print(f"📈 {symbol} | RSI({RSI_PERIOD}): {round(last_rsi, 2)}")
            except Exception as e:
                print(f"⚠️ خطا در محاسبه RSI برای {symbol}: {e}")
        time.sleep(RSI_PRINT_INTERVAL)

# ارسال قیمت هر 10 دقیقه به تلگرام
def send_prices_periodically():
    while True:
        messages = []
        for symbol in SYMBOLS:
            try:
                candles = get_kucoin_candles(symbol, INTERVAL, limit=1)
                if candles is None or len(candles) == 0:
                    messages.append(f"⚠️ داده قیمت برای {symbol} موجود نیست.")
                    continue
                last_close = float(candles[-1][2])
                messages.append(f"💰 قیمت فعلی {symbol}: {last_close}")
            except Exception as e:
                messages.append(f"⚠️ خطا در دریافت قیمت {symbol}: {e}")
        full_message = "\n".join(messages)
        send_telegram_message(full_message)
        time.sleep(PRICE_SEND_INTERVAL)

# حلقه اصلی چک سیگنال‌ها هر 5 دقیقه
def main_loop():
    while True:
        check_signals()
        time.sleep(CHECK_INTERVAL)

# =============== Flask سرور برای Render ===============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

if __name__ == '__main__':
    # اجرای thread چک سیگنال‌ها
    signal_thread = threading.Thread(target=main_loop)
    signal_thread.start()

    # اجرای thread چاپ RSI در ترمینال
    rsi_thread = threading.Thread(target=print_rsi_values)
    rsi_thread.start()

    # اجرای thread ارسال قیمت‌ها به تلگرام هر 10 دقیقه
    price_thread = threading.Thread(target=send_prices_periodically)
    price_thread.start()

    # اجرای سرور Flask
    app.run(host="0.0.0.0", port=10000)
