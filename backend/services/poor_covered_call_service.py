"""POOR_COVERED_CALL backtests on the shared rules (algo_trading/shared/tradekit).

A poor man's covered call: a deep in-the-money call about a year out instead of 100 shares,
and a monthly call sold against it. The rules (tradekit/rules/poor_covered_call.py) are the
very file trade-engine's paper bot runs (on SPY only); the engine (tradekit/daily.py) decides
at the close, one order at a time, like the bot from 15:45. Any ticker backtests: SPY is
priced with VIX, another stock with its own 30-day IV from IB (loaded like WHEEL's), and the
ticker-dependent settings left blank are filled in by tradekit's poor_covered_call_auto.
"""

from __future__ import annotations

import csv
import io
import logging
import urllib.request
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd

from services.spy_power_cashflow_service import _rule_params
from services.wheel_service import SHARED_PATH, load_days

logger = logging.getLogger(__name__)

STRATEGY_ID = "POOR_COVERED_CALL"
TBILL_NAME = "TBILL_3M"   # FRED's DTB3 (3-month T-bill, % a year) in market_data, one bar a day
FRED_DTB3_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"


def load_tbill(end: str) -> Tuple[Optional[Dict], str]:
    """Daily 3-month T-bill rates {date: fraction} for the cash interest and Black-Scholes. Kept in
    the DB as TBILL_3M; downloaded from FRED when missing or more than 10 days old. On any failure:
    (None, note), and the backtest falls back to tradekit's yearly averages."""
    try:
        from ibkr_data_service import ibkr_service

        df = ibkr_service.get_data_from_db(TBILL_NAME, "1990-01-01", end, "1 day")
        if df.empty or (pd.to_datetime(end) - df.index.max()).days > 10:
            logger.info(f"Downloading 3-month T-bill rates from {FRED_DTB3_URL}")
            req = urllib.request.Request(FRED_DTB3_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                text = r.read().decode("utf-8-sig")
            rows = []
            for row in csv.reader(io.StringIO(text)):
                if len(row) < 2 or not row[0][:4].isdigit():
                    continue
                try:
                    v = float(row[1])
                except ValueError:   # "." = no rate that day (holidays)
                    continue
                rows.append({"date": row[0].replace("-", ""), "open": v, "high": v, "low": v, "close": v, "volume": 0})
            if rows:
                ibkr_service.save_data_to_db(TBILL_NAME, rows, "1 day", keep_existing=True)
                df = ibkr_service.get_data_from_db(TBILL_NAME, "1990-01-01", end, "1 day")
        if df.empty:
            return None, "3-month T-bill yearly averages (no daily rates)"
        col = "close" if "close" in df.columns else "Close"
        return {ts.date(): float(v) / 100 for ts, v in df[col].items()}, "3-month T-bill, daily (FRED DTB3)"
    except Exception as e:   # no DB, no internet: the yearly averages still give a fair picture
        logger.warning(f"T-bill rates unavailable ({e}); using yearly averages")
        return None, "3-month T-bill yearly averages (daily rates unavailable)"


def _tradekit():
    try:
        from tradekit.backtests import (POOR_COVERED_CALL_DEFAULTS, poor_covered_call_auto,
                                        poor_covered_call_backtest, poor_covered_call_summary)
        from tradekit.rules.poor_covered_call import PoorCoveredCall
    except ImportError as e:
        raise RuntimeError(
            f"Could not import the POOR_COVERED_CALL rules from {SHARED_PATH} ({e}). Pull the latest "
            f"algo_trading or set ALGO_BASE_PATH in backend/services/.env."
        ) from e
    return (POOR_COVERED_CALL_DEFAULTS, poor_covered_call_backtest, poor_covered_call_summary, PoorCoveredCall,
            poor_covered_call_auto)


def poor_covered_call_params() -> dict:
    """The rules' parameters and the backtest's own settings, with defaults and ranges."""
    defaults, _, _, Rules, _ = _tradekit()
    rules = [{"name": p.name, "type": p.type.__name__, "default": p.default, "min": p.lo, "max": p.hi,
              "choices": list(p.choices) if p.choices else None, "help": p.help}
             for p in Rules.PARAMS if p.name != "underlying"]
    return {"rules": rules, "backtest": dict(defaults)}


def run_poor_covered_call(config: dict, start_dt: datetime, end_dt: datetime,
                          initial_balance: Optional[float] = None) -> dict:
    """Run the shared rules and return {date: {...}} in the dashboard's format, plus __metadata__."""
    defaults, backtest, summarize, Rules, auto = _tradekit()
    config = dict(config or {})
    if "budget" not in config and initial_balance:
        config["budget"] = initial_balance
    params = _rule_params(config, Rules)
    params["underlying"] = str(config.get("underlying") or "SPY").upper().strip()
    p = Rules(params).p     # validates every value against its range
    settings = {k: float(config[k]) if config.get(k) not in (None, "") else v for k, v in defaults.items()}
    settings["long_days"] = int(settings["long_days"])

    start, end = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    days, notes = load_days(p.underlying, start, end, "market")
    # blank ticker-dependent settings: SPY's fixed values, or from the stock's own prices and IV
    settings.update({k: v for k, v in auto(days, p.underlying).items() if settings.get(k) is None})
    rates, rate_note = (None, None)
    if settings.get("cash_rate") is None or settings.get("risk_free_rate") is None:
        rates, rate_note = load_tbill(end)
    logger.info(f"POOR_COVERED_CALL {p.underlying} {start}..{end}: {len(days)} days, IV {notes}, {settings}")
    bt = backtest(days, params, rates=rates, **settings)
    if rate_note:
        notes = dict(notes, rates=rate_note)
    return to_dashboard(bt, days, p, notes, summarize(bt), settings)


def _log_text(t) -> str:
    """A trade for the Trading_Log. Only real shares read as "Buy: N shares" (the chart marks
    those); calls read as "Buy call" / "Sell call"."""
    if " " not in t.contract:   # the stock (left by an assignment or exercise)
        verb = "Buy" if t.side == "BUY" else "Sell"
        return f"{verb}: {t.qty} shares at ${t.price:.2f} ({t.reason})"
    verb = "Buy call" if t.side == "BUY" else "Sell call"
    return f"{verb}: {t.qty} {t.contract} @ {t.price:.2f} ({t.reason})"


def to_dashboard(bt, days, p, notes: dict, summary: dict, settings: dict) -> Dict[str, dict]:
    # Buy & hold the same ticker with the same money, dividends reinvested at the ex-date close
    shares = p.budget / days[0].close if days[0].close > 0 else 0.0
    bench = {}
    for d in days:
        if d.dividend and d.close > 0 and d.date != days[0].date:
            shares *= 1 + d.dividend / d.close
        bench[d.date] = shares * d.close

    by_date = {d.date: d for d in days}
    long_only = dict(getattr(bt, "long_only", None) or [])   # the same long calls and rolls, no calls sold
    out: Dict[str, dict] = {}
    prev = None
    peak, max_dd = 0.0, 0.0
    for r in bt.results:
        day = by_date[r.date]
        daily = lambda name: getattr(r, name) - (getattr(prev, name) if prev else 0.0)
        state = lambda name, src: (src.state.get(name) or 0.0) if src else 0.0
        st = r.state
        exposure = (st.get("long_qty", 0) + st.get("old_long_qty", 0)) * 100 * r.close
        peak = max(peak, r.equity)
        if peak > 0:
            max_dd = max(max_dd, 1 - r.equity / peak)
        out[r.date.strftime("%Y-%m-%d")] = {
            "Portfolio_Value": round(r.equity, 2),
            "Cash_Balance": round(r.cash, 2),
            "Close": r.close,
            "Open": day.open,
            "High": day.high,
            "Low": day.low,
            "VIX": round(r.iv, 4) if r.iv is not None else 0.0,
            "Margin_Ratio": round(exposure / r.equity, 4) if r.equity > 0 else 0.0,   # stock exposure per $ equity
            "spy_value": round(bench.get(r.date, 0.0), 2),
            **({"long_only_value": round(long_only[r.date], 2)} if r.date in long_only else {}),
            "Interest_Paid": 0.0,
            "Withdrawal": 0.0,
            # the rules' own total: short calls sold only (the engine's counts the old long calls sold in rolls too)
            "Premiums_Received": round(state("premiums", r) - state("premiums", prev), 2),
            "Dividends_Received": round(daily("dividends"), 2),
            "Commissions_Paid": round(daily("commissions"), 2),
            # in-the-money short calls bought back (month end, before ex-dividend); not harvests of nearly worthless ones
            "Call_Closure_Cost": round(sum(t.qty * t.price * 100 + t.commission for t in r.trades
                                           if t.side == "BUY" and t.reason.startswith(("MONTH END", "EX-DIVIDEND"))), 2),
            "Open_Positions": (1 if st.get("long_qty") else 0) + (1 if st.get("short_qty") else 0),
            "Closed_Positions": 0,
            "Shares": r.shares,
            "Option_Value": round(r.option_value, 2),
            "Trading_Log": "; ".join(_log_text(t) for t in r.trades),
        }
        prev = r

    final = bt.results[-1]
    years = max((final.date - bt.results[0].date).days / 365.25, 1e-9)
    summary = dict(summary)
    summary.update({
        "underlying": p.underlying,
        "budget": p.budget,
        "final_value": round(final.equity, 2),
        "benchmark_final_value": round(bench.get(final.date, 0.0), 2),
        "cagr": round(((final.equity / p.budget) ** (1 / years) - 1) * 100, 1) if final.equity > 0 else None,
        "max_drawdown_pct": round(max_dd * 100, 1),
    })
    out["__metadata__"] = {
        "strategy": STRATEGY_ID,
        "pcc_summary": summary,
        "data_notes": dict(notes, **settings, pricing=f"Black-Scholes with {p.underlying}'s dividend yield: monthly calls at "
                                                      f"{'VIX' if p.underlying == 'SPY' else 'its 30-day IV'} x short_iv_mult, "
                                                      "the year-out call at a damped long-dated IV; no skew; "
                                                      "half-spreads paid as slippage"),
    }
    return out
