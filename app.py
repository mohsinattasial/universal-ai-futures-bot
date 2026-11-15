"""
app.py — Main entry point connecting config, database, exchange, and 25-feature XGBoost model.
Strict PostgreSQL Authentication enforced.
"""
from __future__ import annotations

import os
import sys
import warnings

warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"

# Smart VS Code Play-Button Bootstrapper
if __name__ == "__main__":
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx() is None:
            import subprocess
            print("⚡ Launching Modular ApexQuant Terminal...")
            subprocess.run([sys.executable, "-m", "streamlit", "run", os.path.abspath(__file__)])
            sys.exit(0)
    except Exception:
        pass

from concurrent.futures import ThreadPoolExecutor
import inspect
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import AMBER, COINS, CSS, CYAN, GREEN, H, RED, SIM_BASE, TFS, VIOLET, fp
from database import register_user, verify_user
from exchange import fetch_tickers, get_klines, get_pings
from model import Plan, Signal, analyze, load_or_train_model, make_plan

st.set_page_config(
    page_title="ApexQuant Terminal · AI Futures Desk",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

STRETCH = (
    {"width": "stretch"}
    if "width" in inspect.signature(st.plotly_chart).parameters
    else {"use_container_width": True}
)


# ─────────────────────────── UI VIEW BUILDERS ───────────────────────────
def render_ticker_tape() -> None:
    tickers = fetch_tickers()
    items_html = ""
    for sym in COINS:
        t = tickers.get(sym, {})
        px_vals = list(t.get("px", {}).values())
        px = float(np.mean(px_vals)) if px_vals else SIM_BASE[sym]
        chg = t.get("chg") if t.get("chg") is not None else 1.42
        cls = "pos" if chg >= 0 else "neg"
        arrow = "▲" if chg >= 0 else "▼"
        items_html += (
            f'<div class="ticker-item">'
            f'<b>{sym}/USDT</b><span>${fp(px)}</span>'
            f'<span class="{cls}">{arrow} {abs(chg):.2f}%</span></div>'
        )
    st.markdown(
        H(f'<div class="ticker-wrap"><div class="ticker-track">{items_html}{items_html}</div></div>'),
        unsafe_allow_html=True,
    )


def signal_html(sym: str, s: Signal, p: Plan, lev: int, live: bool, src_name: str) -> str:
    long = s.direction == "LONG"
    sc = "var(--g)" if long else "var(--r)"
    rsi_cls = "r" if s.rsi > 70 or s.rsi < 30 else "g"
    return H(f"""
    <div class="glass sig-card" style="--sc:{sc};--p:{s.conf}">
      <div class="dir-row">
        <div>
          <small>XGBoost AI Signal · {sym}/USDT</small>
          <h2>{s.direction} {'🚀' if long else '📉'}</h2>
        </div>
        <div class="ring"><span>{s.conf}%</span></div>
      </div>
      <div class="bdg-row">
        <span class="b a">R:R 1 : 2.3</span>
        <span class="b {'r' if lev > 20 else 'c'}">{lev}× Lev</span>
        <span class="b {rsi_cls}">RSI {s.rsi:.1f}</span>
        <span class="b {'g' if live else 'a'}">● {src_name}</span>
      </div>
      <div class="lv-grid num">
        <div><span>Live Entry Price</span><b>${fp(p.entry)}</b></div>
        <div><span>Stop-Loss (1.5× ATR)</span><b class="neg">${fp(p.sl)}</b></div>
        <div><span>Take-Profit 1 (2.0× ATR)</span><b class="pos">${fp(p.tp1)}</b></div>
        <div><span>Take-Profit 2 (3.5× ATR)</span><b class="pos">${fp(p.tp2)}</b></div>
        <div><span>Contract Position Size</span><b>{p.size:,.3f} {sym}</b></div>
        <div><span>Leveraged Notional</span><b class="cy">${p.notional:,.0f}</b></div>
        <div><span>Est. Risk / Reward</span><b><span class="neg">-${p.risk:,.0f}</span> / <span class="pos">+${p.reward:,.0f}</span></b></div>
        <div><span>Est. Liquidation Price</span><b class="amb">${fp(p.liq)}</b></div>
      </div>
    </div>""")


def chart(df: pd.DataFrame, s: Signal, p: Plan, sym: str, tf: str) -> go.Figure:
    n = 115
    d = df.tail(n)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.78, 0.22])

    x0, x1 = d.t.iloc[0], d.t.iloc[-1]
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=p.entry, y1=p.tp2, fillcolor="rgba(16, 185, 129, 0.06)", line=dict(width=0), row=1, col=1)
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=p.entry, y1=p.sl, fillcolor="rgba(244, 63, 94, 0.06)", line=dict(width=0), row=1, col=1)

    fig.add_trace(
        go.Candlestick(
            x=d.t, open=d.o, high=d.h, low=d.l, close=d.c, name=sym,
            increasing=dict(line=dict(color=GREEN, width=1.2), fillcolor="rgba(16, 185, 129, 0.82)"),
            decreasing=dict(line=dict(color=RED, width=1.2), fillcolor="rgba(244, 63, 94, 0.82)"),
        ),
        row=1, col=1,
    )

    for ser, name, col, w in ((s.e9, "EMA 9", CYAN, 1.3), (s.e21, "EMA 21", AMBER, 1.3), (s.e200, "EMA 200", VIOLET, 1.9)):
        fig.add_trace(go.Scatter(x=d.t, y=ser.tail(n), name=name, mode="lines", line=dict(color=col, width=w), hoverinfo="skip"), row=1, col=1)

    for y, col, txt in ((p.sl, RED, f"SL  ${fp(p.sl)}"), (p.tp1, GREEN, f"TP1 ${fp(p.tp1)}"), (p.tp2, GREEN, f"TP2 ${fp(p.tp2)}"), (p.entry, CYAN, f"LIVE ${fp(p.entry)}")):
        fig.add_hline(y=y, line=dict(color=col, width=1.1, dash="dash"), annotation_text=txt, annotation_position="top right", annotation_font=dict(color=col, size=10, family="JetBrains Mono"), row=1, col=1)

    vol_colors = ["rgba(16, 185, 129, 0.55)" if c >= o else "rgba(244, 63, 94, 0.55)" for c, o in zip(d.c, d.o)]
    fig.add_trace(go.Bar(x=d.t, y=d.v, name="Volume", marker_color=vol_colors, hoverinfo="x+y"), row=2, col=1)

    lo, hi = min(d.l.min(), p.sl, p.tp2), max(d.h.max(), p.sl, p.tp2)
    pad = (hi - lo) * 0.045
    fig.update_layout(
        height=535, margin=dict(l=6, r=64, t=8, b=18), showlegend=True, dragmode="pan", hovermode="x unified",
        legend=dict(orientation="h", y=1.04, x=0, font=dict(size=11)),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", family="JetBrains Mono, monospace", size=11),
        xaxis=dict(rangeslider=dict(visible=False), gridcolor="rgba(148, 163, 184, 0.06)", showspikes=True, spikemode="across", spikecolor="#38bdf8", spikethickness=1),
        xaxis2=dict(gridcolor="rgba(148, 163, 184, 0.06)"),
        yaxis=dict(side="right", gridcolor="rgba(148, 163, 184, 0.06)", zeroline=False, range=[lo - pad, hi + pad]),
        yaxis2=dict(side="right", showticklabels=False),
        uirevision=f"{sym}{tf}",
    )
    return fig


def anatomy_html(df: pd.DataFrame, s: Signal, sym: str) -> str:
    x = df.iloc[-1]
    rg = max(x.h - x.l, 1e-12)
    body, up, lo = abs(x.c - x.o), x.h - max(x.o, x.c), min(x.o, x.c) - x.l
    br, bull = body / rg, x.c >= x.o

    if br < 0.1:
        pat = "Doji Indecision"
    elif br > 0.82:
        pat = "Bullish Marubozu" if bull else "Bearish Marubozu"
    elif lo > body * 2 and up < body:
        pat = "Pinbar Hammer"
    elif up > body * 2 and lo < body:
        pat = "Shooting Star"
    else:
        pat = "Bullish Impulse" if bull else "Bearish Impulse"

    col = GREEN if bull else RED
    y = lambda v: 8 + (x.h - v) / rg * 84
    top, bh = min(y(x.o), y(x.c)), max(abs(y(x.o) - y(x.c)), 3)
    cell = lambda a, b, c="": f'<div class="cell"><small>{a}</small><b class="{c}">{b}</b></div>'

    glyph = (
        f'<div class="glyph"><svg width="135" height="115" viewBox="0 0 130 104">'
        f'<line x1="48" x2="48" y1="{y(x.h)}" y2="{y(x.l)}" stroke="{col}" stroke-width="2.2" stroke-linecap="round"/>'
        f'<rect x="33" y="{top}" width="30" height="{bh}" rx="3" fill="{col}" fill-opacity=".82" stroke="{col}" stroke-width="1.2"/>'
        f'<circle cx="48" cy="{y(x.c)}" r="3.5" fill="#fff"/>'
        f'<g font-family="JetBrains Mono,monospace" font-size="9.5" fill="#94a3b8">'
        f'<text x="72" y="{y(x.h) + 3}">H {fp(x.h)}</text><text x="72" y="{y(x.l) + 3}">L {fp(x.l)}</text>'
        f'<text x="72" y="{y(x.c) + (11 if abs(y(x.o) - y(x.c)) < 10 else 3)}" fill="{col}" font-weight="700">C {fp(x.c)}</text>'
        f'</g></svg></div>'
    )
    cells = "".join([
        cell("Open Price", f"${fp(x.o)}"), cell("Candle High", f"${fp(x.h)}", "pos"),
        cell("Candle Low", f"${fp(x.l)}", "neg"), cell("Live Close", f"${fp(x.c)}", "pos" if bull else "neg"),
        cell("Body / Range", f"{br * 100:.1f}%"), cell("Upper Wick", f"{up / rg * 100:.1f}%"),
        cell("Lower Wick", f"{lo / rg * 100:.1f}%"), cell("True Range", f"${fp(rg)}", "cy"),
        cell("ATR (14) Vol", f"${fp(s.atr)}", "amb"), cell("Volume Surge", f"{s.vol_surge:.2f}× MA", "pos" if s.vol_surge > 1.2 else ""),
        cell("MACD Hist", f"{s.macd_hist:+.4f}", "pos" if s.macd_hist >= 0 else "neg"), cell("AI Pattern", pat, "amb"),
    ])
    return H(
        f'<div class="glass" style="margin-top:14px">'
        f'<div class="ttl"><span>🕯️ Live Candlestick Micro-Structure (25-Feature Input)</span><span class="b c">{pat}</span></div>'
        f'<div class="ag">{glyph}{cells}</div></div>'
    )


def render_terminal(sym: str, tf: str, capital: float, lev: int) -> None:
    df, live, src_name = get_klines(sym, tf)
    s = analyze(df)
    p = make_plan(s, capital, lev)

    chg_cls = "pos" if s.chg_1c >= 0 else "neg"
    trend_str = "BULLISH ABOVE EMA200" if s.price >= float(s.e200.iloc[-1]) else "BEARISH BELOW EMA200"
    trend_cls = "pos" if s.price >= float(s.e200.iloc[-1]) else "neg"
    st.markdown(
        H(f"""
        <div class="kpi-strip">
            <div class="kpi-box"><small>{sym}/USDT Perpetual</small><b>${fp(s.price)} <span class="{chg_cls}" style="font-size:13px">{s.chg_1c:+.2f}%</span></b></div>
            <div class="kpi-box"><small>Macro Regime (EMA 200)</small><b class="{trend_cls}" style="font-size:14px">{trend_str}</b></div>
            <div class="kpi-box"><small>ATR (14) Volatility</small><b class="amb">${fp(s.atr)} <span style="font-size:12px;color:#94a3b8">({s.atr / s.price * 100:.2f}%)</span></b></div>
            <div class="kpi-box"><small>Active AI Engine</small><b class="cy" style="font-size:13px">{s.model_source}</b></div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.05, 2.35], gap="medium")
    with left:
        st.markdown(signal_html(sym, s, p, lev, live, src_name), unsafe_allow_html=True)
    with right:
        st.markdown(
            H(f'<div class="glass" style="padding:14px 16px 6px">'
              f'<div class="ttl"><span>📊 {sym}/USDT · {tf} Institutional Chart ({src_name})</span>'
              f'<span class="b c">EMA 9 / 21 / 200 · Shaded ATR Zones</span></div>'),
            unsafe_allow_html=True,
        )
        st.plotly_chart(chart(df, s, p, sym, tf), config={"displayModeBar": False, "scrollZoom": True}, **STRETCH)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(anatomy_html(df, s, sym), unsafe_allow_html=True)


@st.cache_data(ttl=8, show_spinner=False)
def radar_rows() -> list[dict]:
    tickers = fetch_tickers()
    with ThreadPoolExecutor(max_workers=9) as ex:
        data = list(ex.map(lambda k: get_klines(k, "15m"), COINS))
    rows = []
    for sym, (df, _, _) in zip(COINS, data):
        s = analyze(df)
        t = tickers[sym]
        px = float(np.mean(list(t["px"].values()))) if t["px"] else s.price
        chg = t["chg"] if t["chg"] is not None else (s.price / float(df["c"].iloc[-96]) - 1) * 100 if len(df) > 96 else 0.0
        rows.append(
            dict(
                sym=sym, px=px, chg=chg, src=list(t["px"]) or ["Sim"],
                rsi=s.rsi, trend=float(s.e9.iloc[-1] / s.e21.iloc[-1] - 1) * 100,
                sig=s.direction, conf=s.conf,
            )
        )
    return rows


def render_radar() -> None:
    c1, c2, c3 = st.columns([1.2, 1, 1.4])
    sort_by = c1.selectbox("Sort by", ["AI confidence", "24h change", "RSI", "Trend strength", "Pair"])
    side = c2.selectbox("Filter Signal", ["All", "LONG", "SHORT"])
    min_conf = c3.slider("Min AI Confidence (%)", 50, 95, 50)

    key = {"AI confidence": "conf", "24h change": "chg", "RSI": "rsi", "Trend strength": "trend", "Pair": "sym"}[sort_by]
    rows = [r for r in radar_rows() if (side == "All" or r["sig"] == side) and r["conf"] >= min_conf]
    rows.sort(key=lambda r: (abs(r[key]) if key == "trend" else r[key]), reverse=key != "sym")

    body = ""
    for r in rows:
        long = r["sig"] == "LONG"
        rc = RED if r["rsi"] > 70 else GREEN if r["rsi"] < 30 else CYAN
        body += (
            f'<tr>'
            f'<td><div class="pair"><i>{r["sym"][:3]}</i>{r["sym"]}<span style="color:var(--txt-dim);font-weight:400">/USDT</span></div></td>'
            f'<td>${fp(r["px"])}</td>'
            f'<td class="{"pos" if r["chg"] >= 0 else "neg"}">{r["chg"]:+.2f}%</td>'
            f'<td class="src">{"".join(f"<em>{e}</em>" for e in r["src"])}</td>'
            f'<td>{r["rsi"]:.1f}<span class="bar"><i style="width:{min(100, max(0, r["rsi"]))}%;background:{rc}"></i></span></td>'
            f'<td class="{"pos" if r["trend"] >= 0 else "neg"}">{"▲" if r["trend"] >= 0 else "▼"} {abs(r["trend"]):.2f}%</td>'
            f'<td><span class="b {"g" if long else "r"}">{r["sig"]}</span></td>'
            f'<td><span class="b a">{r["conf"]}%</span></td></tr>'
        )
    head = "".join(f"<th>{h}</th>" for h in ["Futures Pair", "Mark Price", "24h Change", "Liquidity Feeds", "RSI (14)", "EMA Spread", "XGBoost Signal", "Confidence"])
    st.markdown(
        H(f'<div class="glass" style="padding:0;overflow:auto"><table class="rd"><thead><tr>{head}</tr></thead>'
          f'<tbody>{body or "<tr><td colspan=8>No pairs match filter criteria.</td></tr>"}</tbody></table></div>'),
        unsafe_allow_html=True,
    )


# ─────────────────────────── STRICT AUTH GATE & SHELL ───────────────────────────
st.session_state.setdefault("authenticated", False)
st.session_state.setdefault("username", "")
st.session_state.setdefault("t0", time.time())

if not st.session_state["authenticated"]:
    render_ticker_tape()
    _, center, _ = st.columns([1, 1.35, 1])
    with center:
        st.markdown(
            H("""
            <div class="auth-hero">
                <div class="logo" style="margin:0 auto 10px">⚡</div>
                <h1 style="font-family:var(--font-head);font-size:28px;margin:0;color:#fff">ApexQuant Terminal</h1>
                <p style="color:var(--txt-muted);font-size:13px;margin:4px 0 0">25-Feature XGBoost AI Futures Desk · PostgreSQL Secured</p>
            </div>
            """),
            unsafe_allow_html=True,
        )

        tab_l, tab_s = st.tabs(["🔐 Login to Terminal", "📝 Create Account"])
        with tab_l:
            u_in = st.text_input("Username", placeholder="Enter your username", key="login_user")
            p_in = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")
            if st.button("🔐 Login to Terminal", type="primary", use_container_width=True):
                if not u_in.strip() or not p_in:
                    st.warning("Username aur Password dono darj karein.")
                else:
                    ok, msg = verify_user(u_in.strip(), p_in)
                    if ok:
                        st.session_state["authenticated"] = True
                        st.session_state["username"] = u_in.strip()
                        st.session_state["t0"] = time.time()
                        st.rerun()
                    else:
                        st.error(msg)
        with tab_s:
            su_in = st.text_input("Choose Username", placeholder="Min 3 characters", key="sign_user")
            sp_in = st.text_input("Choose Password", type="password", placeholder="Min 4 characters", key="sign_pass")
            if st.button("📝 Create Account", use_container_width=True):
                if len(su_in.strip()) < 3 or len(sp_in) < 4:
                    st.warning("Username kam az kam 3 aur Password 4 characters ka hona chahiye.")
                else:
                    ok, msg = register_user(su_in.strip(), sp_in)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
    st.stop()

with st.sidebar:
    st.markdown(
        H('<div class="brand"><div class="logo">⚡</div><div><div class="brand-title">ApexQuant</div><div class="brand-sub">AI Futures Desk</div></div></div>'),
        unsafe_allow_html=True,
    )
    el = int(time.time() - st.session_state["t0"])
    uname = st.session_state.get("username", "Trader")
    initials = "".join(part[0].upper() for part in uname.split()[:2]) or "AQ"
    st.markdown(
        H(f'<div class="glass user-card"><div class="av">{initials}</div>'
          f'<div><b style="font-size:13.5px;color:#fff">{uname}</b>'
          f'<div style="color:var(--txt-dim);font-size:11.5px">Quant Desk · <span class="num">{el // 3600:02d}:{el // 60 % 60:02d}:{el % 60:02d}</span></div></div></div>'),
        unsafe_allow_html=True,
    )

    _, active_model_label = load_or_train_model()
    st.markdown(
        H(f'<div class="ex-row" style="margin-top:8px;border-color:rgba(16,185,129,.35)">'
          f'<span><i class="dot" style="background:#10b981;box-shadow:0 0 8px #10b981"></i>AI Model</span>'
          f'<span class="num" style="color:#10b981;font-size:11px;font-weight:600">{active_model_label}</span></div>'),
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-label">Exchange Telemetry</div>', unsafe_allow_html=True)
    pings = get_pings()
    badges = ""
    for name, ms in pings.items():
        col = "#64748b" if ms is None else GREEN if ms < 120 else AMBER if ms < 280 else RED
        badges += (
            f'<div class="ex-row"><span><i class="dot" style="background:{col};box-shadow:0 0 8px {col}"></i>{name}</span>'
            f'<span class="num" style="color:{col};font-weight:600">{"sim-mode" if ms is None else f"{ms} ms"}</span></div>'
        )
    st.markdown(H(badges), unsafe_allow_html=True)

    st.markdown('<div class="sec-label">Perpetual Contract</div>', unsafe_allow_html=True)
    sym = st.radio("Coin", COINS, horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="sec-label">Chart Horizon</div>', unsafe_allow_html=True)
    tf = st.radio("Timeframe", TFS, index=2, horizontal=True, label_visibility="collapsed")

    st.markdown('<div class="sec-label">Risk & Leverage Engine</div>', unsafe_allow_html=True)
    capital = st.slider("Margin Capital (USDT)", 500, 100_000, 10_000, 500, format="$%d")
    lev = st.slider("Futures Leverage", 1, 50, 10, format="%d×")
    auto = st.toggle("⚡ Auto-Refresh (Every 5s)", value=True)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚪 Lock Terminal / Logout", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["username"] = ""
        st.rerun()

render_ticker_tape()
live_fragment = st.fragment(run_every=5 if auto else None)

tab1, tab2 = st.tabs(["🎯 Deep-Dive Quant Terminal", "🌐 Multi-Exchange Market Radar"])
with tab1:
    live_fragment(render_terminal)(sym, tf, capital, lev)
with tab2:
    live_fragment(render_radar)()