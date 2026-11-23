"""Central config paths (XDG) and one-time migration from the old flat layout."""
import os
import shutil

_xdg = os.environ.get("XDG_CONFIG_HOME", "")
_base = _xdg if os.path.isabs(_xdg) else os.path.expanduser("~/.config")
CONFIG_DIR = os.path.join(_base, "another-spotibar")

TOKEN_FILE = os.path.join(CONFIG_DIR, "token.json")
CLIENT_FILE = os.path.join(CONFIG_DIR, "client.json")
LANG_FILE = os.path.join(CONFIG_DIR, "lang.json")
CONFIG_FILE = os.path.join(CONFIG_DIR, "window.json")
RECENT_FILE = os.path.join(CONFIG_DIR, "recent.json")
SETTINGS_FILE = os.path.join(CONFIG_DIR, "settings.json")
SKINS_DIR = os.path.join(CONFIG_DIR, "skins")

_OLD_DIR = os.path.expanduser("~/.config")
_MIGRATE = {
    "spotify-bar-token.json": TOKEN_FILE,
    "spotify-bar-client.json": CLIENT_FILE,
    "spotify-bar-lang.json": LANG_FILE,
    "spotify-bar.json": CONFIG_FILE,
    "spotify-bar-recent.json": RECENT_FILE,
}


def migrate():
    """Move files from the pre-release layouts into CONFIG_DIR (never overwrites)."""
    old_dir = os.path.join(_base, "spotify-bar")
    if os.path.isdir(old_dir) and not os.path.exists(CONFIG_DIR):
        try:
            shutil.move(old_dir, CONFIG_DIR)
        except OSError:
            pass
    try:
        os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    except OSError:
        return
    for old_name, new in _MIGRATE.items():
        old = os.path.join(_OLD_DIR, old_name)
        if os.path.isfile(old) and not os.path.exists(new):
            try:
                shutil.move(old, new)
            except OSError:
                pass


migrate()
