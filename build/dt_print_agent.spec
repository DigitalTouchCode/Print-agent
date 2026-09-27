# Build with:  pyinstaller build\dt_print_agent.spec
# Can be run from anywhere — root is derived from this spec file's own
# location (build\..), not the invoking shell's CWD. PyInstaller chdirs to
# the spec file's folder before exec'ing it, so a bare Path(".") here would
# silently resolve to build\ instead of the project root; SPECPATH is the
# global PyInstaller injects for exactly this reason.
from pathlib import Path

block_cipher = None
root = Path(SPECPATH).resolve().parent

a = Analysis(
    [str(root / "run_agent.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "assets" / "dt_icon.ico"), "assets")],
    hiddenimports=[
        "pystray._win32",
        "PIL._tkinter_finder",
        "engineio.async_drivers.threading",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

# `libusb` ships its DLL as package data — collect it explicitly so the
# frozen exe can find libusb-1.0.dll without the user installing anything.
# collect_dynamic_libs() returns (dest, src) 2-tuples; a.binaries is already
# a normalized TOC of (dest, src, typecode) 3-tuples, so the typecode has
# to be added by hand here rather than concatenating the raw list.
from PyInstaller.utils.hooks import collect_dynamic_libs
a.binaries += [(dest, src, "BINARY") for dest, src in collect_dynamic_libs("libusb")]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DT Print Agent",
    debug=False,
    strip=False,
    upx=False,
    console=False,  # windowed: no console flash on startup, tray icon only
    icon=str(root / "assets" / "dt_icon.ico"),
)
