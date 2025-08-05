import time
import threading
import requests
import pandas as pd
from flask import Flask
import datetime

# ----- پیکربندی -----
SYMBOLS = ["BTCUSDT", "DOGEUSDT", "SHIBUSDT", "DOTUSDT", "PEPEUSDT"]
RSI_LENGTH = 36
INTERVAL = "5m"
API_URL = "https://api.binance.com/api/v3/klines"
TELEGRAM_TOKEN = "توکن ربات"
TELEGRAM_CHAT_ID = "chat_id یا عددی که از @userinfobot گرفتی"

app = Flask(__name__)

# ----- محاسبه RSI -----
def calculate_rsi(prices, length=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ----- گرفتن داده از Binance -----
def get_klines(symbol, interval="5m", limit=800):
    url = f"{API_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    close_prices = [float(kline[4]) for kline in data]
    return pd.Series(close_prices)

# ----- ارسال پیام به تلگرام -----
def send_message_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

# ----- بررسی RSI و ارسال سیگنال -----
def check_rsi_signals():
    for symbol in SYMBOLS:
        prices = get_klines(symbol, interval=INTERVAL)
        if prices is None or len(prices) < RSI_LENGTH:
            continue
        rsi_series = calculate_rsi(prices, RSI_LENGTH)
        current_rsi = rsi_series.iloc[-1]
        msg = f"📊 بررسی: {symbol}\n📟 RSI فعلی: {round(current_rsi, 2)}"
        print(msg)

        # اگر سیگنالی صادر شد
        if current_rsi < 30:
            msg += "\n📉 سیگنال خرید: RSI زیر 30"
            send_message_to_telegram(msg)
        elif current_rsi > 70:
            msg += "\n📈 سیگنال فروش: RSI بالای 70"
            send_message_to_telegram(msg)

# ----- ارسال قیمت هر 10 دقیقه -----
def send_prices():
    message = f"📆 گزارش قیمت‌ها - {datetime.datetime.now().strftime('%H:%M')}\n"
    for symbol in SYMBOLS:
        prices = get_klines(symbol, interval=INTERVAL)
        if prices is None:
            continue
        last_price = prices.iloc[-1]
        rsi = calculate_rsi(prices, RSI_LENGTH).iloc[-1]
        message += f"\n💰 {symbol}: {last_price} | RSI: {round(rsi, 2)}"
    send_message_to_telegram(message)

# ----- حلقه اصلی RSI هر 1 دقیقه -----
def rsi_loop():
    while True:
        print("✅ شروع بررسی RSI...")
        check_rsi_signals()
        time.sleep(60)  # هر دقیقه

# ----- حلقه ارسال قیمت هر 10 دقیقه -----
def price_loop():
    while True:
        print("📤 ارسال قیمت‌ها به تلگرام...")
        send_prices()
        time.sleep(600)  # هر 10 دقیقه

# ----- اجرای حلقه‌ها در Thread -----
@app.before_first_request
def start_threads():
    threading.Thread(target=rsi_loop, daemon=True).start()
    threading.Thread(target=price_loop, daemon=True).start()

# ----- اجرای Flask برای دیپلوی -----
@app.route('/')
def home():
    return "Bot is running..."

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
