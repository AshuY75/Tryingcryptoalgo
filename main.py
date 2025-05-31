import ccxt
import pandas as pd
import ta
import time
import requests
from datetime import datetime

# === Telegram Bot Config ===

BOT_TOKEN = '7724103910:AAHGjqgh_nmhdJMxDDqrFt1JhMqWq9j9Y9o'
CHAT_ID = '721677346'

def send_telegram_message(text):
    url = f'https://api.telegram.org/bot{7724103910:AAHGjqgh_nmhdJMxDDqrFt1JhMqWq9j9Y9o}/sendMessage'  # yahan BOT_TOKEN variable use karo
    data = {'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}
    try:
        response = requests.post(url, data=data)
        if response.status_code != 200:
            print(f"Telegram send failed: {response.text}")
    except Exception as e:
        print(f"Telegram error: {e}")


# === Exchange & Symbols Config ===
exchange = ccxt.binance({'enableRateLimit': True})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
timeframe = '1h'

# Tracking stats per symbol
stats_dict = {
    sym: {
        'position': None,       # 'long', 'short', or None
        'entry_price': 0.0,
        'total_trades': 0,
        'profitable_trades': 0,
        'cumulative_profit_pct': 0.0,
        'last_signal_time': None
    } for sym in symbols
}

def fetch_ohlcv(symbol):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"Fetch error for {symbol}: {e}")
        return None

def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
    bb_indicator = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb_indicator.bollinger_hband()
    df['bb_middle'] = bb_indicator.bollinger_mavg()
    df['bb_lower'] = bb_indicator.bollinger_lband()
    return df

def check_signals(df, position):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy_signal = False
    sell_signal = False
    exit_signal = False

    # Buy: RSI crosses below 25 and close < lower BB (only if no position)
    if position is None:
        if prev['rsi'] > 25 and last['rsi'] <= 25 and last['close'] < last['bb_lower']:
            buy_signal = True

        # Sell: RSI crosses above 75 and close > upper BB (only if no position)
        elif prev['rsi'] < 75 and last['rsi'] >= 75 and last['close'] > last['bb_upper']:
            sell_signal = True

    # Exit signals: close crosses middle BB depending on position
    if position == 'long' and last['close'] >= last['bb_middle']:
        exit_signal = True
    elif position == 'short' and last['close'] <= last['bb_middle']:
        exit_signal = True

    return buy_signal, sell_signal, exit_signal

def main():
    print("Starting scalping strategy monitoring...")

    while True:
        for symbol in symbols:
            df = fetch_ohlcv(symbol)
            if df is None or len(df) < 20:
                continue

            df = calculate_indicators(df)
            stats = stats_dict[symbol]
            buy, sell, exit_pos = check_signals(df, stats['position'])
            current_close = df.iloc[-1]['close']
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            if buy:
                msg = f"🟢 *BUY* signal on *{symbol}* 📈\n_Time_: {now}"
                send_telegram_message(msg)
                stats['position'] = 'long'
                stats['entry_price'] = current_close
                stats['total_trades'] += 1
                stats['last_signal_time'] = now
                print(f"{symbol}: BUY signal sent.")

            elif sell:
                msg = f"🔴 *SELL* signal on *{symbol}* 📉\n_Time_: {now}"
                send_telegram_message(msg)
                stats['position'] = 'short'
                stats['entry_price'] = current_close
                stats['total_trades'] += 1
                stats['last_signal_time'] = now
                print(f"{symbol}: SELL signal sent.")

            elif exit_pos and stats['position'] is not None:
                # Calculate profit percent
                entry_price = stats['entry_price']
                profit_pct = 0.0
                if stats['position'] == 'long':
                    profit_pct = ((current_close - entry_price) / entry_price) * 100
                elif stats['position'] == 'short':
                    profit_pct = ((entry_price - current_close) / entry_price) * 100

                stats['cumulative_profit_pct'] += profit_pct
                if profit_pct > 0:
                    stats['profitable_trades'] += 1

                profit_emoji = "💰" if profit_pct > 0 else "⚠️"
                msg = (
                    f"⏹️ *EXIT* {stats['position'].upper()} on *{symbol}*\n"
                    f"_Time_: {now}\n"
                    f"{profit_emoji} Profit: *{profit_pct:.2f}%*\n"
                    f"📊 Total Trades: *{stats['total_trades']}*\n"
                    f"✅ Profitable Trades: *{stats['profitable_trades']}*\n"
                    f"📈 Cumulative Profit: *{stats['cumulative_profit_pct']:.2f}%*"
                )
                send_telegram_message(msg)
                print(f"{symbol}: EXIT signal sent. Profit: {profit_pct:.2f}%")
                stats['position'] = None
                stats['entry_price'] = 0.0
                stats['last_signal_time'] = now

            else:
                print(f"{symbol}: No signal at {now}")

        time.sleep(30)  # check every 30 seconds but using 1h timeframe data

if __name__ == "__main__":
    main()
