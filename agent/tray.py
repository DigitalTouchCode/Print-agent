import logging
import os
import subprocess
import sys
import threading

import pystray
from PIL import Image

from . import config

logger = logging.getLogger("dt_print_agent")


def _icon_path() -> str:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:
        base = os.path.join(os.path.dirname(__file__), "..")
    return os.path.join(base, "assets", "dt_icon.ico")


def _open_logs_folder(icon, item):
    os.startfile(str(config.logs_dir()))  # noqa: S606 — Windows-only by design


def _toggle_autostart(icon, item):
    config.set_autostart(not config.is_autostart_enabled())


def build_and_run_tray(on_quit) -> None:
    image = Image.open(_icon_path())

    def quit_action(icon, item):
        icon.stop()
        on_quit()

    menu = pystray.Menu(
        pystray.MenuItem(f"{config.APP_NAME} — running", None, enabled=False),
        pystray.MenuItem(f"Listening on 127.0.0.1:{config.PORT}", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Open logs folder", _open_logs_folder),
        pystray.MenuItem(
            "Start with Windows",
            _toggle_autostart,
            checked=lambda item: config.is_autostart_enabled(),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", quit_action),
    )
    icon = pystray.Icon("dt_print_agent", image, config.APP_NAME, menu)
    icon.run()
