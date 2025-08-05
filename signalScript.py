import requests
import time
import threading
from flask import Flask
import numpy as np

# 📍 پیکربندی اولیه
TELEGRAM_TOKEN = 'توکن بات'
TELEGRAM_CHAT_ID = 'آی‌دی چت شما'
SYMBOLS = ['BTCUSDT', 'DOGEUSDT', 'SHIBUSDT', 'DOTUSDT', 'PEPEUSDT']
RSI_PERIOD = 36
INTERVAL = '5m'  # تایم‌فریم ۵ دقیقه‌ای
CHECK_INTERVAL = 60  # هر ۱ دقیقه چک شود
PRICE_INTERVAL = 600  # هر ۱۰ دقیقه ارسال قیمت

# 📤 ارسال پیام به تلگرام
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = {'chat_id': TELEGRAM_CHAT_ID, 'text': message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f'❌ خطا در ارسال پیام تلگرام: {e}')

# 📉 محاسبه RSI
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    seed = deltas[:period]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        upval = max(delta, 0)
        downval = -min(delta, 0)
        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period
        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs)
    return rsi

# 📊 دریافت داده و بررسی RSI
def check_rsi_and_signals():
    while True:
        print("✅ بررسی RSI شروع شد...")
        for symbol in SYMBOLS:
            try:
                url = f'https://api.binance.com/api/v3/klines?symbol={symbol}&interval={INTERVAL}&limit=800'
                response = requests.get(url)
                data = response.json()
                closes = np.array([float(candle[4]) for candle in data])

                if len(closes) < RSI_PERIOD:
                    print(f"❌ داده کافی برای {symbol} وجود ندارد.")
                    continue

                rsi = calculate_rsi(closes, RSI_PERIOD)[-1]
                price = closes[-1]
                print(f"📟 RSI فعلی {symbol}: {round(rsi, 2)}")
                print(f"💰 قیمت فعلی {symbol}: {price}")

                # ✉️ اگر سیگنال داده شد به بات پیام بفرست
                if rsi < 30:
                    send_telegram_message(f"📈 سیگنال خرید: RSI={round(rsi,2)} برای {symbol}")
                elif rsi > 70:
                    send_telegram_message(f"📉 سیگنال فروش: RSI={round(rsi,2)} برای {symbol}")
            except Exception as e:
                print(f"⚠️ خطا در پردازش {symbol}: {e}")
        time.sleep(CHECK_INTERVAL)

# 💰 ارسال قیمت تمام نمادها هر ۱۰ دقیقه
def send_price_updates():
    while True:
        message = "📊 قیمت‌ نمادها:\n"
        for symbol in SYMBOLS:
            try:
                url = f'https://api.binance.com/api/v3/ticker/price?symbol={symbol}'
                response = requests.get(url).json()
                price = float(response['price'])
                message += f"{symbol}: {price}\n"
            except:
                message += f"{symbol}: خطا در دریافت قیمت\n"
        send_telegram_message(message)
        time.sleep(PRICE_INTERVAL)

# 🚀 اجرای موازی در پس‌زمینه با Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is running!"

if __name__ == '__main__':
    # اجرای تسک‌ها در پس‌زمینه
    threading.Thread(target=check_rsi_and_signals, daemon=True).start()
    threading.Thread(target=send_price_updates, daemon=True).start()

    # اجرای سرور Flask
    app.run(host='0.0.0.0', port=10000)
