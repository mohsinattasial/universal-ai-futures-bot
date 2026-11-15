import os
import sys
import glob
import shutil
import warnings
import subprocess

warnings.filterwarnings("ignore")

# 1. Auto-Install Missing Packages (xgboost & plotly for interactive candlestick charts)
for pkg in ["xgboost", "plotly"]:
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

# 2. VS Code Play Button (▷) Auto-Bootstrapper
# Agar user seedha 'python main.py' chalaye toh yeh khud 'streamlit run main.py' chala dega
if get_script_run_ctx() is None:
    print("🚀 Launching Universal AI Futures Dashboard in your browser...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
    sys.exit()

import ccxt
import pandas as pd
import numpy as np
import joblib
import plotly.graph_objects as go
from xgboost import XGBClassifier

# --- PAGE CONFIGURATION & DARK GLASSMORPHIC UI ---
st.set_page_config(
    page_title="Universal AI Futures Bot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0b0f19; color: #f8fafc; }
    .signal-box-long {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.18), rgba(6, 78, 59, 0.35));
        border: 1px solid #10b981; border-radius: 14px; padding: 20px; text-align: center;
    }
    .signal-box-short {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.18), rgba(127, 29, 29, 0.35));
        border: 1px solid #ef4444; border-radius: 14px; padding: 20px; text-align: center;
    }
    .metric-card {
        background: rgba(30, 41, 59, 0.65); border: 1px solid rgba(148, 163, 184, 0.15);
        border-radius: 12px; padding: 15px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- PATHS & 25 UNIVERSAL CANDLESTICK FEATURES ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_DIR, 'ai_trading_model.pkl')
DOWNLOADS_DIR = os.path.join(os.path.expanduser('~'), 'Downloads')

FEATURES = [
    'body_pct', 'body_to_range', 'upper_wick_ratio', 'lower_wick_ratio', 'range_pct',
    'ret_1', 'ret_2', 'ret_3', 'ret_5', 'ret_10',
    'prev_body_1', 'prev_body_2', 'prev_upper_wick_1', 'prev_lower_wick_1',
    'pos_10_candle', 'ema9_dist', 'ema21_dist', 'ema50_dist', 'ema200_dist',
    'rsi', 'macd_norm', 'macd_hist_norm', 'bb_pos', 'atr_pct', 'vol_ratio'
]

def extract_universal_candle_features(df):
    df = df.copy()
    eps = 1e-9
    total_range = (df['high'] - df['low']) + eps
    df['body_pct'] = (df['close'] - df['open']) / (df['open'] + eps)
    df['body_to_range'] = np.abs(df['close'] - df['open']) / total_range
    df['upper_wick_ratio'] = (df['high'] - np.maximum(df['open'], df['close'])) / total_range
    df['lower_wick_ratio'] = (np.minimum(df['open'], df['close']) - df['low']) / total_range
    df['range_pct'] = (df['high'] - df['low']) / (df['low'] + eps)
    
    for lag in [1, 2, 3, 5, 10]:
        df[f'ret_{lag}'] = df['close'].pct_change(lag)
    df['prev_body_1'] = df['body_pct'].shift(1)
    df['prev_body_2'] = df['body_pct'].shift(2)
    df['prev_upper_wick_1'] = df['upper_wick_ratio'].shift(1)
    df['prev_lower_wick_1'] = df['lower_wick_ratio'].shift(1)
    
    high_10 = df['high'].rolling(10).max()
    low_10 = df['low'].rolling(10).min()
    df['pos_10_candle'] = (df['close'] - low_10) / ((high_10 - low_10) + eps)
    
    df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    df['ema9_dist'] = (df['close'] - df['ema9']) / (df['ema9'] + eps)
    df['ema21_dist'] = (df['close'] - df['ema21']) / (df['ema21'] + eps)
    df['ema50_dist'] = (df['close'] - df['ema50']) / (df['ema50'] + eps)
    df['ema200_dist'] = (df['close'] - df['ema200']) / (df['ema200'] + eps)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['rsi'] = 100 - (100 / (1 + (gain / (loss + eps))))
    
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    macd_sig = macd.ewm(span=9, adjust=False).mean()
    df['macd_norm'] = macd / (df['close'] + eps)
    df['macd_hist_norm'] = (macd - macd_sig) / (df['close'] + eps)
    
    bb_mid = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = bb_mid + (2 * bb_std)
    df['bb_lower'] = bb_mid - (2 * bb_std)
    df['bb_pos'] = (df['close'] - df['bb_lower']) / ((4 * bb_std) + eps)
    
    tr = pd.concat([
        df['high'] - df['low'],
        np.abs(df['high'] - df['close'].shift()),
        np.abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['atr'] = tr.rolling(14).mean()
    df['atr_pct'] = df['atr'] / (df['close'] + eps)
    
    vol_ma = df['volume'].rolling(20).mean()
    df['vol_ratio'] = df['volume'] / (vol_ma + eps)
    return df

@st.cache_resource
def get_exchange():
    return ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })

@st.cache_resource
def load_or_train_model():
    exchange = get_exchange()
    # Check Downloads folder for Kaggle trained model
    if not os.path.exists(MODEL_PATH):
        downloaded = glob.glob(os.path.join(DOWNLOADS_DIR, 'ai_trading_model*.pkl'))
        if downloaded:
            latest_dl = max(downloaded, key=os.path.getctime)
            shutil.copy(latest_dl, MODEL_PATH)

    if os.path.exists(MODEL_PATH):
        try:
            loaded_model = joblib.load(MODEL_PATH)
            if getattr(loaded_model, "n_features_in_", len(FEATURES)) == len(FEATURES):
                return loaded_model, "Kaggle / Saved Universal Model"
        except Exception:
            pass

    # Auto-train fallback if file is missing or outdated
    train_coins = ['ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'BTC/USDT']
    dfs = []
    for sym in train_coins:
        try:
            ohlcv = exchange.fetch_ohlcv(sym, timeframe='1d', limit=1000)
            tdf = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            tdf = extract_universal_candle_features(tdf)
            tdf['target'] = np.where(tdf['close'].shift(-1) > tdf['close'], 1, 0)
            tdf.replace([np.inf, -np.inf], np.nan, inplace=True)
            tdf.dropna(subset=FEATURES + ['target'], inplace=True)
            dfs.append(tdf.iloc[:-1])
        except Exception:
            continue
    master = pd.concat(dfs, ignore_index=True)
    new_model = XGBClassifier(
        n_estimators=300, learning_rate=0.03, max_depth=6,
        subsample=0.8, colsample_bytree=0.8, tree_method='hist', random_state=42
    )
    new_model.fit(master[FEATURES].astype(np.float32), master['target'].astype(np.int8))
    joblib.dump(new_model, MODEL_PATH)
    return new_model, f"Auto-Trained Multi-Coin Model ({len(master):,} candles)"

def fetch_coin_analysis(symbol, timeframe):
    exchange = get_exchange()
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=250)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = extract_universal_candle_features(df)
    df.dropna(subset=FEATURES, inplace=True)
    return df

# --- SIDEBAR CONTROLS ---
st.sidebar.title("⚡ AI Futures Terminal")
with st.spinner("Loading Universal Candlestick AI Model..."):
    model, model_source = load_or_train_model()
st.sidebar.success(f"🧠 Model Active:\n{model_source}")

COINS_LIST = [
    'SOL/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT',
    'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'DOT/USDT', 'LTC/USDT', 'BTC/USDT'
]
selected_coin = st.sidebar.selectbox("🪙 Select Futures Pair", COINS_LIST, index=0)
custom_coin = st.sidebar.text_input("Or Type Any Pair (e.g. SUI/USDT)", "")
active_coin = custom_coin.strip().upper() if custom_coin.strip() else selected_coin

timeframe = st.sidebar.selectbox("⏱️ Timeframe", ['15m', '1h', '4h', '1d'], index=1)

st.sidebar.markdown("---")
st.sidebar.subheader("🛡️ Risk Management")
capital = st.sidebar.number_input("Trading Capital ($)", min_value=10.0, value=500.0, step=50.0)
leverage = st.sidebar.slider("Leverage (x)", min_value=1, max_value=25, value=5)
risk_pct = st.sidebar.slider("Risk Per Trade (%)", min_value=0.5, max_value=5.0, value=1.5, step=0.5)

if st.sidebar.button("🔄 Refresh Live Market Data", use_container_width=True):
    st.rerun()

# --- MAIN DASHBOARD HEADER ---
st.title("📈 Universal AI Crypto Futures Terminal")
st.caption("Live Binance Futures Data • 25-Feature Candlestick Anatomy Engine • Automated ATR Stop-Loss & Take-Profit")

tab1, tab2 = st.tabs(["🎯 Live Coin Deep-Dive & Chart", "🌐 Multi-Coin Market Radar (All Coins)"])

# ================= TAB 1: SINGLE COIN DEEP-DIVE =================
with tab1:
    try:
        df = fetch_coin_analysis(active_coin, timeframe)
        latest = df.iloc[-1]
        X_live = df.iloc[[-1]][FEATURES].astype(np.float32)
        
        pred = int(model.predict(X_live)[0])
        prob = model.predict_proba(X_live)[0]
        confidence = float(prob[pred] * 100)
        
        price = float(latest['close'])
        atr = float(latest['atr'])
        rsi = float(latest['rsi'])
        
        # Calculate ATR-based Dynamic Stop Loss & Take Profit
        if pred == 1:
            direction = "BUY / LONG 🚀"
            box_class = "signal-box-long"
            sl_price = price - (1.5 * atr)
            tp1_price = price + (2.0 * atr)
            tp2_price = price + (3.5 * atr)
        else:
            direction = "SELL / SHORT 📉"
            box_class = "signal-box-short"
            sl_price = price + (1.5 * atr)
            tp1_price = price - (2.0 * atr)
            tp2_price = price - (3.5 * atr)
            
        sl_dist_pct = abs(price - sl_price) / price
        risk_amount = capital * (risk_pct / 100.0)
        position_size_usd = (risk_amount / sl_dist_pct) if sl_dist_pct > 0 else capital * leverage
        max_allowed_pos = capital * leverage
        recommended_pos = min(position_size_usd, max_allowed_pos)

        # Top Signal Banner & Key Metrics
        col_sig, col_m1, col_m2, col_m3 = st.columns([1.4, 1, 1, 1])
        
        with col_sig:
            st.markdown(f"""
            <div class="{box_class}">
                <h4 style="margin:0; letter-spacing:1px;">{active_coin} ({timeframe}) AI SIGNAL</h4>
                <h2 style="margin:6px 0; font-size:28px;">{direction}</h2>
                <p style="margin:0; font-size:16px;">Confidence: <b>{confidence:.2f}%</b></p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_m1:
            st.metric("💵 Live Price", f"${price:,.4f}", f"{latest['ret_1']*100:.2f}% (Last Candle)")
            st.metric("📊 RSI (14)", f"{rsi:.1f}", "Overbought" if rsi > 70 else ("Oversold" if rsi < 30 else "Neutral"))
            
        with col_m2:
            st.metric("🎯 Take-Profit 1 (2x ATR)", f"${tp1_price:,.4f}")
            st.metric("🚀 Take-Profit 2 (3.5x ATR)", f"${tp2_price:,.4f}")
            
        with col_m3:
            st.metric("🛑 Stop-Loss (1.5x ATR)", f"${sl_price:,.4f}")
            st.metric("⚖️ Recommended Position", f"${recommended_pos:,.2f}", f"Risk: ${risk_amount:.2f}")

        st.markdown("---")
        
        # Interactive Plotly Candlestick Chart
        plot_df = df.tail(100)
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=plot_df['datetime'],
            open=plot_df['open'], high=plot_df['high'],
            low=plot_df['low'], close=plot_df['close'],
            name="Candles"
        ))
        fig.add_trace(go.Scatter(x=plot_df['datetime'], y=plot_df['ema9'], name="EMA 9", line=dict(color="#38bdf8", width=1.2)))
        fig.add_trace(go.Scatter(x=plot_df['datetime'], y=plot_df['ema21'], name="EMA 21", line=dict(color="#f59e0b", width=1.2)))
        fig.add_trace(go.Scatter(x=plot_df['datetime'], y=plot_df['ema200'], name="EMA 200", line=dict(color="#a855f7", width=1.8)))
        
        # Add Entry, SL, TP horizontal lines
        fig.add_hline(y=price, line_dash="dot", line_color="#e2e8f0", annotation_text="Entry")
        fig.add_hline(y=sl_price, line_dash="dash", line_color="#ef4444", annotation_text="Stop-Loss")
        fig.add_hline(y=tp1_price, line_dash="dash", line_color="#10b981", annotation_text="TP 1")
        
        fig.update_layout(
            title=f"{active_coin} Live Candlestick Anatomy & AI Levels ({timeframe})",
            template="plotly_dark",
            height=520,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=45, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Candle Anatomy Breakdown
        st.subheader("🕯️ Latest Candle Anatomy (What the AI Sees)")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Body Size %", f"{latest['body_pct']*100:.2f}%")
        c2.metric("Upper Wick Ratio", f"{latest['upper_wick_ratio']*100:.1f}%")
        c3.metric("Lower Wick Ratio", f"{latest['lower_wick_ratio']*100:.1f}%")
        c4.metric("10-Candle Breakout Pos", f"{latest['pos_10_candle']*100:.1f}%")
        c5.metric("Volume Surge Ratio", f"{latest['vol_ratio']:.2f}x")

    except Exception as e:
        st.error(f"Error fetching data for {active_coin}: {e}")

# ================= TAB 2: MULTI-COIN MARKET RADAR =================
with tab2:
    st.subheader(f"🌐 All-Coin Live AI Scanner ({timeframe})")
    if st.button("🚀 Scan All Futures Coins Now", type="primary"):
        rows = []
        progress = st.progress(0)
        for idx, sym in enumerate(COINS_LIST):
            try:
                cdf = fetch_coin_analysis(sym, timeframe)
                last = cdf.iloc[-1]
                X_c = cdf.iloc[[-1]][FEATURES].astype(np.float32)
                p = int(model.predict(X_c)[0])
                pr = model.predict_proba(X_c)[0]
                conf_c = float(pr[p] * 100)
                
                c_price = float(last['close'])
                c_atr = float(last['atr'])
                c_sl = c_price - 1.5 * c_atr if p == 1 else c_price + 1.5 * c_atr
                c_tp = c_price + 2.0 * c_atr if p == 1 else c_price - 2.0 * c_atr
                
                rows.append({
                    "Coin": sym,
                    "Live Price ($)": round(c_price, 4),
                    "AI Signal": "🟢 LONG / BUY" if p == 1 else "🔴 SHORT / SELL",
                    "Confidence (%)": round(conf_c, 2),
                    "RSI (14)": round(float(last['rsi']), 1),
                    "Trend (vs EMA200)": "Bullish 📈" if c_price > last['ema200'] else "Bearish 📉",
                    "Stop-Loss ($)": round(c_sl, 4),
                    "Take-Profit ($)": round(c_tp, 4)
                })
            except Exception:
                pass
            progress.progress((idx + 1) / len(COINS_LIST))
            
        scan_df = pd.DataFrame(rows).sort_values(by="Confidence (%)", ascending=False)
        st.dataframe(scan_df, use_container_width=True, hide_index=True)