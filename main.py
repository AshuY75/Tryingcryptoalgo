import time
import datetime
import requests
import pandas as pd
import numpy as np
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import os

# Load secrets from .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET")

session = HTTP(testnet=False, api_key=BYBIT_API_KEY, api_secret=BYBIT_API_SECRET)
SYMBOLS = ["BTCUSDT", "ETHUSDT"]

buy_count = 0
sell_count = 0
last_summary_sent = datetime.datetime.now()

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("[TELEGRAM] Message sent.")
        else:
            print(f"[TELEGRAM] Failed: {response.text}")
    except Exception as e:
        print(f"[ERROR] Telegram error: {e}")

def save_signal(symbol, signal_type, price, rsi, time_stamp):
    df = pd.DataFrame([[symbol, signal_type, price, rsi, time_stamp]],
                      columns=["Symbol", "Type", "Price", "RSI", "Time"])
    df.to_csv("signals.csv", mode='a', header=not os.path.exists("signals.csv"), index=False)
    print("[SAVE] Signal logged.")

def fetch_ohlcv(symbol, interval="60", limit=100):
    try:
        result = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            limit=limit
        )
        data = result['result']['list']
        df = pd.DataFrame(data, columns=[
            "timestamp", "open", "high", "low", "close", "volume", "turnover"
        ])
        df[["timestamp", "open", "high", "low", "close", "volume", "turnover"]] = df[["timestamp", "open", "high", "low", "close", "volume", "turnover"]].astype(float)
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"[ERROR] Failed to fetch OHLCV for {symbol}: {e}")
        return None

def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def calculate_bollinger_bands(df, period=20):
    sma = df['close'].rolling(window=period).mean()
    std = df['close'].rolling(window=period).std()
    upper_band = sma.iloc[-1] + (2 * std.iloc[-1])
    lower_band = sma.iloc[-1] - (2 * std.iloc[-1])
    return upper_band, lower_band

print("[INFO] Bot started successfully.")
send_telegram_message("🤖 Bot started and running!")

last_candle_time = None

while True:
    now = datetime.datetime.now()
    now_hour = now.hour

    # Only run between 9:00 AM to 12:00 AM (15 hours)
    if not (9 <= now_hour < 24):
        print("[INFO] Outside of active hours (9 AM to Midnight). Sleeping 5 minutes...\n")
        time.sleep(300)
        continue

    print(f"\n[LOOP] Checking signals...")
    max_candle_time = None

    for symbol in SYMBOLS:
        print(f"[FETCH] Getting OHLCV for {symbol}")
        df = fetch_ohlcv(symbol, interval='60', limit=100)
        if df is None or df.empty:
            print(f"[WARN] Skipping {symbol} due to no data.\n")
            continue

        candle_time = df['timestamp'].iloc[-1]
        if max_candle_time is None or candle_time > max_candle_time:
            max_candle_time = candle_time

        price = df['close'].iloc[-1]
        rsi = calculate_rsi(df)
        upper_band, lower_band = calculate_bollinger_bands(df)
        current_time = now.strftime('%Y-%m-%d %H:%M:%S')

        print(f"[DATA] {symbol} | Price: {price:.2f} | RSI: {rsi:.2f} | BB Upper: {upper_band:.2f} | BB Lower: {lower_band:.2f}")

        if rsi >= 70 and price >= upper_band:
            msg = f"🔴 SELL SIGNAL: {symbol}\nPrice: {price:.2f}\nRSI: {rsi:.2f}\nTime: {current_time}"
            send_telegram_message(msg)
            save_signal(symbol, 'SELL', price, rsi, current_time)
            sell_count += 1
        elif rsi <= 30 and price <= lower_band:
            msg = f"🟢 BUY SIGNAL: {symbol}\nPrice: {price:.2f}\nRSI: {rsi:.2f}\nTime: {current_time}"
            send_telegram_message(msg)
            save_signal(symbol, 'BUY', price, rsi, current_time)
            buy_count += 1
        else:
            print(f"[INFO] No signal for {symbol} at {current_time}")

    if max_candle_time and (last_candle_time is None or max_candle_time != last_candle_time):
        readable = datetime.datetime.fromtimestamp(max_candle_time / 1000).strftime('%Y-%m-%d %H:%M:%S')
        msg = f"⏰ New 1-hour candle at {readable}. Bot is alive and running."
        print(f"[INFO] {msg}")
        send_telegram_message(msg)
        last_candle_time = max_candle_time

    # Send daily summary every 24 hours
    if (now - last_summary_sent).total_seconds() >= 86400:
        summary_msg = f"📊 24-Hour Summary:\nTotal BUYs: {buy_count}\nTotal SELLs: {sell_count}\nTime: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        send_telegram_message(summary_msg)
        buy_count = 0
        sell_count = 0
        last_summary_sent = now

    print("[SLEEP] Waiting 30 seconds...\n")
    time.sleep(30)
