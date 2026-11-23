"""Theme: all colors/fonts/sizes in one dict. Skins override these keys."""
from string import Template

DEFAULT = {
    "name": "dark",
    "bg": "#161616",
    "border": "#3a3d42",
    "radius": 10,
    "font": "Manrope",
    "title_size": 10,
    "artist_size": 9,
    "title_color": "#c4c4c4",
    "artist_color": "#7a7a7a",
    "button": "#a8a8a8",
    "hover": "rgba(255, 255, 255, 0.07)",
    "icon": "#8a8a8a",         # kalp (cizgi) ve arti
    "icon_active": "#cccccc",  # shuffle/dongu acikken, ok/hata isaretleri
    "mode_off": "#5c5c5c",     # shuffle/dongu kapaliyken
    "liked": "#a3202c",        # begenilmis kalp
    "progress_bg": "rgba(255, 255, 255, 0.09)",
    "progress_fill": "#858585",
    "progress_h": 4,
    "knob": "#b0b0b0",
    "row_text": "#c4c4c4",
    "entry_bg": "rgba(255, 255, 255, 0.1)",
}

current = dict(DEFAULT)

_CSS = Template("""
window { background-color: $bg; border-radius: ${radius}px;
         border: 1px solid $border; }
label.title { font-family: "$font"; color: $title_color; font-size: ${title_size}pt; }
label.artist { font-family: "$font"; color: $artist_color; font-size: ${artist_size}pt; }
button { background: transparent; border: none; box-shadow: none;
         padding: 2px; min-width: 26px; min-height: 26px; color: $button; }
button:hover { background-color: $hover; }
scale { min-height: 10px; padding: 0; }
scale trough { min-height: ${progress_h}px; background-color: $progress_bg;
               border: none; border-radius: 2px; }
scale highlight { min-height: ${progress_h}px; background-color: $progress_fill;
                  border: none; border-radius: 2px; }
scale slider { min-width: 10px; min-height: 10px; margin: -3px 0;
               background: $knob; border: none; border-radius: 50%;
               box-shadow: none; }
list { background: transparent; }
row { color: $row_text; padding: 6px 8px; }
row:hover { background-color: $hover; }
entry { color: $row_text; background: $entry_bg; }
""")


def set_theme(d):
    global current
    current = dict(DEFAULT)
    current.update(d or {})


def build_css():
    return _CSS.safe_substitute(current)


def rgb(key):
    """Cairo icin (r, g, b) 0-1; gecersiz renkte gri."""
    v = str(current.get(key, DEFAULT.get(key, "#888888"))).lstrip("#")
    try:
        return tuple(int(v[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        return (0.5, 0.5, 0.5)
