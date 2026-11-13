"""Paper test history: the server's tests copied into paper_tests / paper_test_trades.

Needs a PostgreSQL you can throw away: set TEST_DB_NAME (and DB_USER / DB_PASSWORD / DB_HOST
if needed); skipped otherwise."""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DB_NAME"), reason="set TEST_DB_NAME to a scratch db")


@pytest.fixture
def conn():
    import psycopg2

    c = psycopg2.connect(dbname=os.environ["TEST_DB_NAME"], user=os.environ.get("DB_USER"),
                         password=os.environ.get("DB_PASSWORD"), host=os.environ.get("DB_HOST", "localhost"))
    with c.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS paper_tests, paper_test_trades")
    c.commit()
    yield c
    c.close()


def trade(time, side, qty, price, kind="fill"):
    return {"time": time, "mode": "PAPER", "side": side, "qty": qty, "contract": "TSLA 397.5C 11-13",
            "price": price, "multiplier": 100, "reason": "", "kind": kind}


def running_old_setup():
    return {"strategy": "options_martin", "id": "current-old-setup", "status": "running", "legacy": True,
            "label": "old setup (before paper tests)", "started": "2026-10-29 09:31:14-04:00", "ended": None,
            "params": {"otm_pct": 0.1}, "param_periods": [{"mode": "PAPER", "params": {"otm_pct": 0.1}}],
            "results": {"PAPER": {"realized": 598.2}},
            "trades": [trade("2026-11-09T09:45:12-05:00", "BUY", 1, 2.48),
                       trade("2026-11-11T09:35:00-05:00", "SELL", 1, 3.45)]}


def test_save_and_list(conn):
    from services import paper_test_history_service as h

    h.save([running_old_setup(),
            {"strategy": "tsla_calls", "id": "legacy-20261028", "status": "finished", "legacy": True,
             "started": "2026-10-28T09:31:03-04:00", "ended": "2026-10-28T15:52:00-04:00",
             "results": {"PAPER": {"realized": -203.3}}, "trades": []}], conn)
    tests = h.list_tests(conn=conn, with_trades=True)
    assert [t["id"] for t in tests] == ["current-old-setup", "legacy-20261028"]  # running first
    om = tests[0]
    assert om["legacy"] and om["params"] == {"otm_pct": 0.1} and float(om["paper_realized"]) == 598.2
    assert [x["side"] for x in om["trades"]] == ["BUY", "SELL"] and om["trade_count"] == 2
    assert [t["id"] for t in h.list_tests("tsla_calls", conn=conn)] == ["legacy-20261028"]


def test_running_row_replaced_when_the_test_finishes(conn):
    from services import paper_test_history_service as h

    h.save([running_old_setup()], conn)
    h.save([running_old_setup()], conn)  # syncing twice keeps one row
    finished = dict(running_old_setup(), id="before-paper-tests-20261116", status="finished",
                    ended="2026-11-16T09:35:00-05:00")
    new = {"strategy": "options_martin", "id": "20261116-0935-5pct", "status": "running", "legacy": False,
           "label": "5% OTM", "started": "2026-11-16T09:35:00-05:00", "rules_commit": "abc123", "trades": []}
    h.save([finished, new], conn)
    tests = h.list_tests("options_martin", conn=conn, with_trades=True)
    assert [(t["id"], t["status"]) for t in tests] == [("20261116-0935-5pct", "running"),
                                                       ("before-paper-tests-20261116", "finished")]
    assert len(tests[1]["trades"]) == 2
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM paper_test_trades")
        assert cur.fetchone()[0] == 2
