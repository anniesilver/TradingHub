"""IB's history server reported down (2105): the request gives up quickly with a clear message."""
import os
import sys
from datetime import datetime

import types

import pytest

try:
    import ibapi  # noqa: F401
except ImportError:  # the test only needs the client's own code; stand in for the IB library
    for name in ("ibapi", "ibapi.client", "ibapi.contract", "ibapi.wrapper"):
        sys.modules[name] = types.ModuleType(name)
    sys.modules["ibapi.client"].EClient = type("EClient", (), {"__init__": lambda self, wrapper: None})
    sys.modules["ibapi.wrapper"].EWrapper = type("EWrapper", (), {})
    sys.modules["ibapi.contract"].Contract = type("Contract", (), {})

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from services import ibkr_data_service as ids  # noqa: E402


def client(notices, answer=False):
    c = ids.IBKRDataClient()
    c.cancelled = []

    def req(req_id, *args):
        for code, text in notices:
            c.error(-1, code, text)
        if answer:
            c.historicalData(req_id, type("Bar", (), dict(date="20261111 09:30:00", open=1, high=1, low=1,
                                                            close=1, volume=1))())
            c.historicalDataEnd(req_id, "", "")

    c.reqHistoricalData = req
    c.cancelHistoricalData = c.cancelled.append
    return c


def test_broken_history_farm_fails_fast(monkeypatch):
    monkeypatch.setattr(ids, "FARM_DOWN_WAIT_S", 1)
    c = client([(2105, "HMDS data farm connection is broken:ushmds")])
    t0 = datetime.now()
    with pytest.raises(ids.HistoryServerDown, match="ushmds"):
        c.fetch_historical_data("TSLA", "3 W", "5 mins", "20261111 16:00:00 US/Eastern")
    assert (datetime.now() - t0).total_seconds() < 10
    assert c.cancelled == [0]


def test_farm_back_ok_is_not_down():
    c = client([(2105, "HMDS data farm connection is broken:ushmds"),
                (2106, "HMDS data farm connection is OK:ushmds")], answer=True)
    assert len(c.fetch_historical_data("TSLA", "1 D", "5 mins", "20261111 16:00:00 US/Eastern")) == 1
    assert c.hmds_down == set()


def test_intraday_range_passes_the_error_on(monkeypatch):
    svc = ids.IBKRDataService.__new__(ids.IBKRDataService)

    class Fake:
        def __init__(self, *_):
            pass

        def connect_to_ibkr(self, *_):
            return True

        def fetch_historical_data(self, *_):
            raise ids.HistoryServerDown("down")

        def disconnect_from_ibkr(self):
            pass

    monkeypatch.setattr(ids, "IBKRDataClient", Fake)
    with pytest.raises(ids.HistoryServerDown):
        svc.fetch_intraday_range("TSLA", datetime(2026, 10, 1), datetime(2026, 11, 1))
