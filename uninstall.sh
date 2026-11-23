#!/usr/bin/env bash
# Removes the program. Your settings in ~/.config/another-spotibar are kept
# (delete that folder too if you also want to remove your login token).
set -eu
APP=another-spotibar
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}"
rm -rf "$SHARE/$APP" "$HOME/.local/bin/$APP" \
       "$SHARE/applications/$APP.desktop" \
       "$SHARE/icons/hicolor/scalable/apps/$APP.svg" \
       "${XDG_CONFIG_HOME:-$HOME/.config}/autostart/$APP.desktop"
echo "Removed."
