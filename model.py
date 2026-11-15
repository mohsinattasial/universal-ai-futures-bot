"""
model.py — 25-Feature Universal Candlestick Anatomy AI Engine (XGBoost)
Connected directly to ai_trading_model.pkl and the ApexQuant Terminal UI.
"""
from __future__ import annotations

from dataclasses import dataclass
import glob
import os
import shutil

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from xgboost import XGBClassifier

from config import COINS
from exchange import get_klines

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(PROJECT_DIR, "ai_trading_model.pkl")
DOWNLOADS_DIR = os.path.join(os.path.expanduser("~"), "Downloads")

FEATURES = [
    "body_pct", "body_to_range", "upper_wick_ratio", "lower_wick_ratio", "range_pct",
    "ret_1", "ret_2", "ret_3", "ret_5", "ret_10",
    "prev_body_1", "prev_body_2", "prev_upper_wick_1", "prev_lower_wick_1",
    "pos_10_candle", "ema9_dist", "ema21_dist", "ema50_dist", "ema200_dist",
    "rsi", "macd_norm", "macd_hist_norm", "bb_pos", "atr_pct", "vol_ratio",
]


@dataclass
class Signal:
    direction: str
    conf: int
    rsi: float
    macd_hist: float
    atr: float
    price: float
    chg_1c: float
    vol_surge: float
    e9: pd.Series
    e21: pd.Series
    e200: pd.Series
    model_source: str = "25-Feature XGBoost AI"


@dataclass
class Plan:
    entry: float
    sl: float
    tp1: float
    tp2: float
    size: float
    notional: float
    risk: float
    reward: float
    liq: float


def extract_universal_candle_features(df: pd.DataFrame) -> pd.DataFrame:
    """Computes all 25 candlestick micro-structure & momentum features."""
    d = df.copy()
    opn = d["o"].astype(float)
    high = d["h"].astype(float)
    low = d["l"].astype(float)
    close = d["c"].astype(float)
    vol = d["v"].astype(float)

    eps = 1e-9
    total_range = (high - low) + eps

    d["body_pct"] = (close - opn) / (opn + eps)
    d["body_to_range"] = np.abs(close - opn) / total_range
    d["upper_wick_ratio"] = (high - np.maximum(opn, close)) / total_range
    d["lower_wick_ratio"] = (np.minimum(opn, close) - low) / total_range
    d["range_pct"] = (high - low) / (low + eps)

    for lag in [1, 2, 3, 5, 10]:
        d[f"ret_{lag}"] = close.pct_change(lag)

    d["prev_body_1"] = d["body_pct"].shift(1)
    d["prev_body_2"] = d["body_pct"].shift(2)
    d["prev_upper_wick_1"] = d["upper_wick_ratio"].shift(1)
    d["prev_lower_wick_1"] = d["lower_wick_ratio"].shift(1)

    high_10 = high.rolling(10).max()
    low_10 = low.rolling(10).min()
    d["pos_10_candle"] = (close - low_10) / ((high_10 - low_10) + eps)

    d["ema9"] = close.ewm(span=9, adjust=False).mean()
    d["ema21"] = close.ewm(span=21, adjust=False).mean()
    d["ema50"] = close.ewm(span=50, adjust=False).mean()
    d["ema200"] = close.ewm(span=200, adjust=False).mean()

    d["ema9_dist"] = (close - d["ema9"]) / (d["ema9"] + eps)
    d["ema21_dist"] = (close - d["ema21"]) / (d["ema21"] + eps)
    d["ema50_dist"] = (close - d["ema50"]) / (d["ema50"] + eps)
    d["ema200_dist"] = (close - d["ema200"]) / (d["ema200"] + eps)

    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=14).mean()
    d["rsi"] = 100.0 - (100.0 / (1.0 + (gain / (loss + eps))))

    exp1 = close.ewm(span=12, adjust=False).mean()
    exp2 = close.ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    macd_sig = macd.ewm(span=9, adjust=False).mean()
    d["macd_hist_raw"] = macd - macd_sig
    d["macd_norm"] = macd / (close + eps)
    d["macd_hist_norm"] = d["macd_hist_raw"] / (close + eps)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_lower = bb_mid - (2.0 * bb_std)
    d["bb_pos"] = (close - bb_lower) / ((4.0 * bb_std) + eps)

    tr = pd.concat([
        high - low,
        np.abs(high - close.shift()),
        np.abs(low - close.shift()),
    ], axis=1).max(axis=1)
    d["atr"] = tr.rolling(14).mean()
    d["atr_pct"] = d["atr"] / (close + eps)

    vol_ma = vol.rolling(20).mean()
    d["vol_ratio"] = vol / (vol_ma + eps)

    return d


@st.cache_resource(show_spinner=False)
def load_or_train_model() -> tuple[XGBClassifier, str]:
    """Loads pre-trained ai_trading_model.pkl or trains a fresh 25-feature XGBoost model."""
    if not os.path.exists(MODEL_PATH) and os.path.exists(DOWNLOADS_DIR):
        downloaded = glob.glob(os.path.join(DOWNLOADS_DIR, "ai_trading_model*.pkl"))
        if downloaded:
            latest_dl = max(downloaded, key=os.path.getctime)
            try:
                shutil.copy(latest_dl, MODEL_PATH)
            except Exception:
                pass

    if os.path.exists(MODEL_PATH):
        try:
            loaded_model = joblib.load(MODEL_PATH)
            if getattr(loaded_model, "n_features_in_", len(FEATURES)) == len(FEATURES):
                return loaded_model, "Pre-Trained 25-Feature XGBoost (.pkl)"
        except Exception:
            pass

    dfs = []
    for sym in COINS:
        try:
            raw_df, _, _ = get_klines(sym, "1h")
            tdf = extract_universal_candle_features(raw_df)
            tdf["target"] = np.where(tdf["c"].shift(-1) > tdf["c"], 1, 0)
            tdf.replace([np.inf, -np.inf], np.nan, inplace=True)
            tdf.dropna(subset=FEATURES + ["target"], inplace=True)
            if len(tdf) > 30:
                dfs.append(tdf.iloc[:-1])
        except Exception:
            continue

    master = pd.concat(dfs, ignore_index=True)
    new_model = XGBClassifier(
        n_estimators=300,
        learning_rate=0.03,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        tree_method="hist",
        random_state=42,
    )
    new_model.fit(master[FEATURES].astype(np.float32), master["target"].astype(np.int8))
    try:
        joblib.dump(new_model, MODEL_PATH)
    except Exception:
        pass
    return new_model, f"25-Feature XGBoost AI ({len(master):,} candles)"


def analyze(df: pd.DataFrame) -> Signal:
    """Runs the 25-Feature XGBoost model on the latest candle to generate live AI signals."""
    feat_df = extract_universal_candle_features(df)
    clean_df = feat_df.replace([np.inf, -np.inf], np.nan).dropna(subset=FEATURES)

    model, model_source = load_or_train_model()

    if len(clean_df) > 0:
        latest = clean_df.iloc[-1]
        X_live = clean_df.iloc[[-1]][FEATURES].astype(np.float32)
        pred = int(model.predict(X_live)[0])
        prob = model.predict_proba(X_live)[0]
        raw_conf = float(prob[pred] * 100.0)
        conf = int(np.clip(round(raw_conf), 51, 99))
        direction = "LONG" if pred == 1 else "SHORT"
        rsi = float(latest["rsi"])
        macd_hist = float(latest["macd_hist_raw"])
        atr = float(latest["atr"])
        vol_surge = float(latest["vol_ratio"])
        chg_1c = float(latest["ret_1"] * 100.0)
    else:
        latest = feat_df.iloc[-1]
        direction = "LONG" if feat_df["ema9"].iloc[-1] >= feat_df["ema21"].iloc[-1] else "SHORT"
        conf = 60
        rsi = float(latest.get("rsi", 50.0) or 50.0)
        macd_hist = 0.0
        atr = float((df["h"].iloc[-1] - df["l"].iloc[-1]) or 1.0)
        vol_surge = 1.0
        chg_1c = 0.0

    px = float(df["c"].iloc[-1])
    return Signal(
        direction=direction,
        conf=conf,
        rsi=rsi,
        macd_hist=macd_hist,
        atr=max(atr, px * 0.001),
        price=px,
        chg_1c=chg_1c,
        vol_surge=vol_surge,
        e9=feat_df["ema9"],
        e21=feat_df["ema21"],
        e200=feat_df["ema200"],
        model_source=model_source,
    )


def make_plan(s: Signal, capital: float, lev: int) -> Plan:
    k = 1 if s.direction == "LONG" else -1
    sl = s.price - k * 1.5 * s.atr
    tp1 = s.price + k * 2.0 * s.atr
    tp2 = s.price + k * 3.5 * s.atr
    notional = capital * lev
    size = notional / s.price
    return Plan(
        s.price,
        sl,
        tp1,
        tp2,
        size,
        notional,
        abs(s.price - sl) * size,
        abs(tp2 - s.price) * size,
        max(0.0, s.price * (1 - k * 0.9 / lev)),
    )