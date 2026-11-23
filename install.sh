#!/usr/bin/env bash
# Installs another-spotibar for the current user (no root needed).
#   ./install.sh              install
#   ./install.sh --autostart  install + start on login
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

APP=another-spotibar
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}"
LIB="$SHARE/$APP"
BIN="$HOME/.local/bin"

if ! python3 -c 'import gi; gi.require_version("Gtk","3.0"); from gi.repository import Gtk' 2>/dev/null; then
    echo "Missing GTK3 Python bindings. Install them first, e.g.:"
    echo "  Debian/Ubuntu/Mint: sudo apt install python3-gi gir1.2-gtk-3.0"
    echo "  Fedora:             sudo dnf install python3-gobject gtk3"
    echo "  Arch:               sudo pacman -S python-gobject gtk3"
    exit 1
fi

rm -rf "$LIB"
mkdir -p "$LIB" "$BIN" "$SHARE/applications" "$SHARE/icons/hicolor/scalable/apps"
cp -r src/another_spotibar "$LIB/"
find "$LIB" -name __pycache__ -prune -exec rm -rf {} +

cat > "$BIN/$APP" <<LAUNCH
#!/bin/sh
PYTHONPATH="$LIB\${PYTHONPATH:+:\$PYTHONPATH}" exec python3 -m another_spotibar "\$@"
LAUNCH
chmod +x "$BIN/$APP"

cp data/$APP.svg "$SHARE/icons/hicolor/scalable/apps/$APP.svg"
sed "s|^Exec=.*|Exec=$BIN/$APP|" data/$APP.desktop > "$SHARE/applications/$APP.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$SHARE/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q "$SHARE/icons/hicolor" 2>/dev/null || true

if [ "${1:-}" = "--autostart" ]; then
    mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/autostart"
    cp "$SHARE/applications/$APP.desktop" "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP.desktop"
    echo "Autostart enabled."
fi

echo "Installed. Run: $APP   (make sure $BIN is in your PATH)"
