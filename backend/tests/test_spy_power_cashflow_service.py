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
    # 60% of 500k at 500 = 600 shares, then 6 calls at 500 x 1.0225 -> 510
    assert first["Trading_Log"].startswith("Buy: 600 shares at $500.00 (FIRST BUY); Sell call: 6 SPY 510C 2025-01-31")
    # an expiry closes the call without looking like a share purchase (the chart marks those)
    expiry = out["2025-01-31"]["Trading_Log"]
    assert "Close call: 6 SPY 510C 2025-01-31 @ 0.00 (EXPIRED)" in expiry
    assert not re.search(r"(?:buy|bought|purchase[d]?)(?:\s+|:\s*)\d", expiry.replace("Buy: ", "", 0), re.I)
    assert first["Shares"] == 600 and first["Margin_Ratio"] == pytest.approx(0.6, abs=0.01)
    s = meta["spy_cashflow_summary"]
    assert s["calls_sold"] == 3 and s["calls_expired"] == 3 and s["budget"] == 500_000
    assert sum(out[d]["Withdrawal"] for d in days) == pytest.approx(s["withdrawn"], abs=0.05)
    assert "Monthly withdrawal: $" in out["2025-01-31"]["Trading_Log"]
    assert meta["strategy"] == "SPY_POWER_CASHFLOW_RULES" and meta["data_notes"]["iv_name"] == "VIX"


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


def test_runs_on_the_pages_ticker(monkeypatch):
    import pandas as pd
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 40.0 + i * 0.02))
    monkeypatch.setattr(wheel_service, "_load_stock_iv",
                        lambda symbol, start, end: pd.Series(0.45, index=pd.bdate_range(start, end)))
    monkeypatch.setattr(wheel_service, "_load_dividends", lambda symbol, start, end: pd.Series(dtype=float))
    out = svc.run_spy_power_cashflow_rules({"underlying": "AMZN", "budget": 60_000, "strike_rounding": "",
                                            "strike_step": ""}, datetime(2025, 1, 2), datetime(2025, 3, 31))
    meta = out.pop("__metadata__")
    assert meta["spy_cashflow_summary"]["underlying"] == "AMZN"
    logs = " ".join(d["Trading_Log"] for d in out.values())
    assert "AMZN" in logs and "SPY" not in logs
    notes = meta["data_notes"]
    assert notes["auto_settings"] == {"strike_rounding": 0.5, "strike_step": 0.5}
    assert notes["strike_step"] == 0.5 and "implied volatility" in notes["pricing"]
