import logging
import sys
import threading

from . import config, server, tray
from .version import __version__


def main() -> int:
    logger = config.setup_logging()
    logger.info("DT Print Agent v%s starting", __version__)

    try:
        lock_socket = config.acquire_single_instance_lock()  # noqa: F841 — held for process lifetime
    except OSError:
        logger.info("Another instance is already running on port %d — exiting.", config.PORT)
        # A second launch (e.g. double-clicking the shortcut again) should be
        # a silent no-op, not an error dialog — the running instance is fine.
        return 0

    stop_event = threading.Event()
    server_thread = threading.Thread(target=server.run, daemon=True)
    server_thread.start()
    logger.info("Print server listening on http://%s:%d", config.HOST, config.PORT)

    def on_quit():
        logger.info("Quit requested from tray")
        stop_event.set()

    try:
        tray.build_and_run_tray(on_quit)
    except Exception:
        logger.exception("Tray icon failed — running headless")
        stop_event.wait()

    return 0


if __name__ == "__main__":
    sys.exit(main())
