"""OPTIONS_MARTIN through TradingHub's service, with made-up 5-min bars instead of the database.

Needs algo_trading next to TradingHub (or ALGO_BASE_PATH pointing at it) for tradekit.
"""
import os
import sys
from datetime import datetime, time, timedelta

import pandas as pd
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("ALGO_BASE_PATH", os.path.join(HERE, "..", "..", "..", "algo_trading"))

from services import options_martin_service as oms  # noqa: E402

if not os.path.isdir(os.path.join(os.environ["ALGO_BASE_PATH"], "shared", "tradekit")):
    pytest.skip("algo_trading/shared not found", allow_module_level=True)


def fake_db(price=lambda d, i: 360.0, iv=0.40):
    """Stands in for _ensure_intraday: regular-hours 5-min bars on weekdays."""
    def ensure(name, start, end, interval):
        assert interval == "5 mins"
        rows, idx = [], []
        d = start
        while d <= end:
            if d.weekday() < 5:
                for i in range(78):
                    t = datetime.combine(d.date(), time(9, 30)) + timedelta(minutes=5 * i)
                    v = (iv(d, i) if callable(iv) else iv) if name.endswith("_IV") else price(d, i)
                    idx.append(t)
                    rows.append({"open": v, "high": v, "low": v, "close": v, "volume": 100})
            d += timedelta(days=1)
        return pd.DataFrame(rows, index=pd.DatetimeIndex(idx))
    return ensure


def test_params_come_from_the_shared_rules():
    out = oms.options_martin_params()
    names = [p["name"] for p in out["rules"]]
    assert "round_budget" in names and "take_profit_of" in names
    assert out["backtest"]["strike_step"] == 2.5
    preset = out["presets"]["paper_bot"]
    assert set(preset) <= set(names)                       # every preset key is a real rule parameter


def test_paper_bot_settings_run_one_round_a_week(monkeypatch):
    monkeypatch.setattr(oms, "_ensure_intraday", fake_db())
    out = oms.run_options_martin_kit(dict(oms.PAPER_BOT), datetime(2026, 11, 2), datetime(2026, 11, 13))
    meta = out.pop("__metadata__")
    assert sorted(out)[0] == "2026-11-02" and sorted(out)[-1] == "2026-11-13"
    rounds = meta["options_martin_rounds"]
    assert len(rounds) == 2 and all(r["exit"] == "END OF DAY" for r in rounds)
    assert rounds[0]["contract"] == "TSLA 395C 2026-11-06"     # ~10% above $360, that Friday
    assert out["2026-11-02"]["Trading_Log"].startswith("09:35 BUY")
    assert out["2026-11-02"]["Contracts"] > 0 and out["2026-11-06"]["Contracts"] == 0
    assert meta["options_martin_summary"]["rounds"] == 2
    assert meta["data_notes"]["bars"] == 10 * 78


def test_out_of_range_setting_is_a_settings_error(monkeypatch):
    monkeypatch.setattr(oms, "_ensure_intraday", fake_db())
    with pytest.raises(ValueError):
        oms.run_options_martin_kit(dict(oms.PAPER_BOT, otm_pct=0.5), datetime(2026, 11, 2), datetime(2026, 11, 6))


def test_strings_from_the_page_are_converted():
    from tradekit.rules.options_martin import OptionsMartin
    got = oms._rule_params({"round_budget": "1900", "max_top_ups": "4.0", "weekly_only": "true",
                            "underlying": "tsla", "otm_pct": ""}, OptionsMartin)
    assert got == {"round_budget": 1900.0, "max_top_ups": 4, "weekly_only": True, "underlying": "TSLA"}


def test_holes_inside_the_cached_bars_are_downloaded(monkeypatch):
    """Two earlier runs over separate months leave a hole in the middle: fetch it too."""
    import types
    days = [d for d in pd.bdate_range("2026-01-05", "2026-01-30").append(pd.bdate_range("2026-06-01", "2026-06-30"))]
    have = pd.DatetimeIndex([d + pd.Timedelta(hours=9, minutes=30) for d in days])
    df = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}, index=have)
    fetched = []
    fake = types.SimpleNamespace(get_data_from_db=lambda *a: df,
                                 fetch_intraday_range=lambda name, a, b, i: fetched.append((a.date(), b.date())))
    monkeypatch.setitem(sys.modules, "ibkr_data_service", types.SimpleNamespace(ibkr_service=fake))
    oms._ensure_intraday("TSLA", datetime(2026, 1, 5), datetime(2026, 6, 30), "5 mins")
    assert fetched == [(datetime(2026, 1, 30).date(), datetime(2026, 6, 1).date())]   # Jan 30 -> Jun 1
