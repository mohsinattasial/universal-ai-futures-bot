import ccxt
import pandas as pd
import numpy as np
import joblib

# 1. Train kiya hua Advanced AI Model Load Karein
try:
    model = joblib.load('ai_trading_model.pkl')
    print("✅ Advanced AI Model Successfully Loaded!")
except Exception as e:
    print(f"❌ Model load karne mein error: {e}")
    exit()

# 2. Binance Futures Exchange Connection (CCXT)
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def get_live_prediction(symbol='BTC/USDT'):
    print(f"\nFetching live data for {symbol} from Binance...")
    
    # Rolling indicators (jaise Bollinger Bands aur ATR) ke liye thori purani candles bhi chahiye hoti hain (e.g., 50 limit)
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1d', limit=60)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    
    # --- TRAINING SCRIPT JESE EXACT ADVANCED INDICATORS CALCULATE KARNA ---
    
    # 1. EMAs & RSI
    df['ema_fast'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=21, adjust=False).mean()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 2. MACD (Moving Average Convergence Divergence)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = exp1 - exp2
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    
    # 3. Bollinger Bands
    df['bb_middle'] = df['close'].rolling(window=20).mean()
    std = df['close'].rolling(window=20).std()
    df['bb_upper'] = df['bb_middle'] + (std * 2)
    df['bb_lower'] = df['bb_middle'] - (std * 2)
    
    # 4. ATR (Average True Range)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.rolling(window=14).mean()
    
    # NaNs ko drop karna
    df.dropna(inplace=True)
    
    # Sirf latest row (current live candle features) uthana jo model training mein use hue thay[cite: 1]
    latest_row = df.iloc[[-1]]
    features = ['rsi', 'ema_fast', 'ema_slow', 'macd', 'macd_signal', 'bb_upper', 'bb_lower', 'atr', 'volume']
    X_live = latest_row[features]
    
    # Model Prediction
    pred = model.predict(X_live)[0]
    prob = model.predict_proba(X_live)[0]
    confidence = prob[pred] * 100
    
    print(f"Current Price: {latest_row['close'].values[0]}")
    print(f"Calculated RSI: {latest_row['rsi'].values[0]:.2f} | MACD: {latest_row['macd'].values[0]:.4f}")
    
    if pred == 1:
        print(f"🚀 AI SIGNAL: **BUY / LONG** | Confidence: {confidence:.2f}%")
    else:
        print(f"📉 AI SIGNAL: **SELL / SHORT** | Confidence: {confidence:.2f}%")

if __name__ == "__main__":
    get_live_prediction('BTC/USDT')