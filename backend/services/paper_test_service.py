"""Start a paper test: send the parameters on the page to the trade-engine server.

One paper test runs per strategy. The server side is trade-engine's autotrader/papertest.py,
run here over SSH (the same key-based login as the IB tunnel, IBKR_SSH_TUNNEL):

    status   what runs now and what it holds (valued at IB's current prices)
    start    the rules' parameters + the algo_trading commit this backtest ran. If the strategy
             still holds positions the server refuses, unless close_out is true: then it closes
             them at the price available (from 09:35 New York time) and starts the new test.

The test is locked to the algo_trading commit checked out here, so shared/ must be committed
and pushed first: the server copies that commit's rules.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

ALGO_BASE_PATH = os.environ.get("ALGO_BASE_PATH", "C:/ALGO/algo_trading")
# TradingHub strategy id -> the strategy's name on the server
SERVER_NAMES = {"WHEEL": "wheel", "OPTIONS_MARTIN": "options_martin"}


class PaperTestError(Exception):
    pass


def _target() -> str:
    return (os.environ.get("TRADE_ENGINE_SSH") or os.environ.get("IBKR_SSH_TUNNEL") or "annie@192.168.0.219").strip()


def _server_dir() -> str:
    return os.environ.get("TRADE_ENGINE_DIR", "~/trade-engine")


def server_name(strategy_id: str) -> str:
    try:
        return SERVER_NAMES[strategy_id]
    except KeyError:
        raise PaperTestError(f"{strategy_id} can't run paper tests yet (only {', '.join(SERVER_NAMES)})")


def _ssh(command: str, stdin: Optional[dict] = None, timeout: int = 180) -> dict:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", _target(),
           f"cd {_server_dir()} && .venv/bin/python -m autotrader.papertest {command}"]
    logger.info("paper test: %s", " ".join(cmd))
    try:
        p = subprocess.run(cmd, input=json.dumps(stdin) if stdin is not None else "", capture_output=True,
                           text=True, timeout=timeout)
    except FileNotFoundError:
        raise PaperTestError("ssh not found on this PC: install the OpenSSH client")
    except subprocess.TimeoutExpired:
        raise PaperTestError(f"the server {_target()} did not answer within {timeout}s")
    lines = [line for line in p.stdout.strip().splitlines() if line.startswith("{")]
    if not lines:
        raise PaperTestError(f"server {_target()}: {(p.stderr or p.stdout).strip()[-400:] or 'no answer'}")
    out = json.loads(lines[-1])
    if out.get("error"):
        raise PaperTestError(out["error"])
    return out


# --- the rules' version ---------------------------------------------------------------
def _git(*args) -> str:
    p = subprocess.run(["git", "-C", ALGO_BASE_PATH, *args], capture_output=True, text=True, timeout=30)
    if p.returncode:
        raise PaperTestError(f"git {' '.join(args)} in {ALGO_BASE_PATH}: {p.stderr.strip()}")
    return p.stdout.strip()


def rules_commit() -> str:
    """The algo_trading commit the backtests here run. shared/ must have no uncommitted changes."""
    if _git("status", "--porcelain", "--", "shared"):
        raise PaperTestError("algo_trading/shared has uncommitted changes: commit and push them first, so the "
                             "paper test runs exactly the rules this backtest ran")
    return _git("rev-parse", "HEAD")


# --- parameters -------------------------------------------------------------------------
def rule_params(strategy_id: str, config: dict) -> dict:
    """Every rule parameter, from the page's settings (defaults filled in), validated by the rules."""
    if strategy_id == "WHEEL":
        from services.wheel_service import _rule_params, _tradekit
        Rules = _tradekit()[-1]
        config = dict(config)
        if "budget" not in config and config.get("initialBalance"):
            config["budget"] = config["initialBalance"]
    else:
        from services.options_martin_service import _rule_params, _tradekit
        Rules = _tradekit()[-1]
    try:
        return Rules(_rule_params(config, Rules)).p.as_dict()
    except ValueError as e:
        raise PaperTestError(str(e))


def backtest_settings(strategy_id: str, config: dict) -> dict:
    """The page's backtest-only settings, kept with the test for comparing later."""
    keep = ("strike_step", "slippage", "risk_free_rate", "fill_mode", "cash", "price_iv_mult", "iv_source",
            "fixed_iv")
    return {k: config[k] for k in keep if k in config}


# --- commands ---------------------------------------------------------------------------
def status(strategy_id: str, quotes: bool = True) -> dict:
    return _ssh(f"status {server_name(strategy_id)}" + (" --quotes" if quotes else ""), timeout=90)


def start(strategy_id: str, config: dict, dry_run: bool = False, close_out: bool = False, label: str = "") -> dict:
    payload = {
        "params": rule_params(strategy_id, config or {}),
        "rules_commit": rules_commit(),
        "dry_run": bool(dry_run),
        "close_out": bool(close_out),
        "label": label,
        "backtest": backtest_settings(strategy_id, config or {}),
        "source": "TradingHub",
    }
    return _ssh(f"start {server_name(strategy_id)}", payload)


def cancel(strategy_id: str) -> dict:
    return _ssh(f"cancel {server_name(strategy_id)}")
