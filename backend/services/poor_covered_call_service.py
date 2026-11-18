"""POOR_COVERED_CALL backtests on the shared rules (algo_trading/shared/tradekit).

A poor man's covered call: a deep in-the-money call about a year out instead of 100 shares,
and a monthly call sold against it. The rules (tradekit/rules/poor_covered_call.py) are the
very file trade-engine's paper bot runs (on SPY only); the engine (tradekit/daily.py) decides
at the close, one order at a time, like the bot from 15:45. Any ticker backtests: SPY is
priced with VIX, another stock with its own 30-day IV from IB (loaded like WHEEL's), and the
ticker-dependent settings left blank are filled in by tradekit's poor_covered_call_auto.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Dict, Optional

from services.spy_power_cashflow_service import _rule_params
from services.wheel_service import SHARED_PATH, load_days

logger = logging.getLogger(__name__)

STRATEGY_ID = "POOR_COVERED_CALL"


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
    logger.info(f"POOR_COVERED_CALL {p.underlying} {start}..{end}: {len(days)} days, IV {notes}, {settings}")
    bt = backtest(days, params, **settings)
    return to_dashboard(bt, days, p, notes, summarize(bt), settings)


def _log_text(t) -> str:
    """A trade for the Trading_Log. Only real shares read as "Buy: N shares" (the chart marks
    those); calls read as "Buy call" / "Sell call"."""
    if " " not in t.contract:   # the stock (left by an assignment or exercise)
        verb = "Buy" if t.side == "BUY" else "Sell"
        return f"{verb}: {t.qty} shares at ${t.price:.2f} ({t.reason})"
    verb = "Buy call" if t.side == "BUY" else "Sell call"
    return f"{verb}: {t.qty} {t.contract} @ {t.price:.2f} ({t.reason})"


def _parse_label(label: Optional[str]):
    """'SPY 765C 2026-11-30' -> the Contract the backtest priced (None for no label)."""
    if not label:
        return None
    from tradekit import Contract
    symbol, strike_right, expiry = label.split()
    return Contract(symbol, strike_right[-1], float(strike_right[:-1]), date.fromisoformat(expiry))


def long_call_only_values(bt, days) -> Dict[date, float]:
    """The same strategy without the short calls: the very same long calls, bought, rolled and
    sold on the same days at the same prices, and nothing sold against them. Each day it is the
    strategy's equity minus everything the short calls did so far: premiums received (after
    commissions) less buybacks (with commissions), less what the open short call is worth now,
    plus the shares an assignment left (their P&L came from a short call)."""
    by_date = {d.date: d for d in days}
    out = {}
    for r in bt.results:
        st = r.state
        short_value = 0.0
        c = _parse_label(st.get("short_label"))
        if c is not None and st.get("short_qty"):
            short_value = st["short_qty"] * 100 * bt.price_option(c, by_date[r.date])
        short_pnl = (st.get("premiums") or 0.0) - (st.get("buybacks") or 0.0) - short_value             + (st.get("stock_pnl") or 0.0)
        out[r.date] = r.equity - short_pnl
    return out


def _stats(values: list, budget: float, years: float) -> dict:
    peak, dd = 0.0, 0.0
    for v in values:
        peak = max(peak, v)
        if peak > 0:
            dd = max(dd, 1 - v / peak)
    final = values[-1] if values else 0.0
    return {"final_value": round(final, 2),
            "cagr": round(((final / budget) ** (1 / years) - 1) * 100, 1) if final > 0 else None,
            "max_drawdown_pct": round(dd * 100, 1)}


def to_dashboard(bt, days, p, notes: dict, summary: dict, settings: dict) -> Dict[str, dict]:
    # Buy & hold the same ticker with the same money, dividends reinvested at the ex-date close
    shares = p.budget / days[0].close if days[0].close > 0 else 0.0
    bench = {}
    for d in days:
        if d.dividend and d.close > 0 and d.date != days[0].date:
            shares *= 1 + d.dividend / d.close
        bench[d.date] = shares * d.close

    long_only = long_call_only_values(bt, days)

    by_date = {d.date: d for d in days}
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
            # not margin (there is none): the shares the long calls stand for, x the price, per $1 of equity
            "Margin_Ratio": round(exposure / r.equity, 4) if r.equity > 0 else 0.0,
            "spy_value": round(bench.get(r.date, 0.0), 2),
            "long_only_value": round(long_only.get(r.date, 0.0), 2),   # the long calls alone, same rolls
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
        "long_only": _stats([long_only[r.date] for r in bt.results], p.budget, years),
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
