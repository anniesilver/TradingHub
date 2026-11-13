"""Every paper test so far, kept in TradingHub's database for listing and comparing with backtests.

The trade-engine server is the source: each test's files live there (state/<name>/tests/<id>/,
see trade-engine autotrader/test_history.py). `sync()` asks it for all tests over SSH
(`papertest history`) and copies them here:

    paper_tests        one row per test: strategy, id, label, running/finished, legacy (from before
                       the Start paper test button), dates, params, param_periods (legacy runs whose
                       settings were changed by hand), rules commit, backtest settings, results per
                       mode (PAPER / DRY RUN)
    paper_test_trades  every fill, settlement (expiry/assignment) and book correction of each test

A running test's row is replaced on every sync. When it finishes, it gets a new id on the
server (tests/<id>/), so the running row is dropped and the finished one added.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from psycopg2.extras import Json, RealDictCursor, execute_values

logger = logging.getLogger(__name__)

TABLES_SQL = """
    CREATE TABLE IF NOT EXISTS paper_tests (
        id SERIAL PRIMARY KEY,
        strategy VARCHAR(40) NOT NULL,
        test_id VARCHAR(120) NOT NULL,
        label TEXT,
        status VARCHAR(12) NOT NULL,
        legacy BOOLEAN NOT NULL DEFAULT FALSE,
        started TIMESTAMPTZ,
        ended TIMESTAMPTZ,
        end_reason TEXT,
        dry_run BOOLEAN,
        rules_commit VARCHAR(40),
        params JSONB,
        param_periods JSONB,
        backtest JSONB,
        results JSONB,
        paper_realized DECIMAL(14, 2),
        trade_count INTEGER,
        synced_at TIMESTAMPTZ DEFAULT now(),
        UNIQUE (strategy, test_id)
    );
    CREATE TABLE IF NOT EXISTS paper_test_trades (
        id SERIAL PRIMARY KEY,
        strategy VARCHAR(40) NOT NULL,
        test_id VARCHAR(120) NOT NULL,
        time TIMESTAMPTZ,
        mode VARCHAR(10),
        side VARCHAR(4),
        qty INTEGER,
        contract VARCHAR(60),
        price DECIMAL(12, 4),
        multiplier INTEGER,
        reason TEXT,
        kind VARCHAR(12)
    );
    CREATE INDEX IF NOT EXISTS idx_paper_test_trades_test ON paper_test_trades (strategy, test_id);
"""


def _conn():
    from services.ibkr_data_service import ibkr_service

    return ibkr_service.get_db_connection()


def create_tables(conn=None):
    own = conn is None
    conn = conn or _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(TABLES_SQL)
        conn.commit()
    finally:
        if own:
            conn.close()


def _paper_realized(results: Optional[dict]):
    paper = (results or {}).get("PAPER") or {}
    return paper.get("realized")


def save(tests: List[dict], conn=None) -> dict:
    """Write the server's tests into the tables. Returns counts."""
    own = conn is None
    conn = conn or _conn()
    try:
        create_tables(conn)
        with conn.cursor() as cur:
            for strategy in {t["strategy"] for t in tests}:  # running rows are always replaced
                cur.execute("SELECT test_id FROM paper_tests WHERE strategy = %s AND status = 'running'", (strategy,))
                for (tid,) in cur.fetchall():
                    cur.execute("DELETE FROM paper_test_trades WHERE strategy = %s AND test_id = %s", (strategy, tid))
                    cur.execute("DELETE FROM paper_tests WHERE strategy = %s AND test_id = %s", (strategy, tid))
            for t in tests:
                trades = t.get("trades") or []
                cur.execute("""
                    INSERT INTO paper_tests (strategy, test_id, label, status, legacy, started, ended, end_reason,
                        dry_run, rules_commit, params, param_periods, backtest, results, paper_realized, trade_count)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (strategy, test_id) DO UPDATE SET
                        label = EXCLUDED.label, status = EXCLUDED.status, legacy = EXCLUDED.legacy,
                        started = EXCLUDED.started, ended = EXCLUDED.ended, end_reason = EXCLUDED.end_reason,
                        dry_run = EXCLUDED.dry_run, rules_commit = EXCLUDED.rules_commit, params = EXCLUDED.params,
                        param_periods = EXCLUDED.param_periods, backtest = EXCLUDED.backtest,
                        results = EXCLUDED.results, paper_realized = EXCLUDED.paper_realized,
                        trade_count = EXCLUDED.trade_count, synced_at = now()
                """, (t["strategy"], t["id"], t.get("label"), t.get("status", "finished"), bool(t.get("legacy")),
                      t.get("started"), t.get("ended"), t.get("end_reason"), t.get("dry_run"), t.get("rules_commit"),
                      Json(t.get("params") or {}), Json(t.get("param_periods") or []), Json(t.get("backtest") or {}),
                      Json(t.get("results") or {}), _paper_realized(t.get("results")), len(trades)))
                cur.execute("DELETE FROM paper_test_trades WHERE strategy = %s AND test_id = %s",
                            (t["strategy"], t["id"]))
                if trades:
                    execute_values(cur, """
                        INSERT INTO paper_test_trades (strategy, test_id, time, mode, side, qty, contract, price,
                                                       multiplier, reason, kind) VALUES %s""",
                        [(t["strategy"], t["id"], x.get("time"), x.get("mode"), x.get("side"), x.get("qty"),
                          x.get("contract"), x.get("price"), x.get("multiplier"), x.get("reason"), x.get("kind"))
                         for x in trades])
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if own:
            conn.close()
    return {"tests": len(tests), "trades": sum(len(t.get("trades") or []) for t in tests)}


def sync() -> dict:
    """Copy every test from the trade-engine server into the database."""
    from services.paper_test_service import _ssh

    tests = _ssh("history", timeout=120).get("tests") or []
    return save(tests)


def list_tests(strategy: Optional[str] = None, with_trades: bool = False, conn=None) -> List[dict]:
    """Tests from the database, newest first. strategy: the server name (wheel, options_martin)."""
    own = conn is None
    conn = conn or _conn()
    try:
        create_tables(conn)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""SELECT strategy, test_id AS id, label, status, legacy, started, ended, end_reason,
                                  dry_run, rules_commit, params, param_periods, backtest, results, paper_realized,
                                  trade_count, synced_at
                           FROM paper_tests WHERE (%s IS NULL OR strategy = %s)
                           ORDER BY status = 'running' DESC, started DESC NULLS LAST""", (strategy, strategy))
            tests = [dict(r) for r in cur.fetchall()]
            if with_trades:
                for t in tests:
                    cur.execute("""SELECT time, mode, side, qty, contract, price, multiplier, reason, kind
                                   FROM paper_test_trades WHERE strategy = %s AND test_id = %s ORDER BY time, id""",
                                (t["strategy"], t["id"]))
                    t["trades"] = [dict(r) for r in cur.fetchall()]
        return json.loads(json.dumps(tests, default=str))  # dates/decimals -> plain JSON
    finally:
        if own:
            conn.close()
