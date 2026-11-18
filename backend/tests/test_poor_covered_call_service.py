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
    total = sum(out[d]["Premiums_Received"] for d in days)
    assert total == pytest.approx(s["premiums"], abs=1.0)              # short calls only, not long-call roll sales
    assert 1.6 < out[days[0]]["Margin_Ratio"] < 1.9                # SPY exposure per $1 of equity


def test_params_and_paper_test_mapping():
    schema = svc.poor_covered_call_params()
    names = [p["name"] for p in schema["rules"]]
    assert "size" in names and "harvest_at" in names and "underlying" not in names
    assert schema["backtest"]["long_slippage"] == 0.40
    assert paper_test_service.server_name("POOR_COVERED_CALL") == "poor_covered_call"
    params = paper_test_service.rule_params("POOR_COVERED_CALL", {"budget": 60000, "size": "1.25"})
    assert params["size"] == 1.25 and params["budget"] == 60000.0 and params["long_itm_pct"] == 0.2


def _fake_stock(monkeypatch, price=40.0, iv=0.45, dividend=0.25):
    """A ticker other than SPY: its own IV and dividends (not VIX, not the DB)."""
    import pandas as pd
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: price + i * 0.02))
    monkeypatch.setattr(wheel_service, "_load_stock_iv",
                        lambda symbol, start, end: pd.Series(iv, index=pd.bdate_range(start, end)))
    monkeypatch.setattr(wheel_service, "_load_dividends",
                        lambda symbol, start, end: pd.Series([dividend], index=[pd.Timestamp("2025-03-14")]))


def test_runs_on_the_pages_ticker_with_settings_worked_out_for_it(monkeypatch):
    _fake_stock(monkeypatch)
    cfg = {"underlying": "amzn", "short_iv_mult": "", "long_iv_base": "", "dividend_yield": "", "strike_rounding": ""}
    out = svc.run_poor_covered_call(cfg, datetime(2025, 1, 2), datetime(2025, 6, 30), initial_balance=60_000)
    meta = out.pop("__metadata__")
    s, notes = meta["pcc_summary"], meta["data_notes"]
    assert s["underlying"] == "AMZN"
    first = out[sorted(out)[0]]["Trading_Log"]
    assert "AMZN " in first and "SPY" not in first
    auto = notes["auto_settings"]
    assert auto["strike_rounding"] == 0.5                       # a $40 stock: $0.50 strikes, not SPY's $5
    assert auto["long_iv_base"] == pytest.approx(0.45)          # its own IV, not SPY's 0.17
    assert auto["short_iv_mult"] == svc.STOCK_SHORT_IV_MULT
    assert 0 < auto["dividend_yield"] < 0.02
    assert notes["short_iv_mult"] == svc.STOCK_SHORT_IV_MULT and "AMZN's 30-day IV" in notes["pricing"]


def test_a_setting_typed_on_the_page_wins_over_the_tickers_own(monkeypatch):
    _fake_stock(monkeypatch)
    out = svc.run_poor_covered_call({"underlying": "AMZN", "short_iv_mult": 0.7, "long_iv_base": 0.3},
                                    datetime(2025, 1, 2), datetime(2025, 3, 31), initial_balance=60_000)
    notes = out["__metadata__"]["data_notes"]
    assert notes["short_iv_mult"] == 0.7 and notes["long_iv_base"] == 0.3
    assert "short_iv_mult" not in notes.get("auto_settings", {})


def test_spy_keeps_its_defaults(monkeypatch):
    monkeypatch.setattr(wheel_service, "_market_data_class", lambda: fake_market_data(lambda i: 500.0 + i * 0.5))
    out = svc.run_poor_covered_call({"underlying": "SPY", "short_iv_mult": ""}, datetime(2025, 1, 2),
                                    datetime(2025, 3, 31), initial_balance=60_000)
    notes = out["__metadata__"]["data_notes"]
    assert "auto_settings" not in notes and notes["short_iv_mult"] == 0.8


def test_a_bad_ticker_is_an_error_not_spy():
    with pytest.raises(ValueError):
        svc.run_poor_covered_call({"underlying": "AM ZN;"}, datetime(2025, 1, 2), datetime(2025, 3, 31))


def test_the_paper_test_never_takes_the_pages_ticker():
    # paper_test_service builds the paper bot's settings with this same helper
    from services.poor_covered_call_service import _rule_params as rp
    _, _, _, Rules = svc._tradekit()
    assert "underlying" not in rp({"underlying": "AMZN", "budget": 60_000}, Rules)
