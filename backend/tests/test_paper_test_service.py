"""Start paper test: what TradingHub sends to the trade-engine server (SSH is faked)."""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
os.environ.setdefault("ALGO_BASE_PATH", os.path.join(HERE, "..", "..", "..", "algo_trading"))

from services import paper_test_service as pts  # noqa: E402

if not os.path.isdir(os.path.join(os.environ["ALGO_BASE_PATH"], "shared", "tradekit")):
    pytest.skip("algo_trading/shared not found", allow_module_level=True)


class FakeRun:
    def __init__(self, answer, porcelain=""):
        self.answer, self.porcelain, self.calls = answer, porcelain, []

    def __call__(self, cmd, input=None, **kw):
        if cmd[0] == "git":
            out = self.porcelain if "status" in cmd else "abc1234def5678"
            return subprocess.CompletedProcess(cmd, 0, out, "")
        self.calls.append((cmd, json.loads(input) if input else None))
        return subprocess.CompletedProcess(cmd, 0, "noise\n" + json.dumps(self.answer) + "\n", "")


def test_start_sends_every_rule_param_the_commit_and_the_choices(monkeypatch):
    fake = FakeRun({"ok": True, "waiting": False, "message": "started"})
    monkeypatch.setattr(pts.subprocess, "run", fake)
    monkeypatch.setenv("TRADE_ENGINE_SSH", "annie@server")
    out = pts.start("WHEEL", {"underlying": "AMZN", "budget": 30000, "put_otm_pct": 0.07, "slippage": 0.02},
                    dry_run=True, label="7%")
    assert out["ok"]
    [(cmd, payload)] = fake.calls
    assert cmd[:4] == ["ssh", "-o", "BatchMode=yes", "-o"] and "annie@server" in cmd
    assert cmd[-1].endswith("autotrader.papertest start wheel")
    assert payload["params"]["underlying"] == "AMZN" and payload["params"]["put_otm_pct"] == 0.07
    assert "min_premium" in payload["params"]  # defaults are sent too: the test is exact
    assert "slippage" not in payload["params"] and payload["backtest"] == {"slippage": 0.02}
    assert payload["rules_commit"] == "abc1234def5678" and payload["dry_run"] and not payload["close_out"]


def test_refuses_uncommitted_rules_bad_params_and_unknown_strategies(monkeypatch):
    monkeypatch.setattr(pts.subprocess, "run", FakeRun({}, porcelain=" M shared/tradekit/rules/wheel.py"))
    with pytest.raises(pts.PaperTestError, match="uncommitted"):
        pts.start("WHEEL", {"underlying": "AMZN", "budget": 30000})
    monkeypatch.setattr(pts.subprocess, "run", FakeRun({}))
    with pytest.raises(pts.PaperTestError):
        pts.start("WHEEL", {"underlying": "AMZN", "budget": 30000, "put_otm_pct": 5})
    with pytest.raises(pts.PaperTestError, match="can't run paper tests"):
        pts.start("SPY_POWER_CASHFLOW", {})


def test_server_errors_come_back_as_messages(monkeypatch):
    monkeypatch.setattr(pts.subprocess, "run", FakeRun({"ok": False, "error": "push algo_trading first"}))
    with pytest.raises(pts.PaperTestError, match="push algo_trading first"):
        pts.status("OPTIONS_MARTIN")


def test_routes_refuse_other_websites(monkeypatch):
    simple_app = pytest.importorskip("simple_app", reason="needs the full backend environment (ibapi, psycopg2)")

    monkeypatch.setattr(pts.subprocess, "run", FakeRun({"ok": True, "message": "dropped"}))
    client = simple_app.app.test_client()
    bad = client.post("/api/paper-test/WHEEL/cancel", headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403
    ok = client.post("/api/paper-test/WHEEL/cancel", headers={"Origin": "http://localhost:3000"})
    assert ok.status_code == 200 and ok.get_json()["message"] == "dropped"
