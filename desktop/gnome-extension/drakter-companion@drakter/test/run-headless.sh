#!/usr/bin/env bash
# Runs a private headless GNOME Shell 50 (own D-Bus session bus, fake empty
# system bus, own XDG dirs), installs drakter-companion into a temp
# XDG_DATA_HOME with scripts/install-gnome-extension.sh and runs client.js.
# Touches nothing of the user's session, the real system bus or ~/.local.
# Usage: bash run-headless.sh   (X11=1 for XWayland test windows; ROOT=… to move the temp dir)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../../.." && pwd)"
ROOT="${ROOT:-/tmp/drakter-gs-e1}"
case "$ROOT" in /tmp/*) ;; *) echo "ROOT must be under /tmp" >&2; exit 2 ;; esac
rm -rf "$ROOT"; mkdir -p "$ROOT"/{rt,config,cache,data/gnome-shell/extensions}
chmod 700 "$ROOT/rt"
# .desktop files for the GTK test windows, so the shell maps them to real apps.
mkdir -p "$ROOT/data/applications"
for id in target drakterfloating drakterlate; do
  printf '[Desktop Entry]\nType=Application\nName=%s\nExec=true\nNoDisplay=true\n' "$id" >"$ROOT/data/applications/org.drakter.test.$id.desktop"
done
# Fake, empty "system" bus so the test shell never talks to the real logind/GDM.
FAKE_SYS="$ROOT/fake-system-bus"
dbus-daemon --session --nofork --address="unix:path=$FAKE_SYS" --print-pid >"$ROOT/fakesys.pid" 2>/dev/null &
FAKE_PID=$!
trap 'kill $FAKE_PID 2>/dev/null' EXIT
for _ in $(seq 50); do [ -S "$FAKE_SYS" ] && break; sleep 0.1; done
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin LANG=C.UTF-8 \
  XDG_RUNTIME_DIR="$ROOT/rt" XDG_CONFIG_HOME="$ROOT/config" XDG_CACHE_HOME="$ROOT/cache" \
  XDG_DATA_HOME="$ROOT/data" ROOT="$ROOT" HERE="$HERE" REPO="$REPO" GDB="${GDB:-}" X11="${X11:-}" \
  DBUS_SYSTEM_BUS_ADDRESS="unix:path=$FAKE_SYS" \
  dbus-run-session -- bash -c '
    set -u
    UUID=drakter-companion@drakter
    DEST="$ROOT/data/gnome-shell/extensions/$UUID"
    gsettings set org.gnome.shell disable-user-extensions false
    gsettings set org.gnome.desktop.interface enable-animations false
    # The normal install must not carry the debug interface nor test/ (M3).
    XDG_DATA_HOME="$ROOT/plain" bash "$REPO/scripts/install-gnome-extension.sh" --no-enable >/dev/null || { echo "FAIL  plain install"; exit 1; }
    PLAIN="$ROOT/plain/gnome-shell/extensions/$UUID"
    if [ -s "$PLAIN/extension.js" ] && ! grep -q "DebugApi\|DRAKTER_COMPANION_DEBUG\|DRAKTER_COMPANION_TRUST\|Inject" "$PLAIN/extension.js" && [ ! -e "$PLAIN/test" ]; then
      echo "PASS  plain install has no DebugApi, no test trust and no test/"
    else
      echo "FAIL  plain install still has debug code or test/"; exit 1
    fi
    # The headless test needs DebugApi: install the source tree as is.
    bash "$REPO/scripts/install-gnome-extension.sh" --dev || { echo "FAIL  install script"; exit 1; }
    echo "enabled-extensions: $(gsettings get org.gnome.shell enabled-extensions)"
    # Test drivers trusted without being Drakter: only gjs (client.js). python3 must pass the real check.
    DRAKTER_COMPANION_DEBUG=1 DRAKTER_COMPANION_TRUST_EXE=/usr/bin/gjs ${GDB:+gdb -batch -ex run -ex bt --args} gnome-shell --headless --wayland ${X11:---no-x11} \
      --virtual-monitor 1280x800 --wayland-display drk-wl >"$ROOT/shell.log" 2>&1 &
    SHELL_PID=$!
    gdbus wait --session --timeout 40 org.drakter.Companion || { echo "NO BUS NAME"; tail -50 "$ROOT/shell.log"; kill $SHELL_PID; exit 1; }
    echo "companion up after shell start"
    WAYLAND_DISPLAY=drk-wl gjs -m "$HERE/client.js" "$ROOT" "$HERE" "$DEST/schemas"; RC=$?
    # disable/enable cycle: the name must go away and come back, no JS errors.
    gnome-extensions disable $UUID; sleep 1
    kill -0 $SHELL_PID 2>/dev/null && echo "shell alive after disable" || echo "SHELL DIED during disable"
    if gdbus introspect --session --dest org.drakter.Companion --object-path /org/drakter/Companion >/dev/null 2>&1; then echo "FAIL  name still owned after disable"; RC=1; else echo "PASS  disable releases the bus name"; fi
    [ -e "$ROOT/rt/drakter-companion/token" ] && { echo "FAIL  token left after disable"; RC=1; } || echo "PASS  disable deletes the token"
    gnome-extensions enable $UUID
    if gdbus wait --session --timeout 10 org.drakter.Companion; then echo "PASS  re-enable owns the name again"; else echo "FAIL  re-enable"; RC=1; fi
    if grep -q "drakter-companion@drakter: \|drakter-companion.*Error\|JS ERROR" "$ROOT/shell.log"; then echo "FAIL  extension errors in shell.log"; grep -n "drakter-companion\|JS ERROR" "$ROOT/shell.log" | head -10; RC=1; else echo "PASS  no extension errors in shell.log"; fi
    if kill -0 $SHELL_PID 2>/dev/null; then echo "shell still alive"; else wait $SHELL_PID; echo "SHELL DIED rc=$?"; fi
    kill $SHELL_PID 2>/dev/null; wait $SHELL_PID 2>/dev/null
    exit $RC'
