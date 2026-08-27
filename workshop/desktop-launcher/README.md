# TWIS Holo Workshop desktop launcher

`TWIS Holo Workshop.exe` is a console-free Windows 10 launcher for the existing local Workshop.

It performs only these bounded actions:

1. verifies the fixed TWIS health endpoint at `http://127.0.0.1:8787/api/health`;
2. when necessary, starts the existing `companion/server.py` with the installed Python launcher and a hidden console;
3. waits for a genuine TWIS health response;
4. opens or focuses Microsoft Edge in app-window mode at the fixed loopback Workshop URL.

The Edge shell uses a dedicated local profile under `%LOCALAPPDATA%\TWIS Holo Workshop\EdgeProfile` so TWIS has its own window lifecycle and can retain normal window sizing without sharing the owner's ordinary browser profile. Background networking, sync, component updates, first-run prompts, and default-browser prompts are disabled for this shell.

The launcher does not stop the Workshop service when its window closes, alter the database, expose a shell command field, fetch network resources, or add cloud/provider behavior. Startup failures use a small native error window with optional technical details.

The executable must remain inside `TWIS\desktop-launcher`; it locates the existing Workshop from its parent directory. Run `build-launcher.ps1` to reproduce the executable using Windows' installed .NET Framework compiler. The icon is generated deterministically from the existing graphite/cyan Workshop mark, with a brass clock-and-compass ring for Windows readability.
