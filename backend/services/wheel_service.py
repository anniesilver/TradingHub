"""WHEEL backtests: the rules from algo_trading/shared/tradekit, data from TradingHub's DB.

The rules (tradekit/rules/wheel.py) are the very file trade-engine's paper bot runs, and the
engine (tradekit/daily.py) decides once a day at the close, like the bot does at 15:45.
This module only loads data and turns the engine's result into the dashboard's format:

  prices     daily bars from the market_data table (IBKR fallback, as for other strategies)
  IV         SPY: VIX. Other tickers: the stock's own 30-day implied volatility from IB
             (OPTION_IMPLIED_VOLATILITY, stored as "<SYMBOL>_IV"). Days without it use the
             stock's 30-day realized volatility. Or choose realized / a fixed IV outright.
  dividends  Yahoo Finance via the DB cache ("<SYMBOL>_DIV"), paid on shares while held
  options    Black-Scholes at that IV on a made-up weekly chain (tradekit/pricing.py)
"""

from __future__ import annotations

import logging
import math
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ALGO_BASE_PATH = os.environ.get("ALGO_BASE_PATH", "C:/ALGO/algo_trading")
SHARED_PATH = os.path.join(ALGO_BASE_PATH, "shared")
if SHARED_PATH not in sys.path:
    sys.path.insert(0, SHARED_PATH)

REALIZED_WINDOW = 21          # trading days for realized volatility (about a month)
WARMUP_DAYS = 60              # calendar days of extra history loaded for that window
IV_SOURCES = ("market", "realized", "fixed")


SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)


def _market_data_class():
    """TradingHub's own MarketData (services/market_data.py). Loaded by path: the algo_trading
    strategy folders on sys.path have modules with the same name."""
    import importlib.util

    name = "tradinghub_market_data"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(SERVICES_DIR, "market_data.py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name].MarketData


def _tradekit():
    """Import tradekit on demand, with a clear error if algo_trading/shared isn't there."""
    try:
        from tradekit.backtests import BACKTEST_DEFAULTS, wheel_backtest, wheel_summary
        from tradekit.daily import Day
        from tradekit.rules.wheel import Wheel
    except ImportError as e:
        raise RuntimeError(
            f"Could not import tradekit from {SHARED_PATH} ({e}). Pull the latest algo_trading "
            f"(it needs the shared/ folder) or set ALGO_BASE_PATH in backend/services/.env."
        ) from e
    return BACKTEST_DEFAULTS, wheel_backtest, wheel_summary, Day, Wheel


def wheel_params() -> dict:
    """The rules' parameters and the backtest's own settings, with defaults and ranges."""
    defaults, _, _, _, Wheel = _tradekit()
    rules = [{"name": p.name, "type": p.type.__name__, "default": p.default, "min": p.lo, "max": p.hi,
              "choices": list(p.choices) if p.choices else None, "help": p.help} for p in Wheel.PARAMS]
    return {"rules": rules, "backtest": dict(defaults, iv_source="market", fixed_iv=0.25)}


# --- data -------------------------------------------------------------------------------

def realized_vol(close: pd.Series, window: int = REALIZED_WINDOW) -> pd.Series:
    """Annualized volatility of daily log returns over the last `window` days."""
    returns = np.log(close / close.shift(1))
    return returns.rolling(window, min_periods=max(5, window // 2)).std() * math.sqrt(252)


def _load_stock_iv(symbol: str, start: str, end: str) -> pd.Series:
    """The stock's daily 30-day IV from the DB; fetched from IB the first time."""
    from ibkr_data_service import ibkr_service

    name = f"{symbol}_IV"
    df = ibkr_service.get_data_from_db(name, start, end, "1 day")
    stale = df.empty or (pd.to_datetime(end) - df.index.max()).days > 7
    if stale:
        # How far back IB keeps IV history differs by ticker: ask for the most, then less.
        for period in ("20 Y", "10 Y", "5 Y", "2 Y", "1 Y"):
            logger.info(f"Fetching {period} of implied volatility for {symbol} from IBKR")
            if ibkr_service.fetch_and_store_data(name, period, "1 day"):
                break
        df = ibkr_service.get_data_from_db(name, start, end, "1 day")
    if df.empty:
        return pd.Series(dtype=float)
    iv = df["close"].astype(float)
    return iv[iv > 0]


def _load_dividends(symbol: str, start: str, end: str) -> pd.Series:
    """Cash dividend per share by ex-date (Yahoo Finance, cached in the DB as <SYMBOL>_DIV)."""
    from ibkr_data_service import ibkr_service

    name = f"{symbol}_DIV"
    try:
        div = ibkr_service.get_data_from_db(name, start, end, "dividends")
        stale = div.empty or (pd.to_datetime(end) - div.index.max()).days > 100
        if stale:
            import yfinance as yf

            raw = yf.Ticker(symbol).dividends
            if not raw.empty:
                raw.index = raw.index.tz_localize(None)
                rows = [{"date": ts.strftime("%Y%m%d"), "open": 0, "high": 0, "low": 0, "close": float(a), "volume": 0}
                        for ts, a in raw.items() if float(a) > 0]
                ibkr_service.save_data_to_db(name, rows, "dividends")
                div = ibkr_service.get_data_from_db(name, start, end, "dividends")
        if div.empty:
            return pd.Series(dtype=float)
        return div["close"].astype(float)
    except Exception as e:  # dividends are a detail: run without them rather than fail
        logger.warning(f"No dividend data for {symbol} ({e}); dividends will not be paid")
        return pd.Series(dtype=float)


def load_days(symbol: str, start: str, end: str, iv_source: str = "market",
              fixed_iv: float = 0.25) -> Tuple[list, dict]:
    """Daily bars with IV and dividends for [start, end], as tradekit Day objects."""
    MarketData = _market_data_class()
    _, _, _, Day, _ = _tradekit()
    if iv_source not in IV_SOURCES:
        raise ValueError(f"iv_source must be one of {IV_SOURCES}")
    warm_start = (pd.to_datetime(start) - timedelta(days=WARMUP_DAYS)).strftime("%Y-%m-%d")
    df = MarketData(symbol).load_data(warm_start, end)
    df = df[~df.index.duplicated()].sort_index()
    close = df["Close"].astype(float)
    realized = realized_vol(close)

    notes = {"iv_source": iv_source, "iv_name": None, "days_on_realized_vol": 0}
    if iv_source == "fixed":
        iv = pd.Series(float(fixed_iv), index=df.index)
        notes["iv_name"] = f"fixed {fixed_iv:.0%}"
    elif iv_source == "realized":
        iv = realized
        notes["iv_name"] = f"{REALIZED_WINDOW}-day realized volatility"
    elif symbol == "SPY":
        iv = df["VIX"].astype(float) if "VIX" in df.columns else pd.Series(dtype=float)
        notes["iv_name"] = "VIX"
    else:
        iv = _load_stock_iv(symbol, warm_start, end)
        notes["iv_name"] = f"{symbol} 30-day implied volatility (IB)"
    iv = iv.reindex(df.index)
    if iv_source == "market":
        missing = iv.isna() | (iv <= 0)
        iv = iv.where(~missing, realized)
        notes["days_on_realized_vol"] = int(missing[df.index >= pd.to_datetime(start)].sum())

    if symbol == "SPY" and "Dividend" in df.columns:
        dividends = df["Dividend"].astype(float)
    else:
        dividends = _load_dividends(symbol, warm_start, end).reindex(df.index).fillna(0.0)

    days = []
    for ts, row in df.loc[pd.to_datetime(start):pd.to_datetime(end)].iterrows():
        v = iv.get(ts)
        v = None if v is None or pd.isna(v) or v <= 0 else float(v)
        d = float(dividends.get(ts, 0.0) or 0.0)
        days.append(Day(ts.date(), float(row["Open"]), float(row["High"]), float(row["Low"]),
                        float(row["Close"]), v, d))
    if not days:
        raise ValueError(f"No {symbol} price data between {start} and {end}")
    notes["days_without_iv"] = sum(1 for d in days if d.iv is None)
    return days, notes


# --- the run ----------------------------------------------------------------------------

def _rule_params(config: dict, Wheel) -> dict:
    """Pick the rules' parameters out of the dashboard's config (same names as the rules)."""
    out = {}
    for p in Wheel.PARAMS:
        if p.name not in config or config[p.name] in (None, ""):
            continue
        v = config[p.name]
        if p.type is bool:
            v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
        elif p.type is int:
            v = int(float(v))
        elif p.type is float:
            v = float(v)
        else:
            v = str(v).upper() if p.name == "underlying" else str(v)
        out[p.name] = v
    return out


def run_wheel(config: dict, start_dt: datetime, end_dt: datetime, initial_balance: Optional[float] = None) -> dict:
    """Run the Wheel and return {date: {...}} in the dashboard's format, plus __metadata__."""
    defaults, wheel_backtest, wheel_summary, _, Wheel = _tradekit()
    config = dict(config or {})
    if "budget" not in config and initial_balance:
        config["budget"] = initial_balance
    params = _rule_params(config, Wheel)
    rules = Wheel(params)   # validates every value against its range
    p = rules.p
    strike_step = float(config.get("strike_step", defaults["strike_step"]))
    slippage = float(config.get("slippage", defaults["slippage"]))
    rate = float(config.get("risk_free_rate", defaults["risk_free_rate"]))
    iv_source = str(config.get("iv_source", "market"))
    fixed_iv = float(config.get("fixed_iv", 0.25))
    if strike_step <= 0:
        raise ValueError("strike_step must be above 0")

    start, end = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    days, notes = load_days(p.underlying, start, end, iv_source, fixed_iv)
    logger.info(f"WHEEL {p.underlying} {start}..{end}: {len(days)} days, IV {notes}")
    bt = wheel_backtest(days, params, strike_step=strike_step, slippage=slippage, risk_free_rate=rate)
    return to_dashboard(bt, days, p, notes, wheel_summary(bt),
                        {"strike_step": strike_step, "slippage": slippage, "risk_free_rate": rate})


def to_dashboard(bt, days, p, notes: dict, summary: dict, settings: dict) -> Dict[str, dict]:
    # Buy & hold of the same stock with the same money, dividends reinvested at the ex-date close
    shares = p.budget / days[0].close if days[0].close > 0 else 0.0
    bench = {}
    for d in days:
        if d.dividend and d.close > 0:
            shares *= 1 + d.dividend / d.close
        bench[d.date] = shares * d.close

    by_date = {d.date: d for d in days}
    out: Dict[str, dict] = {}
    prev = None
    for r in bt.results:
        day = by_date[r.date]
        daily = lambda name: getattr(r, name) - (getattr(prev, name) if prev else 0.0)
        open_options = 1 if (r.state.get("put_qty") or r.state.get("call_qty")) else 0
        out[r.date.strftime("%Y-%m-%d")] = {
            "Portfolio_Value": round(r.equity, 2),
            "Cash_Balance": round(r.cash, 2),
            "Close": r.close,
            "Open": day.open,
            "High": day.high,
            "Low": day.low,
            "VIX": round(r.iv, 4) if r.iv is not None else 0.0,
            "Margin_Ratio": 0.0,
            "spy_value": round(bench.get(r.date, 0.0), 2),
            "Interest_Paid": 0.0,
            "Premiums_Received": round(daily("premiums"), 2),
            "Dividends_Received": round(daily("dividends"), 2),
            "Commissions_Paid": round(daily("commissions"), 2),
            "Open_Positions": open_options + (1 if r.shares else 0),
            "Closed_Positions": 0,
            "Shares": r.shares,
            "Option_Value": round(r.option_value, 2),
            "Trading_Log": "; ".join(t.text() for t in r.trades),
        }
        prev = r

    final = bt.results[-1]
    summary = dict(summary)
    summary.update({
        "underlying": p.underlying,
        "budget": p.budget,
        "final_value": round(final.equity, 2),
        "benchmark_final_value": round(bench.get(final.date, 0.0), 2),
    })
    out["__metadata__"] = {
        "strategy": "WHEEL",
        "wheel_summary": summary,
        "data_notes": dict(notes, **settings, pricing="Black-Scholes, one IV for all strikes (no skew), "
                                                      "weekly Friday expiries, no bid/ask spread"),
    }
    return out
