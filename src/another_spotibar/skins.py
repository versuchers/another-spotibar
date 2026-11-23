"""Skins: built-in + user JSON skins. Selected skin is stored in settings.json.

A skin is a (partial) dict of theme.DEFAULT keys; missing keys fall back to the dark default.
User skins: <config>/another-spotibar/skins/<name>.json
"""
import json
import os
import re

from . import theme
from .paths import SKINS_DIR, SETTINGS_FILE

BUILTIN = {
    "dark": {},
    "light": {
        "bg": "#f2f2f2", "border": "#c9c9c9",
        "title_color": "#222222", "artist_color": "#666666",
        "button": "#444444", "hover": "rgba(0, 0, 0, 0.07)",
        "icon": "#6a6a6a", "icon_active": "#222222", "mode_off": "#b0b0b0",
        "liked": "#c0283a",
        "progress_bg": "rgba(0, 0, 0, 0.12)", "progress_fill": "#666666",
        "knob": "#444444", "row_text": "#222222",
        "entry_bg": "rgba(0, 0, 0, 0.08)",
    },
    "amoled": {"bg": "#000000", "border": "#1f1f1f"},
    "nord": {
        "bg": "#2e3440", "border": "#434c5e",
        "title_color": "#eceff4", "artist_color": "#81a1c1",
        "button": "#d8dee9", "icon": "#81a1c1", "icon_active": "#eceff4",
        "mode_off": "#4c566a", "liked": "#bf616a",
        "progress_fill": "#88c0d0", "knob": "#eceff4", "row_text": "#eceff4",
    },
    "sunset": {
        "bg": "#1e1714", "border": "#4a3830",
        "title_color": "#f0dcc8", "artist_color": "#a88468",
        "button": "#d8b898", "icon": "#a88468", "icon_active": "#ffd9a8",
        "mode_off": "#5e4a3c", "liked": "#e0553a",
        "progress_fill": "#d08850", "knob": "#f0c090", "row_text": "#f0dcc8",
    },
}

_HEX6 = re.compile(r"^#[0-9a-fA-F]{6}$")
_RGBA = re.compile(
    r"^rgba?\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*(,\s*(0|1|0?\.\d+)\s*)?\)$")
_FONT = re.compile(r"^[\w \-]{1,60}$")
_CAIRO = {"icon", "icon_active", "mode_off", "liked"}  # sadece #rrggbb
_INTS = {"radius": (0, 30), "title_size": (6, 24),
         "artist_size": (6, 24), "progress_h": (1, 12)}


def sanitize(d):
    """Keep only known keys with safe values (bad CSS would break the whole theme)."""
    out = {}
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        if k not in theme.DEFAULT or k == "name":
            continue
        if k in _INTS:
            lo, hi = _INTS[k]
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                out[k] = int(min(max(v, lo), hi))
        elif k == "font":
            if isinstance(v, str) and _FONT.match(v):
                out[k] = v
        elif isinstance(v, str):
            if _HEX6.match(v) or (k not in _CAIRO and _RGBA.match(v)):
                out[k] = v
    return out


def _user_names():
    try:
        return sorted(f[:-5] for f in os.listdir(SKINS_DIR)
                      if f.endswith(".json") and not f.startswith("."))
    except OSError:
        return []


def list_skins():
    names = list(BUILTIN)
    for n in _user_names():
        if n not in names:
            names.append(n)
    return names


def load_skin(name):
    """Returns sanitized skin dict, or None if it doesn't exist."""
    if not isinstance(name, str) or not name or os.sep in name or name.startswith("."):
        return None
    path = os.path.join(SKINS_DIR, name + ".json")
    if os.path.isfile(path):
        try:
            with open(path) as f:
                d = sanitize(json.load(f))
            d["name"] = name
            return d
        except (OSError, ValueError):
            pass
    if name in BUILTIN:
        d = sanitize(BUILTIN[name])
        d["name"] = name
        return d
    return None


def _read_settings():
    try:
        with open(SETTINGS_FILE) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def get_selected():
    v = _read_settings().get("skin", "dark")
    return v if isinstance(v, str) else "dark"


def set_selected(name):
    s = _read_settings()
    s["skin"] = name
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(s, f)
        return True
    except OSError:
        return False


def save_user_skin(name, d):
    """Writes a user skin. Returns None on success, or an i18n error key."""
    if not isinstance(name, str) or not re.match(r"^[\w\-]{1,40}$", name):
        return "bad_name"
    if name in BUILTIN:
        return "name_builtin"
    clean = sanitize(d)
    try:
        os.makedirs(SKINS_DIR, exist_ok=True)
        with open(os.path.join(SKINS_DIR, name + ".json"), "w") as f:
            json.dump(clean, f, indent=2)
    except OSError:
        return "save_fail_skin"
    return None


def load_selected():
    t = load_skin(get_selected()) or load_skin("dark")
    t.update(sanitize(_read_settings().get("overrides", {})))
    return t


def set_overrides(d):
    s = _read_settings()
    s["overrides"] = sanitize(d)
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(s, f)
        return True
    except OSError:
        return False
