"""Add SPY and VIX daily bars from before 2006 to TradingHub's database, so SPY backtests
(SPY Power Cashflow, Wheel on SPY) can start in 2000.

Why (checked 2026-11-15 on the paper IB Gateway): the DB's SPY and VIX daily bars started
2006-10-09, because TradingHub only ever asked IB for "20 Y" ending today. IB itself has
  - SPY TRADES daily bars from 1993 (its MIDPOINT bars, which TradingHub used, only from 2004),
  - VIX daily bars only from 2005-10-03.
So this script takes
  - VIX before that from CBOE's own daily history file (VIX_History.csv, from 1990), and
  - SPY from IB as TRADES bars, ending a few weeks after the DB's first bar.

Rows already in the database are KEPT: only dates the DB doesn't have are added. On the
dates both sources share, the script prints how far apart they are, as a sanity check.

Usage (Annie's PC, TradingHub's venv, IB Gateway reachable as in backend/services/.env):
    .venv\\Scripts\\python backend\\import_long_history.py --dry-run     only download and compare
    .venv\\Scripts\\python backend\\import_long_history.py               add the missing rows
    ... --from 1998-01-01     earliest date to add (default 1998-01-01: a 2000 start has warm-up)
    ... --vix-csv PATH        use a VIX_History.csv already downloaded instead of fetching it
    ... --only VIX            or SPY: just one of the two
    ... --client-id 78        IB API client id (avoid 17, 31, 32: trade-engine's bots)
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.request
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "services"))

from ibkr_data_service import ibkr_service, parse_ib_time  # noqa: E402

CBOE_VIX_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv"
OVERLAP_DAYS = 45   # SPY: ask IB for this many days past the DB's first bar, to compare


def parse_cboe_date(text: str) -> datetime:
    text = text.strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            pass
    raise ValueError(f"Unknown date format in the VIX file: {text!r}")


def read_cboe_vix(path: str = "") -> List[Dict]:
    """CBOE's VIX_History.csv (DATE,OPEN,HIGH,LOW,CLOSE) as bars in IB's format."""
    if path:
        with open(path, newline="") as f:
            text = f.read()
    else:
        print(f"Downloading {CBOE_VIX_URL}")
        req = urllib.request.Request(CBOE_VIX_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            text = r.read().decode("utf-8-sig")
    rows = []
    for r in csv.DictReader(io.StringIO(text)):
        r = {k.strip().upper(): v for k, v in r.items() if k}
        try:
            close = float(r["CLOSE"])
        except (KeyError, ValueError):
            continue
        if close <= 0:
            continue
        d = parse_cboe_date(r["DATE"])
        rows.append({"date": d.strftime("%Y%m%d"), "open": float(r.get("OPEN") or close),
                     "high": float(r.get("HIGH") or close), "low": float(r.get("LOW") or close),
                     "close": close, "volume": 0})
    if not rows:
        raise SystemExit("The VIX file had no rows I could read (expected DATE,OPEN,HIGH,LOW,CLOSE)")
    return rows


def compare(name: str, new_rows: List[Dict], db) -> None:
    """Print how far apart the new source and the DB are on the dates both have."""
    have = {ts.date(): float(c) for ts, c in db["close"].items()} if not db.empty else {}
    diffs = []
    for r in new_rows:
        d = parse_ib_time(str(r["date"])).date()
        if d in have and have[d] > 0:
            diffs.append((abs(float(r["close"]) - have[d]) / have[d], d, float(r["close"]), have[d]))
    if not diffs:
        print(f"  {name}: no dates in common with the DB to compare")
        return
    diffs.sort()
    worst = diffs[-1]
    mean = sum(x[0] for x in diffs) / len(diffs)
    print(f"  {name}: {len(diffs)} dates in common; close differs by {mean:.3%} on average, "
          f"at most {worst[0]:.3%} ({worst[1]}: new {worst[2]:.2f} vs DB {worst[3]:.2f})")


def import_one(symbol: str, rows: List[Dict], start: datetime, dry_run: bool) -> None:
    db = ibkr_service.get_data_from_db(symbol, "1900-01-01", "2100-01-01", "1 day")
    first = db.index.min() if not db.empty else None
    print(f"{symbol}: DB has {len(db)} daily bars" + (f" from {first:%Y-%m-%d}" if first is not None else ""))
    compare(f"{symbol} check", rows, db)
    have = set(db.index.date) if not db.empty else set()
    add = [r for r in rows if parse_ib_time(str(r["date"])) >= start
           and parse_ib_time(str(r["date"])).date() not in have]
    if add:
        span = f"{parse_ib_time(add[0]['date']):%Y-%m-%d} to {parse_ib_time(add[-1]['date']):%Y-%m-%d}"
    else:
        span = "nothing"
    print(f"  {symbol}: {len(add)} new daily bars to add ({span})")
    if add and not dry_run:
        n = ibkr_service.save_data_to_db(symbol, add, "1 day", keep_existing=True)
        print(f"  {symbol}: added {n} rows")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="start", default="1998-01-01")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--vix-csv", default="")
    ap.add_argument("--only", choices=("SPY", "VIX"))
    ap.add_argument("--client-id", type=int, default=78)
    a = ap.parse_args()
    if a.client_id in (17, 31, 32):
        raise SystemExit("Client ids 17, 31 and 32 belong to trade-engine's bots; pick another")
    start = datetime.strptime(a.start, "%Y-%m-%d")
    print("DRY RUN: nothing will be written" if a.dry_run else "Rows already in the DB are kept")

    if a.only in (None, "VIX"):
        rows = read_cboe_vix(a.vix_csv)
        print(f"CBOE VIX file: {len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}")
        import_one("VIX", rows, start, a.dry_run)

    if a.only in (None, "SPY"):
        db = ibkr_service.get_data_from_db("SPY", "1900-01-01", "2100-01-01", "1 day")
        first = db.index.min().to_pydatetime() if not db.empty else datetime.now()
        rows = ibkr_service.fetch_daily_before("SPY", first + timedelta(days=OVERLAP_DAYS), start,
                                               client_id=a.client_id)
        if not rows:
            raise SystemExit("IB returned no SPY bars")
        print(f"IB SPY TRADES: {len(rows)} days, {rows[0]['date']} to {rows[-1]['date']}")
        import_one("SPY", rows, start, a.dry_run)


if __name__ == "__main__":
    main()
