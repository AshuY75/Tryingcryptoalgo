import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yfinance as yf
import talib

# Fetch historical data for BTC/USDT
data = yf.download('BTC-USD', start='2024-01-01', end='2025-05-31', interval='1h')

# Calculate Bollinger Bands
data['SMA'] = data['Close'].rolling(window=20).mean()
data['UpperBand'] = data['SMA'] + 2 * data['Close'].rolling(window=20).std()
data['LowerBand'] = data['SMA'] - 2 * data['Close'].rolling(window=20).std()

# Calculate RSI
data['RSI'] = talib.RSI(data['Close'], timeperiod=14)

# Generate signals
data['Signal'] = 0
data.loc[(data['Close'] < data['LowerBand']) & (data['RSI'] < 25), 'Signal'] = 1  # Buy
data.loc[(data['Close'] > data['UpperBand']) & (data['RSI'] > 75), 'Signal'] = -1  # Sell

# Calculate daily returns
data['DailyReturn'] = data['Close'].pct_change()
data['StrategyReturn'] = data['Signal'].shift(1) * data['DailyReturn']

# Calculate cumulative returns
data['CumulativeMarketReturn'] = (1 + data['DailyReturn']).cumprod()
data['CumulativeStrategyReturn'] = (1 + data['StrategyReturn']).cumprod()

# Plot cumulative returns
plt.figure(figsize=(10, 6))
plt.plot(data['CumulativeMarketReturn'], label='Market Return')
plt.plot(data['CumulativeStrategyReturn'], label='Strategy Return')
plt.legend()
plt.title('Cumulative Returns: Market vs. Strategy')
plt.show()

# Print final returns
print(f"Final Market Return: {data['CumulativeMarketReturn'].iloc[-1] - 1:.2%}")
print(f"Final Strategy Return: {data['CumulativeStrategyReturn'].iloc[-1] - 1:.2%}")
