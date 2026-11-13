"""SPY_POWER_CASHFLOW backtests on the shared rules (algo_trading/shared/tradekit).

The rules (tradekit/rules/spy_power_cashflow.py) are the very file trade-engine's paper
bot runs. The engine (tradekit/daily.py) decides once a day at the close, like the bot does
at 15:45. This module loads SPY's daily bars (VIX as the IV, dividends) the same way as the
Wheel, and turns the result into the dashboard's format.

The old simulator (algo_trading/SPY_POWER_CASHFLOW, TradingSimulator) is still available
as the strategy "SPY_POWER_CASHFLOW", shown as "SPY Power Cashflow (old)", for comparison.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, Optional

from services.wheel_service import SHARED_PATH, load_days

logger = logging.getLogger(__name__)

STRATEGY_ID = "SPY_POWER_CASHFLOW_RULES"


def _tradekit():
    try:
        from tradekit.backtests import BACKTEST_DEFAULTS, spy_power_cashflow_backtest, spy_power_cashflow_summary
        from tradekit.rules.spy_power_cashflow import SpyPowerCashflow
    except ImportError as e:
        raise RuntimeError(
            f"Could not import the SPY_POWER_CASHFLOW rules from {SHARED_PATH} ({e}). Pull the latest "
            f"algo_trading or set ALGO_BASE_PATH in backend/services/.env."
        ) from e
    return BACKTEST_DEFAULTS, spy_power_cashflow_backtest, spy_power_cashflow_summary, SpyPowerCashflow


def spy_power_cashflow_params() -> dict:
    """The rules' parameters and the backtest's own settings, with defaults and ranges."""
    defaults, _, _, Rules = _tradekit()
    rules = [{"name": p.name, "type": p.type.__name__, "default": p.default, "min": p.lo, "max": p.hi,
              "choices": list(p.choices) if p.choices else None, "help": p.help}
             for p in Rules.PARAMS if p.name != "underlying"]
    return {"rules": rules, "backtest": dict(defaults)}


def _rule_params(config: dict, Rules) -> dict:
    out = {}
    for p in Rules.PARAMS:
        if p.name == "underlying" or p.name not in config or config[p.name] in (None, ""):
            continue
        v = config[p.name]
        if p.type is bool:
            v = v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
        elif p.type is int:
            v = int(float(v))
        elif p.type is float:
            v = float(v)
        else:
            v = str(v)
        out[p.name] = v
    return out


def run_spy_power_cashflow_rules(config: dict, start_dt: datetime, end_dt: datetime,
                                 initial_balance: Optional[float] = None) -> dict:
    """Run the shared rules and return {date: {...}} in the dashboard's format, plus __metadata__."""
    defaults, backtest, summarize, Rules = _tradekit()
    config = dict(config or {})
    if "budget" not in config and initial_balance:
        config["budget"] = initial_balance
    params = _rule_params(config, Rules)
    p = Rules(params).p     # validates every value against its range
    strike_step = float(config.get("strike_step", defaults["strike_step"]))
    slippage = float(config.get("slippage", defaults["slippage"]))
    rate = float(config.get("risk_free_rate", defaults["risk_free_rate"]))
    if strike_step <= 0:
        raise ValueError("strike_step must be above 0")

    start, end = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    days, notes = load_days(p.underlying, start, end, "market")
    logger.info(f"SPY_POWER_CASHFLOW (rules) {start}..{end}: {len(days)} days, IV {notes}")
    bt = backtest(days, params, strike_step=strike_step, slippage=slippage, risk_free_rate=rate)
    return to_dashboard(bt, days, p, notes, summarize(bt),
                        {"strike_step": strike_step, "slippage": slippage, "risk_free_rate": rate})


def _log_text(t) -> str:
    """A trade for the Trading_Log; cash moves in the words the dashboard looks for."""
    if t.side == "CASH":
        what = "Monthly withdrawal" if t.reason == "WITHDRAW" else t.reason.capitalize()
        return f"{what}: ${t.price:,.2f}"
    return t.text()


def to_dashboard(bt, days, p, notes: dict, summary: dict, settings: dict) -> Dict[str, dict]:
    # Buy & hold SPY with the same money, dividends reinvested at the ex-date close
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
        state = lambda name, src: (src.state.get(name) or 0.0) if src else 0.0
        calls = r.state.get("calls") or []
        out[r.date.strftime("%Y-%m-%d")] = {
            "Portfolio_Value": round(r.equity, 2),
            "Cash_Balance": round(r.cash, 2),
            "Close": r.close,
            "Open": day.open,
            "High": day.high,
            "Low": day.low,
            "VIX": round(r.iv, 4) if r.iv is not None else 0.0,
            "Margin_Ratio": round(r.stock_value / r.equity, 4) if r.equity > 0 else 0.0,
            "spy_value": round(bench.get(r.date, 0.0), 2),
            "Interest_Paid": round(state("interest", r) - state("interest", prev), 2),
            "Withdrawal": round(state("withdrawn", r) - state("withdrawn", prev), 2),
            "Premiums_Received": round(daily("premiums"), 2),
            "Dividends_Received": round(daily("dividends"), 2),
            "Commissions_Paid": round(daily("commissions"), 2),
            "Open_Positions": len(calls) + (1 if r.shares else 0),
            "Closed_Positions": 0,
            "Shares": r.shares,
            "Option_Value": round(r.option_value, 2),
            "Trading_Log": "; ".join(_log_text(t) for t in r.trades),
        }
        prev = r

    final = bt.results[-1]
    summary = dict(summary)
    summary.update({
        "budget": p.budget,
        "final_value": round(final.equity, 2),
        "benchmark_final_value": round(bench.get(final.date, 0.0), 2),
        "max_leverage_seen": round(max((x.stock_value / x.equity for x in bt.results if x.equity > 0), default=0.0), 2),
    })
    out["__metadata__"] = {
        "strategy": STRATEGY_ID,
        "spy_cashflow_summary": summary,
        "data_notes": dict(notes, **settings, pricing="Black-Scholes at VIX, one IV for all strikes (no skew), "
                                                      "month-end expiries, no bid/ask spread"),
    }
    return out
