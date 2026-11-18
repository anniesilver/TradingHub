"""POOR_COVERED_CALL (shared rules) through TradingHub's service, with made-up prices.

Needs algo_trading next to TradingHub (or ALGO_BASE_PATH pointing at it) for tradekit.
"""
import os
import sys
from datetime import datetime

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("ALGO_BASE_PATH", os.path.join(HERE, "..", "..", "..", "algo_trading"))

from services import wheel_service  # noqa: E402

if not os.path.isfile(os.path.join(os.environ["ALGO_BASE_PATH"], "shared", "tradekit", "rules",
                                   "poor_covered_call.py")):
    pytest.skip("algo_trading/shared with the POOR_COVERED_CALL rules not found", allow_module_level=True)

from services import poor_covered_call_service as svc  # noqa: E402
from services import paper_test_service  # noqa: E402
from test_wheel_service import fake_market_data  # noqa: E402


def test_runs_the_shared_rules_and_returns_dashboard_days(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0 + i * 0.5))
    out = svc.run_poor_covered_call({}, datetime(2025, 1, 2), datetime(2025, 6, 30), initial_balance=60_000)
    meta = out.pop("__metadata__")
    days = sorted(out)
    first = out[days[0]]["Trading_Log"]
    close = out[days[0]]["Close"]
    long_k = int(close * 0.8 // 5 * 5)
    assert first.startswith(f"Buy call: 2 SPY {long_k}C 2026-")     # 60k x 1.5 / (100 x ~520) = 1.7 -> 2
    assert "Sell call: 2 SPY " in first and "(SELL CALL)" in first
    assert "shares" not in " ".join(out[d]["Trading_Log"] for d in days)   # no share trades
    s = meta["pcc_summary"]
    assert s["budget"] == 60_000 and s["calls_sold"] >= 5 and s["long_qty"] == 2
    assert 1.6 < out[days[0]]["Margin_Ratio"] < 1.9                # SPY exposure per $1 of equity


def test_params_and_paper_test_mapping():
    schema = svc.poor_covered_call_params()
    names = [p["name"] for p in schema["rules"]]
    assert "size" in names and "harvest_at" in names and "underlying" not in names
    assert schema["backtest"]["long_slippage"] == 0.40
    assert paper_test_service.server_name("POOR_COVERED_CALL") == "poor_covered_call"
    params = paper_test_service.rule_params("POOR_COVERED_CALL", {"budget": 60000, "size": "1.25"})
    assert params["size"] == 1.25 and params["budget"] == 60000.0 and params["long_itm_pct"] == 0.2
