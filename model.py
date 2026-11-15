"""
model.py — Quantitative signal generation & ATR risk management engine.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


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


def analyze(df: pd.DataFrame) -> Signal:
    c, v = df["c"], df["v"]
    e9, e21, e200 = (c.ewm(span=n, adjust=False).mean() for n in (9, 21, 200))
    tr = pd.concat([df.h - df.l, (df.h - c.shift()).abs(), (df.l - c.shift()).abs()], axis=1).max(axis=1)
    atr = float(tr.ewm(alpha=1 / 14, adjust=False).mean().iloc[-1])

    d = c.diff()
    gain = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = float((100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50).iloc[-1])

    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    macd_hist = float((macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1])

    vol_ma = float(v.rolling(20).mean().iloc[-1] or 1.0)
    vol_surge = float(v.iloc[-1] / vol_ma)
    chg_1c = float((c.iloc[-1] / c.iloc[-2] - 1) * 100) if len(c) > 1 else 0.0

    px, a, b, z = float(c.iloc[-1]), float(e9.iloc[-1]), float(e21.iloc[-1]), float(e200.iloc[-1])
    long = a > b
    aligned = long == (px > z)
    conf = (
        52
        + min(abs(a - b) / max(atr, 1e-9) * 22, 22)
        + (14 if aligned else -6)
        - (10 if (long and rsi > 72) or (not long and rsi < 28) else 0)
        + ((rsi - 50) if long else (50 - rsi)) * 0.2
    )
    return Signal(
        "LONG" if long else "SHORT",
        int(max(54, min(97, conf))),
        rsi,
        macd_hist,
        atr,
        px,
        chg_1c,
        vol_surge,
        e9,
        e21,
        e200,
    )


def make_plan(s: Signal, capital: float, lev: int) -> Plan:
    k = 1 if s.direction == "LONG" else -1
    sl = s.price - k * 1.5 * s.atr
    tp1 = s.price + k * 2.0 * s.atr
    tp2 = s.price + k * 3.2 * s.atr
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