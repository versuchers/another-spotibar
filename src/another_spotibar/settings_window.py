"""Settings window: skin, language, sizes, colors. Live preview; Cancel reverts."""
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

from . import skins
from . import theme
from . import i18n
from .i18n import tr

SPINS = [("title_size", 6, 24), ("artist_size", 6, 24),
         ("radius", 0, 30), ("progress_h", 1, 12)]
COLORS = ["bg", "border", "title_color", "artist_color", "button", "icon",
          "icon_active", "mode_off", "liked", "progress_fill", "knob", "row_text"]


def _hex(rgba):
    return "#%02x%02x%02x" % (round(rgba.red * 255), round(rgba.green * 255),
                              round(rgba.blue * 255))


class SettingsWindow(Gtk.Window):
    def __init__(self, bar):
        super().__init__()
        self.bar = bar
        self.saved = False
        self._loading = True
        self.orig_lang = i18n.get_lang()
        self.ov = skins.sanitize(skins._read_settings().get("overrides", {}))
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
        self.set_resizable(False)

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for m in ("start", "end", "top", "bottom"):
            getattr(vb, "set_margin_" + m)(16)
        self.add(vb)

        grid = Gtk.Grid(column_spacing=12, row_spacing=8)
        vb.pack_start(grid, False, False, 0)
        self.lbls = {}

        def row(i, key, widget):
            lb = Gtk.Label(xalign=0)
            self.lbls[key] = lb
            grid.attach(lb, 0, i, 1, 1)
            grid.attach(widget, 1, i, 1, 1)

        self.skin = Gtk.ComboBoxText()
        for n in skins.list_skins():
            self.skin.append(n, n)
        if not self.skin.set_active_id(skins.get_selected()):
            self.skin.set_active_id("dark")
        self.skin.connect("changed", self._on_skin)
        row(0, "skin", self.skin)

        self.lang = Gtk.ComboBoxText()
        self.lang.append("en", "English")
        self.lang.append("tr", "Türkçe")
        self.lang.set_active_id(i18n.get_lang())
        self.lang.connect("changed", self._on_lang)
        row(1, "language", self.lang)

        v = self._vals()
        self.spins = {}
        for i, (key, lo, hi) in enumerate(SPINS, start=2):
            sp = Gtk.SpinButton.new_with_range(lo, hi, 1)
            sp.set_value(v[key])
            sp.connect("value-changed", self._on_spin, key)
            self.spins[key] = sp
            row(i, key, sp)

        self.colors_head = Gtk.Label(xalign=0)
        vb.pack_start(self.colors_head, False, False, 0)
        cgrid = Gtk.Grid(column_spacing=10, row_spacing=6)
        vb.pack_start(cgrid, False, False, 0)
        self.cbtns = {}
        for i, key in enumerate(COLORS):
            r, c = i // 2, (i % 2) * 2
            lb = Gtk.Label(xalign=0)
            self.lbls["c_" + key] = lb
            btn = Gtk.ColorButton()
            rgba = Gdk.RGBA()
            rgba.parse(v[key])
            btn.set_rgba(rgba)
            btn.set_use_alpha(False)
            btn.connect("color-set", self._on_color, key)
            self.cbtns[key] = btn
            cgrid.attach(lb, c, r, 1, 1)
            cgrid.attach(btn, c + 1, r, 1, 1)

        sbox = Gtk.Box(spacing=8)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_max_length(40)
        self.saveas_btn = Gtk.Button()
        self.saveas_btn.connect("clicked", self._save_as)
        sbox.pack_start(self.name_entry, True, True, 0)
        sbox.pack_start(self.saveas_btn, False, False, 0)
        vb.pack_start(sbox, False, False, 0)

        self.status = Gtk.Label(label="", xalign=0)
        vb.pack_start(self.status, False, False, 0)

        btns = Gtk.Box(spacing=8)
        self.cancel_btn = Gtk.Button()
        self.save_btn = Gtk.Button()
        self.cancel_btn.connect("clicked", lambda *_: self.destroy())
        self.save_btn.connect("clicked", self._save)
        btns.pack_end(self.save_btn, False, False, 0)
        btns.pack_end(self.cancel_btn, False, False, 0)
        vb.pack_start(btns, False, False, 0)

        self.connect("destroy", self._on_destroy)
        self._retr()
        self._loading = False

    def _vals(self):
        v = dict(theme.DEFAULT)
        v.update(skins.load_skin(self.skin.get_active_id()) or {})
        v.update(self.ov)
        return v

    def _retr(self):
        self.set_title(tr("settings"))
        for k, lb in self.lbls.items():
            lb.set_text(tr(k))
        self.colors_head.set_text(tr("colors"))
        self.name_entry.set_placeholder_text(tr("skin_name"))
        self.saveas_btn.set_label(tr("save_as"))
        self.save_btn.set_label(tr("save"))
        self.cancel_btn.set_label(tr("cancel"))
        self.status.set_text("")

    def _preview(self):
        self.bar.apply_theme(self._vals())

    def _on_skin(self, *_):
        if self._loading:
            return
        self.ov = {}
        v = self._vals()
        self._loading = True
        for key, sp in self.spins.items():
            sp.set_value(v[key])
        for key, btn in self.cbtns.items():
            rgba = Gdk.RGBA()
            rgba.parse(v[key])
            btn.set_rgba(rgba)
        self._loading = False
        self._preview()

    def _on_spin(self, sp, key):
        if self._loading:
            return
        self.ov[key] = int(sp.get_value())
        self._preview()

    def _on_color(self, btn, key):
        if self._loading:
            return
        self.ov[key] = _hex(btn.get_rgba())
        self._preview()

    def _on_lang(self, *_):
        if self._loading:
            return
        i18n.set_lang(self.lang.get_active_id())
        self._retr()
        self.bar.retranslate()

    def _save(self, *_):
        skins.set_selected(self.skin.get_active_id())
        skins.set_overrides(self.ov)
        self.saved = True
        self.destroy()

    def _save_as(self, *_):
        name = self.name_entry.get_text().strip()
        err = skins.save_user_skin(name, self._vals())
        if err:
            self.status.set_text(tr(err))
            return
        skins.set_selected(name)
        skins.set_overrides({})
        self.saved = True
        self.destroy()

    def _on_destroy(self, *_):
        if not self.saved:
            if i18n.get_lang() != self.orig_lang:
                i18n.set_lang(self.orig_lang)
            self.bar.apply_theme(skins.load_selected())
            self.bar.retranslate()
        self.bar.settings_win = None
