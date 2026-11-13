"""import_research_data.py: research CSVs -> market_data / option_quotes.

The parsing tests run anywhere. The database test needs a PostgreSQL you can throw away:
set TEST_DB_NAME (and DB_USER / DB_PASSWORD / DB_HOST if needed); it is skipped otherwise.
"""
import json
import os
import sys
import types
from datetime import datetime

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "services"))

try:  # ibkr_data_service imports ibapi; the import doesn't need IB itself
    import ibapi  # noqa: F401
except ImportError:
    for name in ("ibapi", "ibapi.client", "ibapi.contract", "ibapi.wrapper"):
        sys.modules[name] = types.ModuleType(name)
    sys.modules["ibapi.client"].EClient = type("EClient", (), {"__init__": lambda self, w: None})
    sys.modules["ibapi.contract"].Contract = type("Contract", (), {})
    sys.modules["ibapi.wrapper"].EWrapper = type("EWrapper", (), {})

import import_research_data as ird  # noqa: E402

CSV_HEAD = "time,open,high,low,close,volume\n"


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


@pytest.fixture
def data(tmp_path):
    # NFLX daily with an unadjusted 10:1 split between the 2nd and 3rd day
    write(tmp_path / "NFLX_1d.csv", CSV_HEAD + "20251113,1100,1110,1090,1105,100\n"
          "20251114,1105,1120,1100,1110,100\n20251117,111,112,110,111.5,1000\n")
    write(tmp_path / "NFLX_iv_1d.csv", CSV_HEAD + "20251113,0.30,0.31,0.29,0.30,0\n20251114,0.31,0.32,0.30,0.31,0\n")
    write(tmp_path / "NFLX_5m.csv", CSV_HEAD + "20251117  09:30:00,111,112,110,111.5,50\n"
          "20251117  09:35:00,111.5,112,111,111.8,40\n")
    write(tmp_path / "NFLX_iv_5m.csv", CSV_HEAD + "20251117  09:30:00,0.3,0.3,0.3,0.3,0\n")
    calib = {"symbol": "NFLX",
             "stock": [["20261029  09:30:00", 64, 65, 63, 64.5]],
             "iv": [["20261029  09:30:00", 0.36, 0.37, 0.35, 0.36]],
             "options": {"call": {"expiry": "2026-11-20", "strike": 70.0, "right": "C",
                                  "bid_ask": [["20261029  09:30:00", 1.0, 1.2, 0.9, 1.1],
                                              ["20261029  10:00:00", 1.1, 1.3, 1.0, 1.2]]}}}
    write(tmp_path / "calib_NFLX.json", json.dumps(calib))
    return tmp_path


def test_reads_names_intervals_and_undoes_the_split(data):
    sets = {(s["symbol"], s["interval"]): s for s in ird.research_sets(str(data))}
    assert set(sets) == {("NFLX", "1 day"), ("NFLX_IV", "1 day"), ("NFLX", "5 mins"), ("NFLX_IV", "5 mins")}
    daily = sets[("NFLX", "1 day")]
    assert daily["splits"] == [("2025-11-17 00:00:00", 10)]
    assert [round(r[4], 2) for r in daily["rows"]] == [110.5, 111.0, 111.5]
    assert daily["rows"][0][5] == 1000  # volume scaled up by the split
    assert sets[("NFLX_IV", "1 day")]["rows"][0][4] == 0.30  # IV is never split adjusted
    assert sets[("NFLX", "5 mins")]["rows"][0][0] == datetime(2025, 11, 17, 9, 30)


def test_only_filter(data):
    assert ird.research_sets(str(data), {"TSLA"}) == []


def test_calibration_file(data):
    bars, quotes = ird.calib_sets(str(data))
    assert {(b["symbol"], b["interval"]) for b in bars} == {("NFLX", "30 mins"), ("NFLX_IV", "30 mins")}
    assert len(quotes) == 1 and quotes[0]["strike"] == 70.0 and len(quotes[0]["rows"]) == 2


@pytest.mark.skipif(not os.environ.get("TEST_DB_NAME"), reason="set TEST_DB_NAME to a scratch PostgreSQL db")
def test_database_fill_gaps_only(data, monkeypatch, capsys):
    import ibkr_data_service as ids

    monkeypatch.setitem(ids.DB_CONFIG, "dbname", os.environ["TEST_DB_NAME"])
    svc = ids.IBKRDataService()
    svc.create_market_data_table()
    conn = svc.get_db_connection()
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS option_quotes")
        cur.execute("DELETE FROM market_data WHERE symbol LIKE 'NFLX%%'")
        # a bar TradingHub already has: must be kept as it is
        cur.execute("INSERT INTO market_data (symbol, date, open, high, low, close, volume, bar_interval) "
                    "VALUES ('NFLX', '2025-11-14', 1, 1, 1, 99, 0, '1 day')")
    conn.commit()

    assert ird.main([str(data), "--dry-run"]) == 0
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM market_data WHERE symbol LIKE 'NFLX%%'")
        assert cur.fetchone()[0] == 1  # dry run wrote nothing

    assert ird.main([str(data)]) == 0
    assert ird.main([str(data)]) == 0  # a second run adds nothing
    out = capsys.readouterr().out
    assert "Added 0 bars" in out.splitlines()[-1]
    with conn.cursor() as cur:
        cur.execute("SELECT bar_interval, count(*) FROM market_data WHERE symbol LIKE 'NFLX%%' GROUP BY 1")
        assert dict(cur.fetchall()) == {"1 day": 5, "5 mins": 3, "30 mins": 2}
        cur.execute("SELECT close FROM market_data WHERE symbol = 'NFLX' AND date = '2025-11-14'")
        assert float(cur.fetchone()[0]) == 99  # kept
        cur.execute("SELECT count(*) FROM option_quotes WHERE underlying = 'NFLX'")
        assert cur.fetchone()[0] == 2
    conn.close()
