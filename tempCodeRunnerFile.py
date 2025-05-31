for symbol in SYMBOLS:
        print(f"[FETCH] Fetching OHLCV for {symbol}")
        df = fetch_ohlcv(symbol, interval='1h', limit=100)
        if df is None:
            continue