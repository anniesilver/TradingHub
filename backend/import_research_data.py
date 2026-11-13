"""Load price and IV history downloaded by the ticker research into TradingHub's database.

The research (thread "Find best tickers for WHEEL and OPTIONS_MARTIN", 2026-11-12) pulled
from IB paper, for 27 tickers, into C:\\ALGO\\Claude\\ticker-research\\data:

    <T>_1d.csv       daily stock bars (TRADES, regular hours)      -> market_data  T      '1 day'
    <T>_iv_1d.csv    daily 30-day implied volatility               -> market_data  T_IV   '1 day'
    <T>_5m.csv       5-minute stock bars                           -> market_data  T      '5 mins'
    <T>_iv_5m.csv    5-minute 30-day implied volatility            -> market_data  T_IV   '5 mins'
    calib_<T>.json   ~10 days of 30-minute bars: stock, IV, and the real BID_ASK of one
                     call and one put                              -> market_data  T, T_IV '30 mins'
                                                                      option_quotes (new table)

These are the names and intervals the WHEEL and OPTIONS_MARTIN backtests read, so a later
backtest finds the data here and only downloads what is still missing.

Rows already in the database are KEPT (Annie, 2026-11-13: fill gaps only, never overwrite).
Stock prices get a split check: a jump between two bars that matches a split ratio
(2:1, 3:1, ... 50:1, or the reverse) divides every earlier price by it, so prices before a
split line up with prices after it (NFLX's 10:1 split in Nov 2025 came in unadjusted once).

Usage (Annie's PC, TradingHub's venv):
    .venv\\Scripts\\python backend\\import_research_data.py C:\\ALGO\\Claude\\ticker-research\\data
    ... --dry-run      only count what would be added
    ... --only TSLA,META
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

from ibkr_data_service import parse_ib_time  # noqa: E402  (same time parsing as IB downloads)

FILES = (  # file suffix -> (symbol suffix, bar_interval, is a stock price)
    ("_1d.csv", "", "1 day", True),
    ("_iv_1d.csv", "_IV", "1 day", False),
    ("_5m.csv", "", "5 mins", True),
    ("_iv_5m.csv", "_IV", "5 mins", False),
)
SPLIT_RATIOS = (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50)

Row = Tuple[datetime, float, float, float, float, int]  # time, open, high, low, close, volume

OPTION_QUOTES_SQL = """
    CREATE TABLE IF NOT EXISTS option_quotes (
        id SERIAL PRIMARY KEY,
        underlying VARCHAR(10) NOT NULL,
        expiry DATE NOT NULL,
        strike DECIMAL(10, 4) NOT NULL,
        option_right CHAR(1) NOT NULL,
        date TIMESTAMP NOT NULL,
        bar_interval VARCHAR(20) NOT NULL,
        what VARCHAR(20) NOT NULL,
        open DECIMAL(12, 4),
        high DECIMAL(12, 4),
        low DECIMAL(12, 4),
        close DECIMAL(12, 4),
        source VARCHAR(80),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (underlying, expiry, strike, option_right, date, bar_interval, what)
    )
"""


# --- reading -------------------------------------------------------------------------------
def read_csv(path: str) -> List[Row]:
    out = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            vol = r.get("volume") or 0
            out.append((parse_ib_time(r["time"]), float(r["open"]), float(r["high"]), float(r["low"]),
                        float(r["close"]), int(float(vol)) if float(vol) > 0 else 0))
    return out


def bars_from_lists(rows: Iterable[list]) -> List[Row]:
    """calib_<T>.json bars: [time, open, high, low, close] (no volume)."""
    return [(parse_ib_time(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), 0) for r in rows]


def split_adjust(rows: List[Row]) -> Tuple[List[Row], List[Tuple[str, float]]]:
    """Undo stock splits missing from the bars. Returns (rows, [(first bar after split, ratio)])."""
    rows = sorted(rows)
    found = []
    for i in range(len(rows) - 1, 0, -1):
        prev_c, o = rows[i - 1][4], rows[i][1]
        if o <= 0 or prev_c <= 0:
            continue
        q = prev_c / o
        for n in SPLIT_RATIOS:
            if abs(q / n - 1) < 0.06 or abs(q * n - 1) < 0.06:
                k = n if q > 1 else 1.0 / n
                found.append((rows[i][0].isoformat(sep=" "), round(k, 4)))
                rows[:i] = [(d, a / k, b / k, c / k, e / k, int(v * k)) for d, a, b, c, e, v in rows[:i]]
                break
    return rows, found


def research_sets(data_dir: str, only: Optional[set] = None) -> List[dict]:
    """Everything in the folder, as [{symbol, interval, rows, file, splits}]."""
    names = sorted(os.listdir(data_dir))
    tickers = sorted({m.group(1) for n in names if (m := re.fullmatch(r"([A-Z.]+)_1d\.csv", n))})
    sets = []
    for t in tickers:
        if only and t not in only:
            continue
        for suffix, sym_suffix, interval, is_price in FILES:
            path = os.path.join(data_dir, t + suffix)
            if not os.path.exists(path):
                continue
            rows, splits = read_csv(path), []
            if is_price:
                rows, splits = split_adjust(rows)
            sets.append({"symbol": t + sym_suffix, "interval": interval, "rows": rows,
                         "file": os.path.basename(path), "splits": splits})
    return sets


def calib_sets(data_dir: str, only: Optional[set] = None) -> Tuple[List[dict], List[dict]]:
    """calib_<T>.json -> (market_data sets at 30 mins, option quote sets)."""
    bars, quotes = [], []
    for n in sorted(os.listdir(data_dir)):
        m = re.fullmatch(r"calib_([A-Z.]+)\.json", n)
        if not m or (only and m.group(1) not in only):
            continue
        with open(os.path.join(data_dir, n)) as f:
            d = json.load(f)
        t = d.get("symbol") or m.group(1)
        if d.get("stock"):
            bars.append({"symbol": t, "interval": "30 mins", "rows": bars_from_lists(d["stock"]), "file": n,
                         "splits": []})
        if d.get("iv"):
            bars.append({"symbol": t + "_IV", "interval": "30 mins", "rows": bars_from_lists(d["iv"]), "file": n,
                         "splits": []})
        for leg in (d.get("options") or {}).values():
            if not leg or not leg.get("bid_ask"):
                continue
            quotes.append({"underlying": t, "expiry": leg["expiry"], "strike": float(leg["strike"]),
                           "right": leg["right"], "interval": "30 mins", "what": "BID_ASK",
                           "rows": bars_from_lists(leg["bid_ask"]), "file": n})
    return bars, quotes


# --- writing -------------------------------------------------------------------------------
def existing_times(cur, symbol: str, interval: str) -> set:
    cur.execute("SELECT date FROM market_data WHERE symbol = %s AND bar_interval = %s", (symbol, interval))
    return {r[0] for r in cur.fetchall()}


def insert_bars(cur, s: dict, dry_run: bool) -> Tuple[int, int]:
    """Add the bars that aren't there yet. Returns (added, already there)."""
    have = existing_times(cur, s["symbol"], s["interval"])
    new = [r for r in s["rows"] if r[0] not in have]
    if new and not dry_run:
        from psycopg2.extras import execute_values

        execute_values(cur, """
            INSERT INTO market_data (symbol, date, open, high, low, close, volume, bar_interval)
            VALUES %s ON CONFLICT (symbol, date, bar_interval) DO NOTHING""",
            [(s["symbol"], d, round(o, 4), round(h, 4), round(lo, 4), round(c, 4), v, s["interval"])
             for d, o, h, lo, c, v in new], page_size=2000)
    return len(new), len(s["rows"]) - len(new)


def insert_quotes(cur, q: dict, dry_run: bool) -> int:
    """Add one option's quotes that aren't there yet. Returns how many were added."""
    key = (q["underlying"], q["expiry"], q["strike"], q["right"], q["interval"], q["what"])
    cur.execute("""SELECT date FROM option_quotes WHERE underlying = %s AND expiry = %s AND strike = %s
                   AND option_right = %s AND bar_interval = %s AND what = %s""", key)
    have = {r[0] for r in cur.fetchall()}
    new = [r for r in q["rows"] if r[0] not in have]
    if new and not dry_run:
        from psycopg2.extras import execute_values

        execute_values(cur, """
            INSERT INTO option_quotes (underlying, expiry, strike, option_right, date, bar_interval, what,
                                       open, high, low, close, source)
            VALUES %s ON CONFLICT DO NOTHING""",
            [(q["underlying"], q["expiry"], q["strike"], q["right"], d, q["interval"], q["what"], o, h, lo, c,
              "ticker research " + q["file"]) for d, o, h, lo, c, _ in new], page_size=2000)
    return len(new)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("data_dir")
    ap.add_argument("--dry-run", action="store_true", help="only count what would be added")
    ap.add_argument("--only", help="comma-separated tickers, e.g. TSLA,META")
    args = ap.parse_args(argv)
    only = set(args.only.upper().split(",")) if args.only else None

    sets = research_sets(args.data_dir, only)
    calib_bars, quotes = calib_sets(args.data_dir, only)
    if not sets and not calib_bars:
        print(f"Nothing to import in {args.data_dir}")
        return 1

    from ibkr_data_service import IBKRDataService

    service = IBKRDataService()
    service.create_market_data_table()
    conn = service.get_db_connection()
    total_new = total_old = total_q = 0
    try:
        with conn.cursor() as cur:
            cur.execute(OPTION_QUOTES_SQL)
            for s in sets + calib_bars:
                added, had = insert_bars(cur, s, args.dry_run)
                total_new, total_old = total_new + added, total_old + had
                first, last = (s["rows"][0][0], s["rows"][-1][0]) if s["rows"] else (None, None)
                note = f"  split adjusted {s['splits']}" if s["splits"] else ""
                print(f"{s['symbol']:<9} {s['interval']:<8} {first:%Y-%m-%d}..{last:%Y-%m-%d}  "
                      f"added {added:>6}, already there {had:>6}{note}")
            for q in quotes:
                n = insert_quotes(cur, q, args.dry_run)
                total_q += n
                print(f"{q['underlying']:<9} {q['expiry']} {q['strike']:g}{q['right']} BID_ASK  {n} quotes")
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    finally:
        conn.close()
    verb = "Would add" if args.dry_run else "Added"
    print(f"\n{verb} {total_new} bars ({total_old} were already in the database) and {total_q} option quotes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
