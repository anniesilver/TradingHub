"""Daily bars: every finished trading day up to the end asked for is fetched, not only gaps of
more than 10 days (a backtest run a week after the last import stopped at the old data)."""
import os
import sys
from datetime import date

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "services"))

import market_data  # noqa: E402
from market_data import last_complete_session, missing_recent_sessions  # noqa: E402

NY = "America/New_York"


def ts(text):
    return pd.Timestamp(text, tz=NY)


def test_last_complete_session_waits_for_the_close():
    assert last_complete_session(ts("2026-11-20 15:59")) == pd.Timestamp("2026-11-19")  # Fri, open
    assert last_complete_session(ts("2026-11-20 16:15")) == pd.Timestamp("2026-11-20")  # Fri, closed
    assert last_complete_session(ts("2026-11-21 10:00")) == pd.Timestamp("2026-11-20")  # Sat
    assert last_complete_session(ts("2026-11-23 09:00")) == pd.Timestamp("2026-11-20")  # Mon before the open


def test_missing_recent_sessions_counts_weekdays_only():
    last_done = pd.Timestamp("2026-11-20")
    # DB ends Fri 11-13, asked to Fri 11-20: the five days of this week are missing
    assert missing_recent_sessions(pd.Timestamp("2026-11-13"), pd.Timestamp("2026-11-20"), last_done) == 5
    # Up to date, or the end is a weekend after the last bar
    assert missing_recent_sessions(pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-22"), last_done) == 0
    # The end asked for is before the last bar
    assert missing_recent_sessions(pd.Timestamp("2026-11-20"), pd.Timestamp("2026-11-17"), last_done) == 0
    # Today's session not finished: it doesn't count
    assert missing_recent_sessions(pd.Timestamp("2026-11-19"), pd.Timestamp("2026-11-20"),
                                   pd.Timestamp("2026-11-19")) == 0


class FakeIB:
    """The DB holds bars to 11-13; a fetch adds the bars to 'until'."""

    def __init__(self):
        self.db_end = pd.Timestamp("2026-11-13")
        self.fetches = []
        self.last_error = None

    def get_data_from_db(self, symbol, start, end, interval):
        idx = pd.bdate_range(start, min(pd.Timestamp(end), self.db_end))
        return pd.DataFrame({"Open": 1.0, "High": 1.0, "Low": 1.0, "Close": 1.0, "Volume": 0}, index=idx)

    def fetch_and_store_data(self, symbol, period, bar_size, until=None):
        self.fetches.append((symbol, period, until))
        self.db_end = pd.Timestamp(until)
        return True


def test_a_week_old_db_is_brought_up_to_the_last_finished_day(monkeypatch):
    fake = FakeIB()
    monkeypatch.setattr(market_data, "ibkr_service", fake)
    monkeypatch.setattr(market_data, "last_complete_session", lambda: pd.Timestamp("2026-11-20"))
    df = market_data.MarketData("SPY")._load_symbol_data("SPY", "2026-10-20", "2026-11-20")
    assert fake.fetches == [("SPY", "14 D", date(2026, 11, 20))]
    assert df.index.max() == pd.Timestamp("2026-11-20")


def test_no_fetch_when_the_db_is_current(monkeypatch):
    fake = FakeIB()
    monkeypatch.setattr(market_data, "ibkr_service", fake)
    monkeypatch.setattr(market_data, "last_complete_session", lambda: pd.Timestamp("2026-11-13"))
    df = market_data.MarketData("SPY")._load_symbol_data("SPY", "2026-10-20", "2026-11-14")
    assert fake.fetches == []
    assert df.index.max() == pd.Timestamp("2026-11-13")
