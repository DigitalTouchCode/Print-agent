"""PyInstaller entry point — kept as a tiny top-level script so the spec
file has a simple, stable path to point at regardless of how `agent/` is
packaged as a module."""
from agent.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
