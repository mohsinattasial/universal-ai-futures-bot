"""
config.py — Global constants, color tokens, formatting helpers, and Designer CSS.
"""
from __future__ import annotations

COINS = ["BTC", "ETH", "SOL", "BNB", "XRP", "DOGE", "ADA", "AVAX", "LINK"]
TFS = ["1m", "5m", "15m", "1h", "4h", "1d"]
TF_MIN = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}

SIM_BASE = {
    "BTC": 97250.0, "ETH": 3480.0, "SOL": 212.0, "BNB": 690.0, "XRP": 2.34,
    "DOGE": 0.41, "ADA": 0.98, "AVAX": 41.5, "LINK": 24.8
}

GREEN, RED, CYAN, AMBER, VIOLET = "#10b981", "#f43f5e", "#38bdf8", "#f59e0b", "#a855f7"
BINANCE, BYBIT, OKX = "https://fapi.binance.com", "https://api.bybit.com", "https://www.okx.com"


def H(s: str) -> str:
    """Minify multiline HTML to a single line so Streamlit Markdown never renders code blocks."""
    return "".join(line.strip() for line in s.strip().splitlines())


def fp(p: float) -> str:
    """Format crypto prices dynamically based on magnitude."""
    return f"{p:,.2f}" if p >= 100 else f"{p:.3f}" if p >= 1 else f"{p:.4f}"


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    --bg-base: #030712;
    --bg-card: rgba(20, 30, 52, 0.62);
    --border-subtle: rgba(148, 163, 184, 0.14);
    --txt-main: #f8fafc;
    --txt-muted: #94a3b8;
    --txt-dim: #64748b;
    --g: #10b981;
    --r: #f43f5e;
    --c: #38bdf8;
    --a: #f59e0b;
    --v: #a855f7;
    --font-head: 'Outfit', sans-serif;
    --font-body: 'Plus Jakarta Sans', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}

html, body, .stApp, [class*="css"] {
    font-family: var(--font-body);
    color: var(--txt-main);
}
.stApp {
    background-color: var(--bg-base);
    background-image:
        radial-gradient(circle at 12% 8%, rgba(56, 189, 248, 0.12), transparent 42%),
        radial-gradient(circle at 88% 15%, rgba(168, 85, 247, 0.10), transparent 40%),
        radial-gradient(circle at 50% 95%, rgba(16, 185, 129, 0.08), transparent 45%),
        linear-gradient(rgba(148, 163, 184, 0.025) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, 0.025) 1px, transparent 1px);
    background-size: 100% 100%, 100% 100%, 100% 100%, 36px 36px, 36px 36px;
}
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding: 0.8rem 1.6rem 2rem !important; max-width: 100% !important; }

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(6, 11, 25, 0.92), rgba(3, 7, 18, 0.96)) !important;
    backdrop-filter: blur(20px);
    border-right: 1px solid var(--border-subtle);
}

@keyframes tickerMove {
    0% { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
@keyframes pulseGlow {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.55; transform: scale(1.12); }
}
@keyframes floatIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes shimmerBorder {
    0%, 100% { border-color: rgba(56, 189, 248, 0.25); }
    50% { border-color: rgba(16, 185, 129, 0.45); }
}

.ticker-wrap {
    width: 100%; overflow: hidden;
    background: rgba(9, 14, 28, 0.82);
    border: 1px solid var(--border-subtle);
    border-radius: 12px; padding: 8px 0; margin-bottom: 16px;
    backdrop-filter: blur(12px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}
.ticker-track { display: flex; width: max-content; animation: tickerMove 34s linear infinite; }
.ticker-wrap:hover .ticker-track { animation-play-state: paused; }
.ticker-item {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 0 22px; border-right: 1px solid rgba(148, 163, 184, 0.12);
    font-family: var(--font-mono); font-size: 12.5px;
}
.ticker-item b { font-family: var(--font-head); color: #fff; font-size: 13px; letter-spacing: 0.4px; }

.glass {
    background: var(--bg-card);
    border: 1px solid var(--border-subtle);
    border-radius: 16px; backdrop-filter: blur(16px);
    padding: 16px 18px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.05);
    transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), border-color 0.22s ease, box-shadow 0.22s ease;
    animation: floatIn 0.35s ease-out;
}
.glass:hover {
    border-color: rgba(56, 189, 248, 0.32);
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45), 0 0 20px rgba(56, 189, 248, 0.08);
}

.brand { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; padding: 6px 4px; }
.logo {
    width: 40px; height: 40px; border-radius: 11px;
    background: linear-gradient(135deg, #38bdf8 0%, #10b981 55%, #6366f1 100%);
    display: grid; place-items: center;
    color: #030712; font-family: var(--font-head); font-weight: 800; font-size: 19px;
    box-shadow: 0 0 24px rgba(56, 189, 248, 0.5);
}
.brand-title { font-family: var(--font-head); font-weight: 700; font-size: 17px; color: #fff; line-height: 1.1; }
.brand-sub { color: var(--c); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1.2px; }

.user-card { display: flex; gap: 12px; align-items: center; padding: 12px 14px; }
.av {
    width: 36px; height: 36px; border-radius: 10px;
    background: linear-gradient(135deg, #6366f1, #38bdf8);
    display: grid; place-items: center; font-family: var(--font-head); font-weight: 700; font-size: 13px; color: #fff;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
}
.sec-label {
    font-family: var(--font-head); font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 1.3px; color: var(--txt-dim);
    margin: 16px 0 8px;
}

.ex-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 11px; border: 1px solid var(--border-subtle);
    border-radius: 10px; margin-bottom: 6px;
    background: rgba(10, 16, 30, 0.65); font-size: 12.5px;
}
.dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block; margin-right: 8px;
    animation: pulseGlow 2s infinite ease-in-out;
}

.num { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.b {
    font-family: var(--font-mono); font-size: 11px; padding: 3.5px 10px;
    border-radius: 999px; border: 1px solid; font-weight: 600;
    display: inline-flex; align-items: center; gap: 4px;
}
.b.a { color: var(--a); border-color: rgba(245, 158, 11, 0.4); background: rgba(245, 158, 11, 0.12); }
.b.c { color: var(--c); border-color: rgba(56, 189, 248, 0.4); background: rgba(56, 189, 248, 0.12); }
.b.g { color: var(--g); border-color: rgba(16, 185, 129, 0.45); background: rgba(16, 185, 129, 0.14); }
.b.r { color: var(--r); border-color: rgba(244, 63, 94, 0.45); background: rgba(244, 63, 94, 0.14); }

.sig-card {
    border: 1px solid color-mix(in srgb, var(--sc) 50%, transparent);
    box-shadow: 0 0 45px color-mix(in srgb, var(--sc) 16%, transparent),
                inset 0 0 32px color-mix(in srgb, var(--sc) 8%, transparent);
}
.dir-row { display: flex; justify-content: space-between; align-items: center; }
.dir-row h2 {
    margin: 2px 0 0; font-family: var(--font-head);
    font-size: 40px; line-height: 1; font-weight: 800; letter-spacing: 1.5px;
    color: var(--sc); text-shadow: 0 0 26px color-mix(in srgb, var(--sc) 65%, transparent);
}
.dir-row small { color: var(--txt-muted); font-size: 11.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.9px; }

.ring {
    width: 80px; height: 80px; border-radius: 50%;
    background: conic-gradient(var(--sc) calc(var(--p) * 1%), rgba(148, 163, 184, 0.12) 0);
    display: grid; place-items: center; position: relative;
    box-shadow: 0 0 24px color-mix(in srgb, var(--sc) 28%, transparent);
}
.ring::before { content: ""; position: absolute; inset: 7px; border-radius: 50%; background: #0b1325; }
.ring span { position: relative; font-family: var(--font-mono); font-weight: 700; font-size: 17px; color: #fff; }

.bdg-row { display: flex; gap: 6px; flex-wrap: wrap; margin: 14px 0; }
.lv-grid {
    display: grid; gap: 1px; background: rgba(148, 163, 184, 0.12);
    border-radius: 12px; overflow: hidden; border: 1px solid var(--border-subtle);
}
.lv-grid div {
    display: flex; justify-content: space-between; align-items: center;
    padding: 9.5px 13px; background: rgba(11, 18, 34, 0.92); font-size: 13px;
}
.lv-grid div:hover { background: rgba(20, 32, 58, 0.95); }
.lv-grid span { color: var(--txt-muted); font-size: 12.5px; }

.pos { color: var(--g) !important; }
.neg { color: var(--r) !important; }
.amb { color: var(--a) !important; }
.cy  { color: var(--c) !important; }

.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
.kpi-box {
    background: rgba(15, 23, 42, 0.62); border: 1px solid var(--border-subtle);
    border-radius: 13px; padding: 11px 15px; backdrop-filter: blur(12px);
    transition: transform 0.18s ease, border-color 0.18s ease;
}
.kpi-box:hover { transform: translateY(-2px); border-color: rgba(56, 189, 248, 0.35); }
.kpi-box small { color: var(--txt-dim); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.8px; display: block; }
.kpi-box b { font-family: var(--font-mono); font-size: 18px; font-weight: 700; color: #fff; }

.ag { display: grid; grid-template-columns: 165px repeat(auto-fill, minmax(135px, 1fr)); gap: 10px; }
.cell {
    padding: 11px 13px; border: 1px solid var(--border-subtle);
    border-radius: 11px; background: rgba(11, 18, 34, 0.65);
    transition: border-color 0.18s, transform 0.18s;
}
.cell:hover { border-color: rgba(56, 189, 248, 0.45); transform: translateY(-2px); }
.cell small { color: var(--txt-dim); font-size: 11px; font-weight: 600; text-transform: uppercase; display: block; margin-bottom: 3px; }
.cell b { font-family: var(--font-mono); font-size: 14px; font-weight: 600; }
.glyph {
    grid-row: span 2; border: 1px solid var(--border-subtle);
    border-radius: 12px; background: radial-gradient(circle at center, rgba(30, 41, 59, 0.65), rgba(11, 18, 34, 0.85));
    display: grid; place-items: center; padding: 6px;
}
.ttl {
    display: flex; justify-content: space-between; align-items: center;
    font-family: var(--font-head); font-weight: 600; font-size: 15px; margin-bottom: 10px;
}

table.rd { width: 100%; border-collapse: collapse; font-family: var(--font-mono); font-size: 13px; }
.rd th {
    background: rgba(11, 18, 34, 0.95); color: var(--txt-muted);
    text-align: right; padding: 12px 15px; border-bottom: 1px solid var(--border-subtle);
    font-family: var(--font-head); font-weight: 600; font-size: 12px; text-transform: uppercase;
}
.rd td {
    padding: 13px 15px; text-align: right;
    border-bottom: 1px solid rgba(148, 163, 184, 0.07); white-space: nowrap;
}
.rd th:first-child, .rd td:first-child { text-align: left; }
.rd tbody tr:hover td { background: rgba(56, 189, 248, 0.07); }
.pair { display: flex; align-items: center; gap: 10px; font-weight: 700; font-family: var(--font-head); font-size: 14px; color: #fff; }
.pair i {
    width: 28px; height: 28px; border-radius: 8px;
    display: grid; place-items: center; font-style: normal; font-size: 11px; font-weight: 700;
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(99, 102, 241, 0.2));
    border: 1px solid rgba(56, 189, 248, 0.3); color: var(--c); font-family: var(--font-mono);
}
.src em {
    font-style: normal; font-size: 10.5px; padding: 2.5px 7px; border-radius: 6px;
    background: rgba(148, 163, 184, 0.12); color: var(--txt-muted);
    margin-left: 4px; font-family: var(--font-body); font-weight: 500;
}
.bar {
    display: inline-block; width: 62px; height: 6px; border-radius: 99px;
    background: rgba(148, 163, 184, 0.15); position: relative;
    margin-left: 8px; vertical-align: middle; overflow: hidden;
}
.bar i { position: absolute; inset: 0 auto 0 0; border-radius: 99px; }

.auth-hero {
    text-align: center; padding: 26px 20px 18px;
    background: radial-gradient(circle at top, rgba(56, 189, 248, 0.16), rgba(15, 23, 42, 0.85));
    border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 18px; margin-bottom: 16px;
    animation: shimmerBorder 4s infinite ease-in-out;
}
</style>
"""