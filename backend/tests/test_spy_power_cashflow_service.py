"""SPY_POWER_CASHFLOW (shared rules) through TradingHub's service, with made-up prices.

Needs algo_trading next to TradingHub (or ALGO_BASE_PATH pointing at it) for tradekit.
"""
import os
import re
import sys
from datetime import datetime

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("ALGO_BASE_PATH", os.path.join(HERE, "..", "..", "..", "algo_trading"))

from services import wheel_service  # noqa: E402

if not os.path.isfile(os.path.join(os.environ["ALGO_BASE_PATH"], "shared", "tradekit", "rules",
                                   "spy_power_cashflow.py")):
    pytest.skip("algo_trading/shared with the SPY_POWER_CASHFLOW rules not found", allow_module_level=True)

from services import spy_power_cashflow_service as svc  # noqa: E402
from test_wheel_service import fake_market_data  # noqa: E402


def test_runs_the_shared_rules_and_returns_dashboard_days(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))
    out = svc.run_spy_power_cashflow_rules({}, datetime(2025, 1, 2), datetime(2025, 3, 31), initial_balance=500_000)
    meta = out.pop("__metadata__")
    days = sorted(out)
    first = out[days[0]]
    # 60% of 500k at 500 = 600 shares, then 6 calls at max(1.5%, VIX x 0.3) above -> 520
    assert first["Trading_Log"].startswith("Buy: 600 shares at $500.00 (FIRST BUY); Sell call: 6 SPY 520C 2025-01-31")
    # an expiry closes the call without looking like a share purchase (the chart marks those)
    expiry = out["2025-01-31"]["Trading_Log"]
    assert "Close call: 6 SPY 520C 2025-01-31 @ 0.00 (EXPIRED)" in expiry
    assert not re.search(r"(?:buy|bought|purchase[d]?)(?:\s+|:\s*)\d", expiry.replace("Buy: ", "", 0), re.I)
    assert first["Shares"] == 600 and first["Margin_Ratio"] == pytest.approx(0.6, abs=0.01)
    s = meta["spy_cashflow_summary"]
    assert s["calls_sold"] == 3 and s["calls_expired"] == 3 and s["budget"] == 500_000
    assert sum(out[d]["Withdrawal"] for d in days) == pytest.approx(s["withdrawn"], abs=0.05)
    assert "Monthly withdrawal: $" in out["2025-01-31"]["Trading_Log"]
    assert meta["strategy"] == "SPY_POWER_CASHFLOW_RULES" and meta["data_notes"]["iv_name"] == "VIX"


def test_buy_and_hold_takes_the_same_monthly_withdrawal(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))
    out = svc.run_spy_power_cashflow_rules({"monthly_withdrawal_pct": 1.0}, datetime(2025, 1, 2), datetime(2025, 3, 31),
                                           initial_balance=500_000)
    s = out.pop("__metadata__")["spy_cashflow_summary"]
    # flat price, 1% at each of the three month ends: 500k x 0.99^3, the rest withdrawn
    assert s["benchmark_final_value"] == pytest.approx(500_000 * 0.99 ** 3, abs=1)
    assert s["benchmark_withdrawn"] == pytest.approx(500_000 - 500_000 * 0.99 ** 3, abs=1)
    assert out["2025-01-30"]["spy_value"] == pytest.approx(500_000, abs=1)
    assert out["2025-01-31"]["spy_value"] == pytest.approx(495_000, abs=1)
    none = svc.run_spy_power_cashflow_rules({"monthly_withdrawal_pct": 0.0}, datetime(2025, 1, 2), datetime(2025, 3, 31),
                                            initial_balance=500_000)["__metadata__"]["spy_cashflow_summary"]
    assert none["benchmark_final_value"] == pytest.approx(500_000, abs=1) and none["benchmark_withdrawn"] == 0


def test_first_buy_follows_the_high_before_the_start(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))
    seen = []
    monkeypatch.setattr(svc, "_prior_high", lambda sym, start: seen.append((sym, start)) or 600.0)
    out = svc.run_spy_power_cashflow_rules({}, datetime(2025, 1, 2), datetime(2025, 1, 31), initial_balance=500_000)
    assert seen == [("SPY", "2025-01-02")]
    assert out[min(k for k in out if k != "__metadata__")]["Shares"] == 1000      # 16.7% below 600: 100%
    seen.clear()
    out = svc.run_spy_power_cashflow_rules({"start_high": 510}, datetime(2025, 1, 2), datetime(2025, 1, 31),
                                           initial_balance=500_000)
    assert seen == [] and out[min(k for k in out if k != "__metadata__")]["Shares"] == 600   # set by hand: 2% below


def test_spy_on_margin_at_the_strategys_average_leverage(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))
    out = svc.run_spy_power_cashflow_rules({"monthly_withdrawal_pct": 0.0}, datetime(2025, 1, 2), datetime(2025, 3, 31),
                                           initial_balance=500_000)
    s = out.pop("__metadata__")["spy_cashflow_summary"]
    # flat price, no dips: the strategy holds 60% (0.6x), so the benchmark holds 0.6x and never borrows
    assert s["margin_benchmark_leverage"] == pytest.approx(0.6, abs=0.01)
    assert s["margin_benchmark_final_value"] == pytest.approx(500_000, abs=5)
    assert all("margin_value" in v for v in out.values())


def test_margin_benchmark_pays_interest_on_the_borrowed_part():
    from datetime import date
    from types import SimpleNamespace as NS
    from tradekit.market_calendar import month_last_trading_day
    days = [NS(date=date(2025, 1, d), close=100.0, dividend=0.0) for d in (2, 3, 6, 7, 8)]
    bt = NS(results=[NS(stock_value=150.0, equity=100.0)] * 5)
    p = NS(budget=100_000.0, margin_interest_rate=0.0365, monthly_withdrawal_pct=0.0, stock_commission=0.01,
           min_commission=1.0)
    values, withdrawn, lev = svc._margin_benchmark(bt, days, p, month_last_trading_day)
    assert lev == 1.5 and withdrawn == 0
    # 150k of SPY, 50k borrowed at 3.65%/yr = $5 a calendar day; 2nd -> 8th = 6 days
    assert values[date(2025, 1, 8)] == pytest.approx(100_000 - 6 * 5, abs=0.2)


def test_margin_interest_is_charged_but_not_in_the_trading_log(monkeypatch):
    # a falling price makes the rules buy dips on margin, so interest is charged every day
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0 - 0.8 * i))
    out = svc.run_spy_power_cashflow_rules({}, datetime(2025, 1, 2), datetime(2025, 6, 30), initial_balance=500_000)
    meta = out.pop("__metadata__")
    assert meta["spy_cashflow_summary"]["interest"] > 0
    assert sum(v["Interest_Paid"] for v in out.values()) == pytest.approx(meta["spy_cashflow_summary"]["interest"], abs=0.5)
    assert not any("Margin interest" in v["Trading_Log"] for v in out.values())


def test_settings_are_validated(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))
    with pytest.raises(ValueError):
        svc.run_spy_power_cashflow_rules({"max_leverage": 9}, datetime(2025, 1, 2), datetime(2025, 1, 31))


def test_params_list_every_rule_but_the_underlying():
    params = svc.spy_power_cashflow_params()
    names = [p["name"] for p in params["rules"]]
    assert "underlying" not in names and "max_leverage" in names and "month_end_buyback_buffer" in names
    assert params["backtest"]["strike_step"] == 1.0


def test_itm_call_buybacks_are_reported_per_day(monkeypatch):
    # a rising price puts the month's calls in the money, so the rules buy them back at month end
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0 + 1.5 * i))
    out = svc.run_spy_power_cashflow_rules({}, datetime(2025, 1, 2), datetime(2025, 6, 30), initial_balance=500_000)
    meta = out.pop("__metadata__")
    s = meta["spy_cashflow_summary"]
    assert s["calls_bought_back"] > 0 and s["buybacks"] > 0
    assert sum(v["Call_Closure_Cost"] for v in out.values()) == pytest.approx(s["buybacks"], abs=0.5)
    days_with_cost = [d for d, v in out.items() if v["Call_Closure_Cost"] > 0]
    assert days_with_cost and all("Close call:" in out[d]["Trading_Log"] for d in days_with_cost)
