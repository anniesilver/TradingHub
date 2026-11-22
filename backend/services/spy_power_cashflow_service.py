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
        from tradekit.backtests import SPY_POWER_CASHFLOW_DEFAULTS, spy_power_cashflow_backtest, spy_power_cashflow_summary
        from tradekit.rules.spy_power_cashflow import SpyPowerCashflow
    except ImportError as e:
        raise RuntimeError(
            f"Could not import the SPY_POWER_CASHFLOW rules from {SHARED_PATH} ({e}). Pull the latest "
            f"algo_trading or set ALGO_BASE_PATH in backend/services/.env."
        ) from e
    return SPY_POWER_CASHFLOW_DEFAULTS, spy_power_cashflow_backtest, spy_power_cashflow_summary, SpyPowerCashflow


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
    iv_mult = float(config.get("short_iv_mult", defaults["short_iv_mult"]))
    if strike_step <= 0:
        raise ValueError("strike_step must be above 0")
    if iv_mult <= 0:
        raise ValueError("short_iv_mult must be above 0")

    start, end = start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")
    days, notes = load_days(p.underlying, start, end, "market")
    logger.info(f"SPY_POWER_CASHFLOW (rules) {start}..{end}: {len(days)} days, IV {notes}")
    bt = backtest(days, params, strike_step=strike_step, slippage=slippage, risk_free_rate=rate,
                  short_iv_mult=iv_mult)
    return to_dashboard(bt, days, p, notes, summarize(bt),
                        {"strike_step": strike_step, "slippage": slippage, "risk_free_rate": rate,
                         "short_iv_mult": iv_mult})


def _log_text(t) -> str:
    """A trade for the Trading_Log, in the words the dashboard looks for: a share purchase as
    "Buy: N shares at $P" (the chart marks those), a withdrawal as "Monthly withdrawal: $X".
    Closing a call (bought back or expired) must not read as "BUY n ...", or the chart would
    mark every month's expiry as a share purchase."""
    if t.side == "CASH":
        what = "Monthly withdrawal" if t.reason == "WITHDRAW" else t.reason.capitalize()
        return f"{what}: ${t.price:,.2f}"
    if " " not in t.contract:   # the stock
        verb = "Buy" if t.side == "BUY" else "Sell"
        return f"{verb}: {t.qty} shares at ${t.price:.2f} ({t.reason})"
    if t.side == "BUY":
        return f"Close call: {t.qty} {t.contract} @ {t.price:.2f} ({t.reason})"
    return f"Sell call: {t.qty} {t.contract} @ {t.price:.2f} ({t.reason})"


def _call_closure_cost(trades, close: float, underlying: str) -> float:
    """What closing in-the-money calls cost on one day (the "ITM call closure costs" on the
    results page): calls bought back (price x 100 + commission, the same as the rules'
    `buybacks`) plus, for calls assigned at expiry, what the shares were worth above the
    strike they went at ((close - strike) x shares)."""
    cost = 0.0
    for t in trades:
        if t.side == "BUY" and " " in t.contract and t.reason not in ("EXPIRED", "ASSIGNED"):
            cost += t.qty * t.price * 100 + t.commission
        elif t.contract == underlying and t.side == "SELL" and t.reason.startswith("ASSIGNED"):
            cost += max(close - t.price, 0.0) * t.qty
    return cost


def _is_margin_interest(t) -> bool:
    """The daily margin interest charge. It is still taken from cash and counted in
    Interest_Paid and the summary; it is only kept out of the Trading_Log, which is for the
    key trades (calls, dip buys, deleverage sells, withdrawals)."""
    return t.side == "CASH" and t.reason == "MARGIN INTEREST"


def _margin_benchmark(bt, days, p, month_last_trading_day):
    """SPY held on margin at the strategy's own average leverage (mean of the daily
    stock value / equity), with no dip rules and no calls: is the strategy better than simply
    borrowing the same amount? Starts with budget x L in SPY, the rest borrowed. Margin
    interest at the rules' margin_interest_rate on negative cash, charged daily / 365 like the
    rules; dividends go to cash; on each month's last trading day it takes the same
    monthly_withdrawal_pct of its value, then trades back to L (the rules' stock commission).
    Returns ({date: value}, total withdrawn, L)."""
    levs = [r.stock_value / r.equity for r in bt.results if r.equity > 0]
    lev = sum(levs) / len(levs) if levs else 1.0
    if not days or days[0].close <= 0:
        return {}, 0.0, lev
    shares = p.budget * lev / days[0].close
    cash = p.budget - shares * days[0].close
    values, withdrawn, prev = {}, 0.0, None
    wpct = (p.monthly_withdrawal_pct or 0.0) / 100.0
    for d in days:
        if prev is not None and cash < 0:
            cash += cash * p.margin_interest_rate * (d.date - prev).days / 365
        prev = d.date
        if d.dividend and d.date != days[0].date:
            cash += shares * d.dividend
        if d.close > 0 and d.date == month_last_trading_day(d.date):
            equity = cash + shares * d.close
            if wpct and equity > 0:
                cash -= equity * wpct
                withdrawn += equity * wpct
                equity *= 1 - wpct
            target = max(equity, 0.0) * lev / d.close
            qty = abs(target - shares)
            if qty >= 1:
                cash -= (target - shares) * d.close + max(qty * p.stock_commission, p.min_commission)
                shares = target
        values[d.date] = cash + shares * d.close
    return values, withdrawn, lev


def to_dashboard(bt, days, p, notes: dict, summary: dict, settings: dict) -> Dict[str, dict]:
    # Buy & hold SPY with the same money, dividends reinvested at the ex-date close. It takes
    # the same monthly withdrawal as the strategy (monthly_withdrawal_pct of its value, sold on
    # the month's last trading day), so the two lines compare like for like.
    from tradekit.market_calendar import month_last_trading_day
    shares = p.budget / days[0].close if days[0].close > 0 else 0.0
    bench = {}
    bench_withdrawn = 0.0
    wpct = (p.monthly_withdrawal_pct or 0.0) / 100.0
    for d in days:
        if d.dividend and d.close > 0 and d.date != days[0].date:   # bought at the first close: after its ex-date
            shares *= 1 + d.dividend / d.close
        if wpct and d.close > 0 and d.date == month_last_trading_day(d.date):
            bench_withdrawn += shares * d.close * wpct
            shares *= 1 - wpct
        bench[d.date] = shares * d.close

    margin, margin_withdrawn, lev = _margin_benchmark(bt, days, p, month_last_trading_day)

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
            "margin_value": round(margin.get(r.date, 0.0), 2),
            "Interest_Paid": round(state("interest", r) - state("interest", prev), 2),
            "Withdrawal": round(state("withdrawn", r) - state("withdrawn", prev), 2),
            "Premiums_Received": round(daily("premiums"), 2),
            "Dividends_Received": round(daily("dividends"), 2),
            "Commissions_Paid": round(daily("commissions"), 2),
            "Call_Closure_Cost": round(_call_closure_cost(r.trades, r.close, p.underlying), 2),
            "Open_Positions": len(calls) + (1 if r.shares else 0),
            "Closed_Positions": 0,
            "Shares": r.shares,
            "Option_Value": round(r.option_value, 2),
            "Trading_Log": "; ".join(_log_text(t) for t in r.trades if not _is_margin_interest(t)),
        }
        prev = r

    final = bt.results[-1]
    summary = dict(summary)
    summary.update({
        "budget": p.budget,
        "final_value": round(final.equity, 2),
        "benchmark_final_value": round(bench.get(final.date, 0.0), 2),
        "benchmark_withdrawn": round(bench_withdrawn, 2),
        "margin_benchmark_leverage": round(lev, 2),
        "margin_benchmark_final_value": round(margin.get(final.date, 0.0), 2),
        "margin_benchmark_withdrawn": round(margin_withdrawn, 2),
        "max_leverage_seen": round(max((x.stock_value / x.equity for x in bt.results if x.equity > 0), default=0.0), 2),
    })
    out["__metadata__"] = {
        "strategy": STRATEGY_ID,
        "spy_cashflow_summary": summary,
        "data_notes": dict(notes, **settings, pricing="Black-Scholes at VIX x short_iv_mult, one IV for all strikes (no skew), "
                                                      "month-end expiries, no bid/ask spread"),
    }
    return out
