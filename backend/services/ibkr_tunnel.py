"""Keep an SSH tunnel open to IB Gateway on the trade-engine server.

The Gateway there only listens on the server's own 127.0.0.1:4002. When
IBKR_SSH_TUNNEL is set (e.g. annie@192.168.0.219), ensure_tunnel() starts
`ssh -N -L <port>:localhost:<port> <target>` in the background if nothing is
listening on the local port yet. Needs key-based SSH login (no password prompt).
"""

import atexit
import logging
import os
import socket
import subprocess
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_proc = None


def _port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _stop():
    if _proc and _proc.poll() is None:
        _proc.terminate()


def ensure_tunnel(host: str, port: int, timeout: float = 10.0) -> bool:
    """Start the SSH tunnel if IBKR_SSH_TUNNEL is set and the local port is closed."""
    global _proc
    target = os.environ.get("IBKR_SSH_TUNNEL", "").strip()
    if not target or host not in ("127.0.0.1", "localhost"):
        return True
    with _lock:
        if _port_open(host, port):
            return True
        if _proc is None or _proc.poll() is not None:
            cmd = [
                "ssh", "-N",
                "-L", f"{port}:localhost:{port}",
                "-o", "BatchMode=yes",
                "-o", "ExitOnForwardFailure=yes",
                "-o", "ServerAliveInterval=30",
                "-o", "ConnectTimeout=5",
                target,
            ]
            logger.info(f"Opening SSH tunnel to IB Gateway: {' '.join(cmd)}")
            try:
                _proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                         stderr=subprocess.PIPE)
            except FileNotFoundError:
                logger.error("ssh not found; install the OpenSSH client")
                return False
            atexit.register(_stop)
        deadline = time.time() + timeout
        while time.time() < deadline:
            if _port_open(host, port):
                return True
            if _proc.poll() is not None:
                err = _proc.stderr.read().decode(errors="replace").strip() if _proc.stderr else ""
                logger.error(f"SSH tunnel to {target} exited: {err}")
                return False
            time.sleep(0.25)
        logger.error(f"SSH tunnel to {target} did not open port {port} within {timeout}s")
        return False
