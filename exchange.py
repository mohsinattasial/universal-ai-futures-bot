"""
exchange.py — Multi-exchange public futures data feeds with synthetic fallback.
"""
from __future__ import annotations

import math
import time
import zlib

import numpy as np
import pandas as pd
import requests
import streamlit as st

from config import BINANCE, BYBIT, COINS, OKX, SIM_BASE, TF_MIN

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "ApexQuant-Terminal/3.0"})


def sim_klines(sym: str, tf: str, n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(zlib.crc32(f"{sym}{tf}".encode()))
    vol = 0.004 * math.sqrt(TF_MIN[tf] / 15)
    ret = rng.normal(0, vol, n) + np.sin(np.linspace(0, 6, n)) * vol * 0.15
    close = np.exp(np.cumsum(ret))
    close *= SIM_BASE[sym] / close[-1]
    close[-1] *= 1 + np.random.default_rng(int(time.time() // 2)).normal(0, vol * 0.1)
    opn = np.r_[close[0], close[:-1]]
    high = np.maximum(opn, close) * (1 + np.abs(rng.normal(0, vol * 0.4, n)))
    low = np.minimum(opn, close) * (1 - np.abs(rng.normal(0, vol * 0.4, n)))
    t = pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("min"), periods=n, freq=f"{TF_MIN[tf]}min")
    return pd.DataFrame({"t": t, "o": opn, "h": high, "l": low, "c": close, "v": rng.uniform(80, 650, n)})


@st.cache_data(ttl=4, show_spinner=False)
def get_klines(sym: str, tf: str) -> tuple[pd.DataFrame, bool, str]:
    """Fetches live perpetual candles (Binance -> Bybit -> Simulated fallback)."""
    try:
        r = HTTP.get(
            f"{BINANCE}/fapi/v1/klines",
            params={"symbol": f"{sym}USDT", "interval": tf, "limit": 250},
            timeout=3.2,
        )
        r.raise_for_status()
        df = pd.DataFrame(r.json()).iloc[:, :6]
        df.columns = ["t", "o", "h", "l", "c", "v"]
        df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
        df["t"] = pd.to_datetime(df["t"], unit="ms", utc=True)
        return df, True, "Binance Perp"
    except Exception:
        pass

    try:
        bybit_tf = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D"}[tf]
        r = HTTP.get(
            f"{BYBIT}/v5/market/kline",
            params={"category": "linear", "symbol": f"{sym}USDT", "interval": bybit_tf, "limit": 250},
            timeout=3.2,
        )
        r.raise_for_status()
        rows = r.json()["result"]["list"][::-1]
        df = pd.DataFrame(rows).iloc[:, :6]
        df.columns = ["t", "o", "h", "l", "c", "v"]
        df[["o", "h", "l", "c", "v"]] = df[["o", "h", "l", "c", "v"]].astype(float)
        df["t"] = pd.to_datetime(df["t"].astype(np.int64), unit="ms", utc=True)
        return df, True, "Bybit Linear"
    except Exception:
        return sim_klines(sym, tf), False, "Simulated Feed"


@st.cache_data(ttl=5, show_spinner=False)
def fetch_tickers() -> dict[str, dict]:
    out: dict[str, dict] = {s: {"px": {}, "chg": None} for s in COINS}

    def put(sym, ex, px, chg):
        if sym in out and px:
            out[sym]["px"][ex] = float(px)
            if out[sym]["chg"] is None and chg is not None:
                out[sym]["chg"] = float(chg)

    try:
        for x in HTTP.get(f"{BINANCE}/fapi/v1/ticker/24hr", timeout=3.0).json():
            if x["symbol"].endswith("USDT"):
                put(x["symbol"][:-4], "Binance", x["lastPrice"], x["priceChangePercent"])
    except Exception:
        pass
    try:
        for x in HTTP.get(f"{BYBIT}/v5/market/tickers", params={"category": "linear"}, timeout=3.0).json()["result"]["list"]:
            if x["symbol"].endswith("USDT"):
                put(x["symbol"][:-4], "Bybit", x["lastPrice"], float(x["price24hPcnt"]) * 100)
    except Exception:
        pass
    try:
        for x in HTTP.get(f"{OKX}/api/v5/market/tickers", params={"instType": "SWAP"}, timeout=3.0).json()["data"]:
            if x["instId"].endswith("-USDT-SWAP"):
                put(x["instId"].split("-")[0], "OKX", x["last"], (float(x["last"]) / float(x["open24h"]) - 1) * 100)
    except Exception:
        pass
    return out


@st.cache_data(ttl=20, show_spinner=False)
def get_pings() -> dict[str, int | None]:
    urls = {
        "Binance": f"{BINANCE}/fapi/v1/ping",
        "Bybit": f"{BYBIT}/v5/market/time",
        "OKX": f"{OKX}/api/v5/public/time",
    }
    res = {}
    for name, u in urls.items():
        try:
            t0 = time.perf_counter()
            HTTP.get(u, timeout=2.5).raise_for_status()
            res[name] = int((time.perf_counter() - t0) * 1000)
        except Exception:
            res[name] = None
    return res