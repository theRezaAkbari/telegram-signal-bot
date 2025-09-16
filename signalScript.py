import threading
from flask import Flask
import time
import requests
import pandas as pd

# =============== تنظیمات ===============
BOT_TOKEN = '8477585069:AAG8gq06MW7ctfuA9w-WzsUXcH50bGjN6mw'
CHAT_ID = '7628418093'

# همه ارزها + SOL
SYMBOLS = ['BTC-USDT','SOL-USDT']

INTERVAL = '1min'            # ✅ تایم‌فریم 1 دقیقه
RSI_PERIOD = 60              # ✅ RSI دوره 60
CHECK_INTERVAL = 60          # ✅ هر 1 دقیقه برای سیگنال‌دهی
RSI_PRINT_INTERVAL = 60      # هر 1 دقیقه برای چاپ RSI در ترمینال
PRICE_SEND_INTERVAL = 3600   # ✅ هر 1 ساعت ارسال قیمت/RSI به تلگرام

# آستانه‌های کراس
CROSS_LEVELS = [30, 40, 60, 70]

# =============== توابع تحلیل ===============
def get_kucoin_candles(symbol, interval, limit=1800):
    """
    داده کندل از KuCoin:
    پاسخ: [ time, open, close, high, low, volume, turnover ] (به صورت معکوس زمانی)
    ما معکوسش می‌کنیم تا قدیمی->جدید باشد.
    """
    url = f'https://api.kucoin.com/api/v1/market/candles?symbol={symbol}&type={interval}&limit={limit}'
    try:
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if data.get('code') != '200000':
            print(f"❌ خطا در گرفتن داده از کوکوین: {data}")
            return None
        candles = data['data'][::-1]  # مرتب‌سازی زمانی (قدیمی به جدید)
        return candles
    except Exception as e:
        print(f"⚠️ خطا در دریافت داده از کوکوین: {e}")
        return None

def compute_rsi_from_closes(close_prices, period=60):
    """
    RSI به سبک Wilder (EMA) تا با TradingView هم‌خوان‌تر باشد.
    """
    series = pd.Series(close_prices, dtype='float64')
    delta = series.diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # EMA با پارامتر Wilder: alpha = 1/period  -> در pandas: com = period-1
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    payload = {'chat_id': CHAT_ID, 'text': message}
    try:
        resp = requests.post(url, data=payload, timeout=10)
        if resp.status_code != 200:
            print(f"❌ خطا در ارسال پیام تلگرام: {resp.text}")
    except Exception as e:
        print(f"⚠️ استثنا در ارسال پیام تلگرام: {e}")

def crossed(prev_value: float, curr_value: float, level: float):
    """
    بررسی عبور (کراس) از یک سطح: هم کراس به بالا و هم به پایین.
    خروجی: ('up' | 'down' | None)
    """
    if pd.isna(prev_value) or pd.isna(curr_value):
        return None
    if prev_value < level <= curr_value:
        return 'up'
    if prev_value > level >= curr_value:
        return 'down'
    return None

# =============== سیگنال RSI هر 1 دقیقه ===============
def check_signals():
    print("✅ بررسی سیگنال‌ها شروع شد...")
    while True:
        for symbol in SYMBOLS:
            try:
                candles = get_kucoin_candles(symbol, INTERVAL)
                if candles is None or len(candles) < RSI_PERIOD + 2:
                    print(f"⚠️ داده کافی برای {symbol} نیست.")
                    continue

                # close در ایندکس 2 طبق ساختار KuCoin
                close_prices = [float(c[2]) for c in candles if len(c) > 2]
                rsi_series = compute_rsi_from_closes(close_prices, RSI_PERIOD)

                last_rsi = rsi_series.iloc[-1]
                prev_rsi = rsi_series.iloc[-2]

                print(f"RSI آخر {symbol}: {last_rsi:.2f}")

                # بررسی کراس برای سطوح تعیین‌شده
                for level in CROSS_LEVELS:
                    direction = crossed(prev_rsi, last_rsi, level)
                    if direction == 'up':
                        send_telegram_message(f"📈 سیگنال کراس به بالا | {symbol} | سطح {level} | RSI: {last_rsi:.2f}")
                    elif direction == 'down':
                        send_telegram_message(f"📉 سیگنال کراس به پایین | {symbol} | سطح {level} | RSI: {last_rsi:.2f}")

            except Exception as e:
                print(f"⚠️ خطا در پردازش {symbol}: {e}")

        time.sleep(CHECK_INTERVAL)  # هر 1 دقیقه

# =============== چاپ RSI هر دقیقه برای مقایسه در ترمینال ===============
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
                last_rsi = float(rsi_series.iloc[-1])
                print(f"📈 {symbol} | RSI({RSI_PERIOD}): {round(last_rsi, 2)}")
            except Exception as e:
                print(f"⚠️ خطا در محاسبه RSI برای {symbol}: {e}")
        time.sleep(RSI_PRINT_INTERVAL)  # هر دقیقه

# =============== ارسال قیمت و RSI هر ساعت به تلگرام ===============
def send_prices_periodically():
    while True:
        messages = ["🕐 گزارش ساعتی قیمت و RSI:"]
        for symbol in SYMBOLS:
            try:
                candles = get_kucoin_candles(symbol, INTERVAL, limit=RSI_PERIOD + 5)
                if candles is None or len(candles) == 0:
                    messages.append(f"⚠️ داده قیمت برای {symbol} موجود نیست.")
                    continue
                last_close = float(candles[-1][2])
                closes = [float(c[2]) for c in candles if len(c) > 2]
                rsi_val = compute_rsi_from_closes(closes, RSI_PERIOD).iloc[-1]
                messages.append(f"💰 {symbol} | Price: {last_close} | RSI({RSI_PERIOD}): {rsi_val:.2f}")
            except Exception as e:
                messages.append(f"⚠️ خطا در دریافت قیمت/RSI {symbol}: {e}")
        full_message = "\n".join(messages)
        send_telegram_message(full_message)
        time.sleep(PRICE_SEND_INTERVAL)  # هر 1 ساعت

# =============== Flask سرور برای Render ===============
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is alive!"

if __name__ == '__main__':
    # اجرای thread چک سیگنال‌ها (هر دقیقه)
    signal_thread = threading.Thread(target=check_signals, daemon=True)
    signal_thread.start()

    # اجرای thread چاپ RSI در ترمینال (هر دقیقه)
    rsi_thread = threading.Thread(target=print_rsi_values, daemon=True)
    rsi_thread.start()

    # اجرای thread ارسال قیمت‌ها به تلگرام هر 1 ساعت
    price_thread = threading.Thread(target=send_prices_periodically, daemon=True)
    price_thread.start()

    # اجرای سرور Flask
    app.run(host="0.0.0.0", port=10000)

#--------------------------------------------------------------------------------