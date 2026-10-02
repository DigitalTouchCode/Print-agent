# DT Print Agent

A small Windows tray app that print to a USB thermal
receipt printer directly, without relying on the browser's WebUSB permission
model (which hits hitting `Access denied` when Windows or Linux already had a
driver bound to the printer's USB interface).

The agent runs a tiny local HTTP server on `127.0.0.1:9153`. The POS page
posts raw ESC/POS bytes to it; the agent talks to the printer over USB using
`pyusb`/`libusb`, the same way `pairUsb()` in `pos.html` was trying to — the
difference is the WinUSB driver binding is a one-time step done for this
process (via Zadig, see the setup guide), not something Chrome has to
renegotiate every session.

## Layout

```
dt-print-agent/
  agent/
    __main__.py     entry point: single-instance lock, starts server + tray
    server.py        Flask app: GET /health, GET /devices, POST /print
    printer.py        USB discovery + raw bulk-transfer send via pyusb
    tray.py            system tray icon, autostart toggle, quit
    config.py          paths, logging, autostart (stdlib winreg, no pywin32 needed for this part)
  assets/
    dt_icon.ico        tray/app icon — currently a placeholder "DT" monogram;
                        drop in the real DigitalTouch logo (256x256 recommended,
                        transparent or square background) and rerun the icon
                        step, or just re-export dt_icon.ico from the real artwork.
  build/
    dt_print_agent.spec   PyInstaller build spec
    build.bat               one-shot build script (venv, deps, PyInstaller)
    installer.iss           Inno Setup script -> proper Setup.exe
  run_agent.py         thin entry point PyInstaller targets
  requirements.txt
```

## Building without a Windows machine

PyInstaller doesn't cross-compile, so a `.exe` has to be built on Windows —
but that doesn't have to be your machine. `.github/workflows/build-print-agent.yml`
builds it on GitHub's free `windows-latest` runner (installs deps, runs
PyInstaller, runs Inno Setup, uploads the finished installer as a build
artifact — and, if you push a tag, attaches it to a GitHub Release too).

Getting it onto the VPS from there is just:

```
curl -L -o /var/www/downloads/dt-print-agent-setup.exe \
  https://github.com/<you>/<repo>/releases/latest/download/dt-print-agent-setup.exe
```

See `build/nginx-downloads.conf` for the server block that serves it (and
the setup guide PDF) at a stable URL — that's what `printAgentDownloadUrl`
and `printAgentGuideUrl` in `pos.html` should point at.

## Building manually on Windows

If you'd rather not use CI:


1. Install [Python 3.11+](https://www.python.org/downloads/) (check "Add to PATH").
2. Run `build\build.bat`. This creates a venv, installs `requirements.txt`,
   and runs PyInstaller. Output: `dist\DT Print Agent.exe`.
3. Install [Inno Setup](https://jrsoftware.org/isinfo.php), open
   `build\installer.iss`, and click **Build** (or `iscc build\installer.iss`
   from an Inno Setup command prompt). Output:
   `build\output\dt-print-agent-setup.exe` — this is the file to host and
   link from Settings.

If you want the setup-guide PDF bundled into the installer and offered as a
post-install shortcut, drop `dt-print-agent-setup-guide.pdf` into `build\`
before running Inno Setup (the `.iss` script already looks for it there).

## Testing locally before packaging

```
pip install -r requirements.txt
python run_agent.py
```

A tray icon should appear. `curl http://127.0.0.1:9153/health` should return
`{"status": "ok", "version": "1.0.0"}`, and `/devices` should list any
connected USB printer once Zadig has bound WinUSB to it (see the setup guide
— until then Windows' own driver still owns the device and pyusb won't see
a claimable bulk endpoint).

## Replacing the placeholder logo

`assets/dt_icon.ico` is a generated teal "DT" monogram so the build works
out of the box. Once you have the real DigitalTouch logo:

1. Export it as a square PNG (256x256 or larger).
2. Convert to `.ico` with the sizes Windows expects (16/24/32/48/64/128/256)
   — e.g. via Pillow: `Image.open("logo.png").save("dt_icon.ico", sizes=[(s,s) for s in (16,24,32,48,64,128,256)])`.
3. Overwrite `assets/dt_icon.ico` and `assets/dt_icon.png`, rebuild.

## POS integration

`pos.html`'s `printerService` already has a third transport, `"agent"`,
alongside `"bt"` and `"usb"`:

- `printerService.pairAgent()` — health-checks the agent, lists its USB
  devices, and stores the chosen printer's vendor/product ID (same
  `localDB` keys the WebUSB path used, so paper-size settings etc. are
  shared).
- `printerService.write(bytes)` — routes to the agent over HTTP when
  `transport === "agent"`, using the same ESC/POS byte builders as the
  Bluetooth/WebUSB paths.
- Settings > Receipt printer has a **"Connect via DT Print Agent"** button
  plus **Download** / **Setup guide** links. Update
  `printAgentDownloadUrl` and `printAgentGuideUrl` in the tenant settings
  component's `data()` once the installer and PDF are hosted somewhere
  (e.g. `https://digitaltouch.co.zw/downloads/...`).

## Security notes

- The server only binds `127.0.0.1` — never reachable from the network.
- CORS is restricted to the POS origins listed in `config.ALLOWED_ORIGINS`;
  add any staging domain there too.
- No auth token on `/print` since it's localhost-only and any process
  already running as the same user could reach it either way — matches the
  trust model of the WebUSB approach it replaces.
