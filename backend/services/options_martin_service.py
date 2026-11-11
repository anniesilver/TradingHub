"""OPTIONS_MARTIN backtests: the rules from algo_trading/shared/tradekit, data from TradingHub's DB.

The rules (tradekit/rules/options_martin.py) are the very file trade-engine's paper bot runs.
tradekit/backtests.py rolls the contract like the bot does and walks the intraday bars.
This module only loads data and turns the result into the dashboard's format:

  prices   intraday stock bars of the rules' bar_size (5m by default) from the market_data
           table, downloaded from IB in pieces the first time
  IV       the stock's own 30-day implied volatility at the same bar size ("<SYMBOL>_IV"),
           the number the paper bot reads from IB (tick 106)
  options  Black-Scholes at that IV on a made-up weekly chain (tradekit/pricing.py)
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

ALGO_BASE_PATH = os.environ.get("ALGO_BASE_PATH", "C:/ALGO/algo_trading")
SHARED_PATH = os.path.join(ALGO_BASE_PATH, "shared")
if SHARED_PATH not in sys.path:
    sys.path.insert(0, SHARED_PATH)

SERVICES_DIR = os.path.dirname(os.path.abspath(__file__))
if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)

BAR_INTERVALS = {"1m": "1 min", "5m": "5 mins", "15m": "15 mins", "30m": "30 mins"}
GAP_DAYS = 4  # data starting/ending this many days inside the asked range counts as missing

# The paper bot's settings on the server (2026-11-05), offered as a preset on the page
PAPER_BOT = {
    "underlying": "TSLA", "right": "C", "pick_rule": "otm_pct", "otm_pct": 0.10, "min_days_to_expiry": 0,
    "weekly_only": True, "bar_size": "5m", "cycle": "week", "entry_days": 2, "holiday_max_top_ups": 2,
    "entry_mode": "budget", "round_budget": 1900.0, "entry_share": 0.25, "max_top_ups": 4,
    "take_profit_at": 1.5, "take_profit_of": "cost", "take_profit_needs_high_iv": False,
    "use_iv_filter": True, "iv_entry_max": 0.45, "use_iv_spike_exit": False, "iv_exit_min": 0.55,
    "close_min_before_bell": 10,
}


def _tradekit():
    """Import tradekit on demand, with a clear error if algo_trading/shared isn't up to date."""
    try:
        from tradekit import Bar
        from tradekit.backtests import OPTIONS_MARTIN_DEFAULTS, options_martin_backtest
        from tradekit.rules.options_martin import OptionsMartin
    except ImportError as e:
        raise RuntimeError(
            f"Could not import the OPTIONS_MARTIN backtest from {SHARED_PATH} ({e}). Pull the latest "
            f"algo_trading (it needs shared/tradekit/backtests.py with options_martin_backtest) or set "
            f"ALGO_BASE_PATH in backend/services/.env."
        ) from e
    return Bar, OPTIONS_MARTIN_DEFAULTS, options_martin_backtest, OptionsMartin


def options_martin_params() -> dict:
    """The rules' parameters and the backtest's own settings, with defaults and ranges."""
    _, defaults, _, OptionsMartin = _tradekit()
    rules = [{"name": p.name, "type": p.type.__name__, "default": p.default, "min": p.lo, "max": p.hi,
              "choices": list(p.choices) if p.choices else None, "help": p.help} for p in OptionsMartin.PARAMS]
    return {"rules": rules, "backtest": dict(defaults), "presets": {"paper_bot": PAPER_BOT}}


# --- data -------------------------------------------------------------------------------

def _ensure_intraday(name: str, start: datetime, end: datetime, interval: str) -> pd.DataFrame:
    """Intraday bars for [start, end] from the DB; the missing part is fetched from IB first."""
    from ibkr_data_service import ibkr_service

    q_start, q_end = start.strftime("%Y-%m-%d"), (end + timedelta(days=1)).strftime("%Y-%m-%d")
    df = ibkr_service.get_data_from_db(name, q_start, q_end, interval)
    today = datetime.now()
    want_end = min(end, today - timedelta(days=1))
    missing = []
    if df.empty:
        missing.append((start, end))
    else:
        first, last = df.index.min().to_pydatetime(), df.index.max().to_pydatetime()
        if (first - start).days > GAP_DAYS:
            missing.append((start, first))
        if (want_end - last).days > GAP_DAYS:
            missing.append((last, end))
    for a, b in missing:
        logger.info(f"Fetching {interval} {name} {a:%Y-%m-%d}..{b:%Y-%m-%d} from IB")
        ibkr_service.fetch_intraday_range(name, a, b, interval)
    if missing:
        df = ibkr_service.get_data_from_db(name, q_start, q_end, interval)
    return df


def load_bars(symbol: str, start: datetime, end: datetime, bar_size: str = "5m") -> Tuple[list, Dict[datetime, float], dict]:
    """Stock bars (tradekit Bar, regular hours) and the stock's IV by bar start."""
    Bar, _, _, _ = _tradekit()
    interval = BAR_INTERVALS[bar_size]
    prices = _ensure_intraday(symbol, start, end, interval)
    if prices.empty:
        raise ValueError(f"No {interval} {symbol} bars between {start:%Y-%m-%d} and {end:%Y-%m-%d}")
    ivs = _ensure_intraday(f"{symbol}_IV", start, end, interval)
    prices = prices[~prices.index.duplicated()].sort_index()
    bars = [Bar(ts.to_pydatetime(), float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]),
                float(r["volume"] or 0)) for ts, r in prices.iterrows()]
    iv = {} if ivs.empty else {ts.to_pydatetime(): float(v) for ts, v in ivs["close"].items() if float(v) > 0}
    notes = {
        "bars": len(bars),
        "first_bar": bars[0].time.isoformat(),
        "last_bar": bars[-1].time.isoformat(),
        "iv_name": f"{symbol} 30-day implied volatility (IB), {interval} bars",
        "bars_with_iv": sum(1 for b in bars if b.time in iv),
    }
    return bars, iv, notes


# --- the run ----------------------------------------------------------------------------

def _rule_params(config: dict, OptionsMartin) -> dict:
    """Pick the rules' parameters out of the dashboard's config (same names as the rules)."""
    out = {}
    for p in OptionsMartin.PARAMS:
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
            v = str(v).upper() if p.name in ("underlying", "right") else str(v)
        out[p.name] = v
    return out


def run_options_martin_kit(config: dict, start_dt: datetime, end_dt: datetime,
                           initial_balance: Optional[float] = None) -> dict:
    """Run OPTIONS_MARTIN and return {date: {...}} in the dashboard's format, plus __metadata__."""
    _, defaults, options_martin_backtest, OptionsMartin = _tradekit()
    config = dict(config or {})
    params = _rule_params(config, OptionsMartin)
    p = OptionsMartin(params).p   # validates every value against its range
    settings = {k: config.get(k, v) for k, v in defaults.items()}
    settings = {
        "strike_step": float(settings["strike_step"]),
        "slippage": float(settings["slippage"]),
        "risk_free_rate": float(config.get("risk_free_rate", settings["risk_free_rate"])),
        "fill_mode": str(settings["fill_mode"]),
        "cash": float(settings["cash"] or 0.0),
        "price_iv_mult": float(settings["price_iv_mult"]),
    }
    if settings["strike_step"] <= 0:
        raise ValueError("strike_step must be above 0")
    if not 0.1 <= settings["price_iv_mult"] <= 10:
        raise ValueError("price_iv_mult must be between 0.1 and 10")
    if settings["fill_mode"] not in ("close", "next_open", "cautious"):
        raise ValueError("fill_mode must be close, next_open or cautious")

    bars, iv, notes = load_bars(p.underlying, start_dt, end_dt, p.bar_size)
    logger.info(f"OPTIONS_MARTIN {p.underlying} {start_dt:%Y-%m-%d}..{end_dt:%Y-%m-%d}: {notes}")
    run = options_martin_backtest(bars, iv, params, **settings)
    return to_dashboard(run, p, notes, settings)


def _fmt_time(t) -> Optional[str]:
    return t.strftime("%Y-%m-%d %H:%M") if t else None


def to_dashboard(run, p, notes: dict, settings: dict) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    trades_by_day: Dict[str, list] = {}
    for t in run.trades:
        trades_by_day.setdefault(t["time"].strftime("%Y-%m-%d"), []).append(t)
    first_stock = next((run.days[d]["stock_close"] for d in sorted(run.days) if run.days[d]["stock_close"]), 0)
    start_cash = run.start_cash
    for d in sorted(run.days):
        day = run.days[d]
        key = d.strftime("%Y-%m-%d")
        trades = trades_by_day.get(key, [])
        comm = sum(t["commission"] for t in trades)
        log = [f"{t['time']:%H:%M} {t['side']} {t['qty']} {t['contract']} @ {t['price']:.2f} ({t['reason']})"
               for t in trades] + run.notes.get(d, [])
        stock = day["stock_close"] or 0.0
        out[key] = {
            "Portfolio_Value": round(day["equity"], 2),
            "Cash_Balance": round(day["cash"], 2),
            "Close": stock,
            "Open": stock,
            "High": stock,
            "Low": stock,
            "VIX": round(day["iv"], 4) if day["iv"] is not None else 0.0,
            "Margin_Ratio": 0.0,
            # benchmark: the same money in the stock from the first day
            "spy_value": round(start_cash * stock / first_stock, 2) if first_stock else 0.0,
            "Interest_Paid": 0.0,
            "Premiums_Received": 0.0,
            "Dividends_Received": 0.0,
            "Commissions_Paid": round(comm, 2),
            "Open_Positions": 1 if day["held"] else 0,
            "Closed_Positions": sum(1 for t in trades if t["side"] == "SELL"),
            "Shares": 0,
            "Contracts": day["held"],
            "Option_Value": round(day["held"] * day["option_close"] * 100, 2),
            "Option_Price": day["option_close"],
            "Contract": day["contract"],
            "Trading_Log": "; ".join(log),
        }

    rounds = [{
        "start": _fmt_time(r["start"]), "end": _fmt_time(r["end"]), "contract": r["contract"],
        "loads": r["loads"], "contracts": r["contracts"], "cost": round(r["cost"], 2),
        "exit": r["exit"], "pnl": None if r["pnl"] is None else round(r["pnl"], 2),
    } for r in run.rounds()]
    summary = run.summary()
    summary = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in summary.items()}
    final = out[max(out)] if out else {}
    summary.update({"underlying": p.underlying, "round_budget": p.round_budget,
                    "final_value": final.get("Portfolio_Value"), "benchmark_final_value": final.get("spy_value")})
    out["__metadata__"] = {
        "strategy": "OPTIONS_MARTIN",
        "options_martin_summary": summary,
        "options_martin_rounds": rounds,
        "data_notes": dict(notes, **settings, pricing="Black-Scholes at the stock's 30-day IV, one IV for all "
                                                      "strikes (no skew), weekly Friday expiries, no bid/ask spread"),
    }
    return out
