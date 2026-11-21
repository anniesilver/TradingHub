import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
market_data = pytest.importorskip("market_data")

NY = ZoneInfo("America/New_York")


def test_last_complete_trading_day():
    f = market_data.last_complete_trading_day
    assert f(datetime(2026, 11, 20, 21, 0, tzinfo=NY)) == pd.Timestamp("2026-11-20")   # Fri evening
    assert f(datetime(2026, 11, 20, 12, 0, tzinfo=NY)) == pd.Timestamp("2026-11-19")   # Fri midday
    assert f(datetime(2026, 11, 22, 12, 0, tzinfo=NY)) == pd.Timestamp("2026-11-20")   # Sunday
    assert f(datetime(2026, 11, 23, 9, 0, tzinfo=NY)) == pd.Timestamp("2026-11-20")    # Mon morning


def test_a_one_week_gap_is_topped_up(monkeypatch):
    svc = market_data.ibkr_service
    db = {"rows": pd.date_range("2026-10-01", "2026-11-13", freq="B")}

    def get(symbol, start, end, interval):
        idx = db["rows"]
        return pd.DataFrame({"close": 1.0}, index=idx[(idx >= start) & (idx <= end)])

    fetched = []

    def fetch(symbol, period, interval):
        fetched.append(period)
        db["rows"] = pd.date_range("2026-10-01", "2026-11-20", freq="B")
        return True

    monkeypatch.setattr(svc, "get_data_from_db", get)
    monkeypatch.setattr(svc, "fetch_and_store_data", fetch)
    monkeypatch.setattr(market_data, "last_complete_trading_day", lambda: pd.Timestamp("2026-11-20"))
    market_data._TOPPED_UP.clear()
    md = market_data.MarketData.__new__(market_data.MarketData)
    df = md._load_symbol_data("SPY", "2026-10-20", "2026-11-20")
    assert df.index.max() == pd.Timestamp("2026-11-20") and len(fetched) == 1 and fetched[0].endswith(" D")
    md._load_symbol_data("SPY", "2026-10-20", "2026-11-20")
    assert len(fetched) == 1                                       # not asked again
