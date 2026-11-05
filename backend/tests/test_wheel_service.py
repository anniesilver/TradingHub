"""WHEEL through TradingHub's service, with made-up prices instead of the database.

Needs algo_trading next to TradingHub (or ALGO_BASE_PATH pointing at it) for tradekit.
"""
import os
import sys
from datetime import datetime

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("ALGO_BASE_PATH", os.path.join(HERE, "..", "..", "..", "algo_trading"))

from services import wheel_service  # noqa: E402

if not os.path.isdir(os.path.join(os.environ["ALGO_BASE_PATH"], "shared", "tradekit")):
    pytest.skip("algo_trading/shared not found", allow_module_level=True)


def fake_market_data(prices, vix=0.15, dividend_on=None):
    class FakeMarketData:
        def __init__(self, symbol):
            self.symbol = symbol

        def load_data(self, start, end):
            idx = pd.bdate_range(start, end)
            close = pd.Series([prices(i) for i in range(len(idx))], index=idx, dtype=float)
            df = pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close,
                               "VIX": vix, "Dividend": 0.0}, index=idx)
            if dividend_on is not None:
                df.loc[pd.Timestamp(dividend_on), "Dividend"] = 1.5
            return df

    return FakeMarketData


@pytest.fixture
def flat_spy(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0))


def test_run_wheel_returns_dashboard_days_and_summary(flat_spy):
    out = wheel_service.run_wheel({"budget": 100_000}, datetime(2025, 1, 6), datetime(2025, 3, 31))
    meta = out.pop("__metadata__")
    days = sorted(out)
    assert days[0] == "2025-01-06" and days[-1] == "2025-03-31"
    first = out[days[0]]
    assert first["Trading_Log"].startswith("SELL 2 SPY 475P")       # 5% below 500; 100k / 47.5k = 2
    assert first["Premiums_Received"] > 0 and first["Commissions_Paid"] == pytest.approx(1.3)
    assert first["spy_value"] == pytest.approx(100_000)
    assert meta["wheel_summary"]["puts_sold"] >= 2
    assert meta["data_notes"]["iv_name"] == "VIX"
    # flat prices: every put expires worthless, so the account only grows
    values = [out[d]["Portfolio_Value"] for d in days]
    assert values[-1] > 100_000


def test_initial_balance_is_the_budget_when_none_given(flat_spy):
    out = wheel_service.run_wheel({}, datetime(2025, 1, 6), datetime(2025, 1, 31), initial_balance=60_000)
    assert out["__metadata__"]["wheel_summary"]["budget"] == 60_000
    assert out["2025-01-06"]["Trading_Log"].startswith("SELL 1 SPY 475P")


def test_bad_parameter_is_refused(flat_spy):
    with pytest.raises(ValueError):
        wheel_service.run_wheel({"put_otm_pct": 0.9}, datetime(2025, 1, 6), datetime(2025, 1, 31))


def test_realized_vol_fallback(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class",
                        lambda: fake_market_data(lambda i: 100.0 + (i % 2), vix=float("nan")))
    days, notes = wheel_service.load_days("SPY", "2025-03-03", "2025-03-31")
    assert notes["days_on_realized_vol"] == len(days)
    assert all(d.iv and d.iv > 0 for d in days)


def test_params_endpoint_data():
    params = wheel_service.wheel_params()
    names = [p["name"] for p in params["rules"]]
    assert "budget" in names and "initial_position_pct" in names and "contracts" not in names
    assert params["backtest"]["strike_step"] == 1.0
