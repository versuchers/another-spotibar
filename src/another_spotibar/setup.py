"""First-run setup window: Spotify client ID entry + browser login."""
import threading

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

from . import auth
from . import i18n
from .i18n import tr

DASHBOARD = "https://developer.spotify.com/dashboard"


class SetupWindow(Gtk.Window):
    def __init__(self, need_id):
        super().__init__()
        self.ok = False
        self._closed = False
        self._status = None
        self.need_id = need_id
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(460, -1)
        self.set_resizable(False)
        self.connect("destroy", lambda *_: setattr(self, "_closed", True))

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for m in ("start", "end", "top", "bottom"):
            getattr(vb, "set_margin_" + m)(16)
        self.add(vb)

        top = Gtk.Box()
        self.lang_btn = Gtk.Button()
        self.lang_btn.connect("clicked", self._toggle_lang)
        top.pack_end(self.lang_btn, False, False, 0)
        vb.pack_start(top, False, False, 0)

        self.info = Gtk.Label(xalign=0)
        self.info.set_line_wrap(True)
        self.info.set_max_width_chars(60)
        vb.pack_start(self.info, False, False, 0)

        self.entry = Gtk.Entry()
        self.link = None
        self.cp = None
        if need_id:
            self.link = Gtk.LinkButton.new_with_label(DASHBOARD, "")
            vb.pack_start(self.link, False, False, 0)

            row = Gtk.Box(spacing=6)
            uri = Gtk.Entry()
            uri.set_text(auth.REDIRECT_URI)
            uri.set_editable(False)
            self.cp = Gtk.Button()
            self.cp.connect("clicked", lambda *_: Gtk.Clipboard.get(
                Gdk.SELECTION_CLIPBOARD).set_text(auth.REDIRECT_URI, -1))
            row.pack_start(uri, True, True, 0)
            row.pack_start(self.cp, False, False, 0)
            vb.pack_start(row, False, False, 0)

            self.entry.connect("activate", self._go)
            vb.pack_start(self.entry, False, False, 0)

        self.status = Gtk.Label(label="", xalign=0)
        self.status.set_line_wrap(True)
        self.status.set_max_width_chars(60)
        vb.pack_start(self.status, False, False, 0)

        self.btn = Gtk.Button()
        self.btn.connect("clicked", self._go)
        vb.pack_start(self.btn, False, False, 0)
        self._refresh()

    def _refresh(self):
        self.set_title(tr("setup_title"))
        self.lang_btn.set_label(tr("lang_btn"))
        self.info.set_text(tr("steps") if self.need_id else tr("need_login"))
        if self.need_id:
            self.link.set_label(tr("open_dash"))
            self.cp.set_label(tr("copy"))
            self.entry.set_placeholder_text(tr("id_hint"))
        self.btn.set_label(tr("save_login") if self.need_id else tr("login"))
        self._render_status()

    def _set_status(self, key=None, arg=None):
        self._status = (key, arg) if key else None
        self._render_status()

    def _render_status(self):
        if not self._status:
            self.status.set_text("")
            return
        key, arg = self._status
        txt = tr(key)
        self.status.set_text(txt % arg if arg is not None else txt)

    def _toggle_lang(self, *_):
        i18n.set_lang("tr" if i18n.get_lang() == "en" else "en")
        self._refresh()

    def _go(self, *_):
        if not self.btn.get_sensitive():
            return
        if self.need_id:
            cid = self.entry.get_text().strip().lower()
            if not auth.CLIENT_ID_RE.match(cid):
                self._set_status("bad_id")
                return
            try:
                auth.save_client_id(cid)
            except OSError as e:
                self._set_status("save_fail", str(e))
                return
        self.btn.set_sensitive(False)
        self.entry.set_sensitive(False)
        self._set_status("waiting")

        def work():
            try:
                auth.login()
                err = None
            except Exception as e:
                err = str(e)
            GLib.idle_add(self._done, err)
        threading.Thread(target=work, daemon=True).start()

    def _done(self, err):
        if self._closed:
            return False
        if err:
            self._set_status("err", err)
            self.btn.set_sensitive(True)
            self.entry.set_sensitive(True)
        else:
            self.ok = True
            self.destroy()
        return False


def run():
    """Opens the setup window if needed. Returns True when ready."""
    need_id = not auth.get_client_id()
    if not need_id and auth.has_token():
        return True
    win = SetupWindow(need_id)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return win.ok
