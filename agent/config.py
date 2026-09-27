"""Paths, logging and small OS-integration helpers for the DT Print Agent.

Kept dependency-light on purpose: autostart uses the stdlib `winreg` module
rather than pywin32, so the only Windows-specific runtime dependency the
agent actually needs is pystray (for the tray icon) and pyusb/libusb (for
talking to the printer).
"""
import json
import logging
import os
import socket
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_NAME = "DigitalTouch Print Agent"
PORT = 9153
LOCK_PORT = 9154  # separate port held for the process lifetime, purely as a singleton guard
HOST = "127.0.0.1"

# Origins allowed to POST print jobs. Add any other domains the POS is
# served from (e.g. a staging URL) here.
ALLOWED_ORIGINS = [
    "https://apps.digitaltouch.co.zw",
    "https://digitaltouch.duckdns.org",
    "http://localhost",
    "http://127.0.0.1",
]


def app_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    p = Path(base) / "DigitalTouch" / "PrintAgent"
    p.mkdir(parents=True, exist_ok=True)
    return p


def logs_dir() -> Path:
    p = app_data_dir() / "logs"
    p.mkdir(parents=True, exist_ok=True)
    return p


def config_path() -> Path:
    return app_data_dir() / "config.json"


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def save_config(cfg: dict) -> None:
    config_path().write_text(json.dumps(cfg, indent=2))


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("dt_print_agent")
    logger.setLevel(logging.INFO)
    handler = RotatingFileHandler(
        logs_dir() / "agent.log", maxBytes=1_000_000, backupCount=3
    )
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
    return logger


def acquire_single_instance_lock() -> socket.socket:
    """Bind a dedicated lock port before doing anything else.

    Kept separate from PORT (which Flask binds) so this socket can just be
    held open for the process lifetime as a pure singleton guard. Returns
    the bound socket — keep a reference alive — or raises OSError if
    another instance already holds it.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((HOST, LOCK_PORT))
    sock.listen(1)
    return sock


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'


def is_autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _exe_path())
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
