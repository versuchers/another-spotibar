#!/usr/bin/env python3
"""another-spotibar: always-on-top mini player bar for the Spotify desktop app.
Controls playback over MPRIS (D-Bus); uses the Spotify Web API for like/playlists.
Needs only python3-gi (GTK3)."""

import json
import os

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib
import sys
import threading
from . import auth
from .i18n import tr
from .paths import RECENT_FILE, CONFIG_FILE
from . import theme
from . import skins

# ---- Ayarlar (position / size) ----
BAR_WIDTH = 305
BAR_HEIGHT = 57
MARGIN_RIGHT = 10    # ekranın sağ kenarından uzaklık
MARGIN_BOTTOM = 40   # ekranın alt kenarından uzaklık (panelin hemen üstü)
POLL_MS = 1000
EDGE = 6  # kenardan tutup boyutlandirma bolgesi (px)
MAX_CHARS = 40  # en uzun yazi genisligi (karakter); asarsa ... ile kesilir

BUS_NAME = "org.mpris.MediaPlayer2.spotify"
OBJ_PATH = "/org/mpris/MediaPlayer2"
PLAYER_IFACE = "org.mpris.MediaPlayer2.Player"



class ModeButton(Gtk.Button):
    """Ince cizgili shuffle / dongu ikonu (Cairo)."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.on = False
        self.mode = "None"
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_can_focus(False)
        self.area = Gtk.DrawingArea()
        self.area.set_size_request(18, 22)
        self.area.connect("draw", self._draw)
        self.add(self.area)

    def update(self, on, mode="None"):
        self.on, self.mode = on, mode
        self.area.queue_draw()

    def _draw(self, w, cr):
        col = theme.rgb("icon_active" if self.on else "mode_off")
        cr.set_source_rgb(*col)
        cr.set_line_width(1.3)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        aw, ah = w.get_allocated_width(), w.get_allocated_height()
        cr.translate((aw - 18) / 2.0, (ah - 18) / 2.0)
        if self.kind == "shuffle":
            cr.move_to(2, 5); cr.curve_to(8, 5, 8, 13, 14, 13); cr.stroke()
            cr.move_to(2, 13); cr.curve_to(8, 13, 8, 5, 14, 5); cr.stroke()
            cr.move_to(12, 2.8); cr.line_to(14.8, 5); cr.line_to(12, 7.2); cr.stroke()
            cr.move_to(12, 10.8); cr.line_to(14.8, 13); cr.line_to(12, 15.2); cr.stroke()
        else:
            cr.move_to(2.5, 8.5); cr.line_to(2.5, 7.5)
            cr.curve_to(2.5, 5.5, 3.5, 4.5, 5.5, 4.5)
            cr.line_to(14, 4.5); cr.stroke()
            cr.move_to(12, 2.5); cr.line_to(14.2, 4.5); cr.line_to(12, 6.5); cr.stroke()
            cr.move_to(15.5, 9.5); cr.line_to(15.5, 10.5)
            cr.curve_to(15.5, 12.5, 14.5, 13.5, 12.5, 13.5)
            cr.line_to(4, 13.5); cr.stroke()
            cr.move_to(6, 11.5); cr.line_to(3.8, 13.5); cr.line_to(6, 15.5); cr.stroke()
            if self.mode == "Track":
                cr.select_font_face("sans", 0, 1)
                cr.set_font_size(7)
                cr.move_to(7.2, 11)
                cr.show_text("1")
        if self.on:
            cr.arc(9, 18.3, 0.9, 0, 6.2832)
            cr.fill()


class IconButton(Gtk.Button):
    """Cairo ile cizilen kalp / arti ikonu."""

    def __init__(self, kind):
        super().__init__()
        self.kind = kind
        self.state = None
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_can_focus(False)
        self.area = Gtk.DrawingArea()
        self.area.set_size_request(18, 22)
        self.area.connect("draw", self._draw)
        self.add(self.area)

    def set_state(self, st):
        self.state = st
        self.area.queue_draw()

    def _draw(self, w, cr):
        aw, ah = w.get_allocated_width(), w.get_allocated_height()
        cr.translate((aw - 18) / 2.0, (ah - 18) / 2.0)
        cr.set_line_width(1.4)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        if self.kind == "heart":
            cr.move_to(9, 15.6)
            cr.curve_to(3, 11.4, 1.2, 8.6, 1.2, 6.2)
            cr.curve_to(1.2, 3.9, 2.9, 2.4, 4.9, 2.4)
            cr.curve_to(6.7, 2.4, 8.2, 3.4, 9, 4.9)
            cr.curve_to(9.8, 3.4, 11.3, 2.4, 13.1, 2.4)
            cr.curve_to(15.1, 2.4, 16.8, 3.9, 16.8, 6.2)
            cr.curve_to(16.8, 8.6, 15, 11.4, 9, 15.6)
            cr.close_path()
            if self.state:
                cr.set_source_rgb(*theme.rgb("liked"))
                cr.fill()
            else:
                cr.set_source_rgb(*theme.rgb("icon"))
                cr.stroke()
            return
        cr.set_source_rgb(*theme.rgb("icon"))
        st = self.state
        if st == "ok":
            cr.set_source_rgb(*theme.rgb("icon_active"))
            cr.move_to(3.5, 9.5); cr.line_to(7.5, 13.5); cr.line_to(14.5, 4.5); cr.stroke()
        elif st == "err":
            cr.set_source_rgb(*theme.rgb("icon_active"))
            cr.move_to(4, 4); cr.line_to(14, 14); cr.stroke()
            cr.move_to(14, 4); cr.line_to(4, 14); cr.stroke()
        elif st == "dup":
            cr.set_source_rgb(*theme.rgb("icon_active"))
            cr.move_to(9, 3); cr.line_to(9, 10.5); cr.stroke()
            cr.arc(9, 14, 0.9, 0, 6.2832); cr.fill()
        else:
            cr.move_to(3.5, 9); cr.line_to(14.5, 9); cr.stroke()
            cr.move_to(9, 3.5); cr.line_to(9, 14.5); cr.stroke()


class SpotifyBar(Gtk.Window):
    def __init__(self):
        super().__init__()
        self._rgba(self)
        self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)

        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(True)
        self.set_size_request(120, BAR_HEIGHT)
        self.set_default_size(1, BAR_HEIGHT)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        self.set_accept_focus(False)
        self._last_text = None
        self.saved_pos = self._load_pos()
        self.user_w = self._load_w()
        self._user_sized = False
        if self.user_w:
            self.set_default_size(self.user_w, BAR_HEIGHT)
        self._dragged = False
        self._save_timer = None
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect("motion-notify-event", self._on_motion)
        self.connect("button-press-event", self._on_press)
        self.connect("configure-event", self._on_configure)

        self._css_provider = None
        self.apply_theme(skins.load_selected())

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        box.set_margin_start(16)
        box.set_margin_end(16)
        box.set_margin_top(4)
        box.set_margin_bottom(12)
        overlay = Gtk.Overlay()
        overlay.add(box)
        self.progress = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 1, 1)
        self.progress.set_draw_value(False)
        self.progress.set_can_focus(False)
        self.progress.set_valign(Gtk.Align.END)
        self.progress.set_halign(Gtk.Align.FILL)
        self.progress.set_margin_start(14)
        self.progress.set_margin_end(14)
        self.progress.set_margin_bottom(3)
        self.progress.connect("button-press-event", self._on_seek_press)
        self.progress.connect("button-release-event", self._on_seek_release)
        overlay.add_overlay(self.progress)
        self.add(overlay)
        self._seeking = False
        self._length = 0

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        text.set_valign(Gtk.Align.CENTER)
        self.title = Gtk.Label(xalign=0)
        self.title.get_style_context().add_class("title")
        self.title.set_ellipsize(3)  # END
        self.title.set_max_width_chars(MAX_CHARS)
        self.artist = Gtk.Label(xalign=0)
        self.artist.get_style_context().add_class("artist")
        self.artist.set_ellipsize(3)
        self.artist.set_max_width_chars(MAX_CHARS)
        text.pack_start(self.title, False, False, 0)
        text.pack_start(self.artist, False, False, 0)
        box.pack_start(text, False, False, 0)

        self.prev_btn = self._button("media-skip-backward-symbolic", "Previous")
        self.play_btn = self._button("media-playback-start-symbolic", "Play/Pause")
        self.next_btn = self._button("media-skip-forward-symbolic", "Next")
        self.prev_btn.connect("clicked", lambda *_: self._call("Previous"))
        self.play_btn.connect("clicked", lambda *_: self._call("PlayPause"))
        self.next_btn.connect("clicked", lambda *_: self._call("Next"))
        self._shuffle = False
        self._loop = "None"
        self.shuffle_btn = ModeButton("shuffle")
        self.loop_btn = ModeButton("loop")
        self.shuffle_btn.set_tooltip_text(tr("shuffle"))
        self.loop_btn.set_tooltip_text(tr("loop_off"))
        self.shuffle_btn.connect("clicked", self._toggle_shuffle)
        self.loop_btn.connect("clicked", self._cycle_loop)
        self._track_id = None
        self._liked = False
        self.heart_btn = IconButton("heart")
        self.heart_btn.set_tooltip_text(tr("like"))
        self.heart_btn.connect("clicked", self._toggle_like)
        self.plus_btn = IconButton("plus")
        self.plus_btn.set_tooltip_text(tr("add_pl"))
        self.plus_btn.connect("clicked", self._open_picker)
        self.picker = None
        self._playlists = []
        self.heart_btn.set_margin_start(6)
        for b in (self.heart_btn, self.plus_btn):
            b.set_valign(Gtk.Align.CENTER)
            box.pack_start(b, False, False, 0)
        box.pack_start(Gtk.Box(), True, True, 0)
        for b in (self.shuffle_btn, self.prev_btn, self.play_btn,
                  self.next_btn, self.loop_btn):
            b.set_valign(Gtk.Align.CENTER)
            box.pack_start(b, False, False, 0)

        self._place()
        GLib.timeout_add(POLL_MS, self._tick)
        self._tick()

    def apply_theme(self, t=None):
        """Temayi (yeniden) uygula; ayar penceresi canli onizleme icin cagirir."""
        if t is not None:
            theme.set_theme(t)
        scr = Gdk.Screen.get_default()
        if self._css_provider is not None:
            Gtk.StyleContext.remove_provider_for_screen(scr, self._css_provider)
        p = Gtk.CssProvider()
        p.load_from_data(theme.build_css().encode())
        Gtk.StyleContext.add_provider_for_screen(
            scr, p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self._css_provider = p
        self.queue_draw()

    def _popup_menu(self, event):
        menu = Gtk.Menu()
        item = Gtk.MenuItem(label=tr("settings"))
        item.connect("activate", lambda *_: self.open_settings())
        menu.append(item)
        menu.show_all()
        self._menu = menu
        menu.popup_at_pointer(event)

    def open_settings(self):
        if getattr(self, "settings_win", None):
            self.settings_win.present()
            return
        from . import settings_window
        self.settings_win = settings_window.SettingsWindow(self)
        self.settings_win.show_all()

    def retranslate(self):
        self.shuffle_btn.set_tooltip_text(tr("shuffle"))
        self.loop_btn.set_tooltip_text(tr("loop_off"))
        self.heart_btn.set_tooltip_text(tr("like"))
        self.plus_btn.set_tooltip_text(tr("add_pl"))
        try:
            self._show_shuffle(self._shuffle)
            self._show_loop(self._loop)
        except Exception:
            pass

    def _rgba(self, win):
        scr = win.get_screen()
        vis = scr.get_rgba_visual()
        if vis is not None and scr.is_composited():
            win.set_visual(vis)

    def _button(self, icon, tip):
        btn = Gtk.Button()
        btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        btn.set_tooltip_text(tip)
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_can_focus(False)
        return btn

    def _load_pos(self):
        try:
            with open(CONFIG_FILE) as f:
                d = json.load(f)
            return int(d["x"]), int(d["y"])
        except Exception:
            return None

    def _on_press(self, widget, event):
        if event.button == 3:
            self._popup_menu(event)
            return True
        if event.button == 1:
            self._dragged = True
            edge = self._edge_at(event.x)
            if edge is not None:
                self._user_sized = True
                self.begin_resize_drag(edge, event.button, int(event.x_root),
                                       int(event.y_root), event.time)
            else:
                self.begin_move_drag(event.button, int(event.x_root),
                                     int(event.y_root), event.time)
        return False

    def _edge_at(self, x):
        w = self.get_size()[0]
        if x < EDGE:
            return Gdk.WindowEdge.WEST
        if x > w - EDGE:
            return Gdk.WindowEdge.EAST
        return None

    def _on_motion(self, widget, event):
        gw = self.get_window()
        if gw:
            if self._edge_at(event.x) is not None:
                gw.set_cursor(Gdk.Cursor.new_from_name(gw.get_display(), "ew-resize"))
            else:
                gw.set_cursor(None)
        return False

    def _load_w(self):
        try:
            with open(CONFIG_FILE) as f:
                return int(json.load(f)["w"])
        except Exception:
            return None

    def _on_configure(self, widget, event):
        if self._dragged:
            if self._save_timer:
                GLib.source_remove(self._save_timer)
            self._save_timer = GLib.timeout_add(400, self._save_pos)
        return False

    def _save_pos(self):
        self._save_timer = None
        x, y = self.get_position()
        self.saved_pos = (x, y)
        data = {"x": x, "y": y}
        if self._user_sized or self.user_w:
            self.user_w = self.get_size()[0]
            data["w"] = self.user_w
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, "w") as f:
                json.dump(data, f)
        except OSError:
            pass
        return False

    def _refit(self):
        if self.user_w:
            w = self.user_w
        else:
            w = self.get_child().get_preferred_size()[1].width
        self.resize(max(w, 120), BAR_HEIGHT)
        GLib.timeout_add(80, self._place_once)
        return False

    def _place_once(self):
        self._place()
        return False

    def _place(self):
        if self.saved_pos:
            self.move(*self.saved_pos)
            return
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        geo = monitor.get_geometry()
        x = geo.x + geo.width - self.get_size()[0] - MARGIN_RIGHT
        y = geo.y + geo.height - self.get_size()[1] - MARGIN_BOTTOM
        self.move(x, y)

    def _proxy(self, iface):
        return Gio.DBusProxy.new_sync(
            self.bus, Gio.DBusProxyFlags.NONE, None,
            BUS_NAME, OBJ_PATH, iface, None)

    def _call(self, method):
        try:
            self._proxy(PLAYER_IFACE).call_sync(method, None, Gio.DBusCallFlags.NONE, 500, None)
        except GLib.Error:
            pass
        GLib.timeout_add(150, lambda: self._tick() and False)

    def _get_state(self):
        try:
            props = self._proxy("org.freedesktop.DBus.Properties")
            res = props.call_sync(
                "GetAll", GLib.Variant("(s)", (PLAYER_IFACE,)),
                Gio.DBusCallFlags.NONE, 500, None)
            return res.unpack()[0]
        except GLib.Error:
            return None

    def _fetch_playlists(self):
        me = auth.api("GET", "/me")
        uid = me.get("id") if me else None
        out, off = [], 0
        while True:
            r = auth.api("GET", "/me/playlists", {"limit": 50, "offset": off})
            if not r:
                break
            for pl in r.get("items", []):
                if pl and (pl["owner"]["id"] == uid or pl.get("collaborative")):
                    out.append((pl["name"], pl["id"]))
            if not r.get("next"):
                break
            off += 50
        return out

    def _close_picker(self, *_):
        w, self.picker = self.picker, None
        if w:
            w.destroy()
        return False

    def _open_picker(self, *_):
        if self.picker:
            self._close_picker()
            return
        if not self._sp_id():
            return
        W, H = 260, 320
        w = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self._rgba(w)
        w.set_decorated(False)
        w.set_keep_above(True)
        w.set_skip_taskbar_hint(True)
        w.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        w.set_default_size(W, H)
        self.picker = w
        self._pl_filter = ""

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for m in ("start", "end", "top", "bottom"):
            getattr(vb, "set_margin_" + m)(8)
        w.add(vb)
        entry = Gtk.SearchEntry()
        entry.set_placeholder_text(tr("search_pl"))
        vb.pack_start(entry, False, False, 0)
        sc = Gtk.ScrolledWindow()
        sc.set_vexpand(True)
        lb = Gtk.ListBox()
        sc.add(lb)
        vb.pack_start(sc, True, True, 0)

        def match(row):
            return self._pl_filter in row.pl_name.lower()
        lb.set_filter_func(match)

        def on_changed(e):
            self._pl_filter = e.get_text().lower()
            lb.invalidate_filter()
        entry.connect("search-changed", on_changed)

        def fill(items):
            if self.picker is not w:
                return False
            for c in lb.get_children():
                lb.remove(c)
            for name, pid in self._sort_recent(items):
                row = Gtk.ListBoxRow()
                row.pl_name, row.pl_id = name, pid
                lbl = Gtk.Label(label=name, xalign=0)
                lbl.set_ellipsize(3)
                row.add(lbl)
                lb.add(row)
            lb.show_all()
            return False

        def on_activated(_lb, row):
            self._add_to(row.pl_id)
        lb.connect("row-activated", on_activated)

        def on_enter(_e):
            for row in lb.get_children():
                if match(row):
                    self._add_to(row.pl_id)
                    break
        entry.connect("activate", on_enter)

        def on_key(_w, ev):
            if ev.keyval == Gdk.KEY_Escape:
                self._close_picker()
            return False
        w.connect("key-press-event", on_key)
        w.connect("focus-out-event", self._close_picker)

        x, y = self.get_position()
        bw = self.get_size()[0]
        py = y - H - 6
        if py < 0:
            py = y + BAR_HEIGHT + 6
        w.move(max(x + bw - W, 0), py)
        w.show_all()
        w.present()
        entry.grab_focus()

        if self._playlists:
            fill(self._playlists)
        else:
            row = Gtk.ListBoxRow()
            row.pl_name, row.pl_id = "", None
            row.add(Gtk.Label(label=tr("loading"), xalign=0))
            lb.add(row)
            lb.show_all()

        def work():
            items = self._fetch_playlists()
            if items:
                self._playlists = items
            GLib.idle_add(fill, self._playlists)
        threading.Thread(target=work, daemon=True).start()

    def _add_to(self, pid):
        sid = self._sp_id()
        self._close_picker()
        if not sid or not pid:
            return
        uri = "spotify:track:" + sid

        def work():
            self._remember_playlist(pid)
            if self._playlist_has(pid, sid):
                GLib.idle_add(self._flash_plus, None)
                return
            r = auth.api("POST", "/playlists/%s/items" % pid, body={"uris": [uri]})
            if r is None:
                r = auth.api("POST", "/playlists/%s/tracks" % pid, body={"uris": [uri]})
            GLib.idle_add(self._flash_plus, r is not None)
        threading.Thread(target=work, daemon=True).start()

    def _flash_plus(self, ok):
        st = "dup" if ok is None else ("ok" if ok else "err")
        self.plus_btn.set_state(st)
        GLib.timeout_add(1500, lambda: self.plus_btn.set_state(None) or False)
        return False

    def _on_seek_press(self, *_):
        self._seeking = True
        return False

    def _on_seek_release(self, widget, event):
        pos = int(widget.get_value())
        self._seeking = False
        self._seek_to(pos)
        return False

    def _seek_to(self, pos):
        try:
            cur = int((self._get_state() or {}).get("Position", 0) or 0)
            self._proxy(PLAYER_IFACE).call_sync(
                "Seek", GLib.Variant("(x)", (int(pos) - cur,)),
                Gio.DBusCallFlags.NONE, 500, None)
        except Exception:
            try:
                self._proxy(PLAYER_IFACE).call_sync(
                    "SetPosition", GLib.Variant("(ox)", (self._track_id, int(pos))),
                    Gio.DBusCallFlags.NONE, 500, None)
            except Exception:
                pass
        GLib.timeout_add(300, lambda: self._tick() and False)

    def _sort_recent(self, items):
        try:
            with open(RECENT_FILE) as f:
                rec = json.load(f)
        except Exception:
            rec = []
        rank = {pid: i for i, pid in enumerate(rec)}
        return sorted(items, key=lambda it: rank.get(it[1], len(rank)))

    def _remember_playlist(self, pid):
        try:
            with open(RECENT_FILE) as f:
                rec = json.load(f)
        except Exception:
            rec = []
        rec = [pid] + [x for x in rec if x != pid]
        try:
            os.makedirs(os.path.dirname(RECENT_FILE), exist_ok=True)
            with open(RECENT_FILE, "w") as f:
                json.dump(rec[:30], f)
        except OSError:
            pass

    def _playlist_has(self, pid, sid):
        for base in ("/playlists/%s/items", "/playlists/%s/tracks"):
            off, ok = 0, False
            while off < 10000:
                r = auth.api("GET", base % pid, {"limit": 100, "offset": off})
                if r is None:
                    break
                ok = True
                for it in r.get("items", []):
                    it = it or {}
                    t = it.get("item") or it.get("track") or {}
                    if t.get("id") == sid:
                        return True
                if not r.get("next"):
                    return False
                off += 100
            if ok:
                return False
        return False

    def _sp_id(self):
        t = self._track_id or ""
        pre = "/com/spotify/track/"
        return t[len(pre):] if t.startswith(pre) else None

    def _set_heart(self, liked):
        self._liked = liked
        self.heart_btn.set_state(liked)
        return False

    def _refresh_like(self):
        sid = self._sp_id()
        self._set_heart(False)
        if not sid:
            return

        def work():
            r = auth.api("GET", "/me/library/contains",
                                 {"uris": "spotify:track:" + sid})
            if r is None:
                r = auth.api("GET", "/me/tracks/contains", {"ids": sid})
            liked = bool(r and r[0])
            if sid == self._sp_id():
                GLib.idle_add(self._set_heart, liked)
        threading.Thread(target=work, daemon=True).start()

    def _toggle_like(self, *_):
        sid = self._sp_id()
        if not sid:
            return
        new = not self._liked
        self._set_heart(new)

        def work():
            m = "PUT" if new else "DELETE"
            r = auth.api(m, "/me/library", {"uris": "spotify:track:" + sid})
            if r is None:
                r = auth.api(m, "/me/tracks", body={"ids": [sid]})
            if r is None and sid == self._sp_id():
                GLib.idle_add(self._set_heart, not new)
        threading.Thread(target=work, daemon=True).start()

    def _set_prop(self, name, value):
        try:
            self._proxy("org.freedesktop.DBus.Properties").call_sync(
                "Set", GLib.Variant("(ssv)", (PLAYER_IFACE, name, value)),
                Gio.DBusCallFlags.NONE, 500, None)
        except GLib.Error:
            pass
        GLib.timeout_add(150, lambda: self._tick() and False)

    def _show_shuffle(self, on):
        self._shuffle = on
        self.shuffle_btn.update(on)
        self.shuffle_btn.set_tooltip_text(tr("shuffle_on") if on else tr("shuffle_off"))

    def _show_loop(self, mode):
        self._loop = mode
        self.loop_btn.update(mode != "None", mode)
        tips = {"None": tr("loop_off"), "Playlist": tr("loop_pl"),
                "Track": tr("loop_track")}
        self.loop_btn.set_tooltip_text(tips.get(mode, tr("loop_off")))

    def _toggle_shuffle(self, *_):
        new = not self._shuffle
        self._show_shuffle(new)
        self._set_prop("Shuffle", GLib.Variant("b", new))

    def _cycle_loop(self, *_):
        order = ["None", "Playlist", "Track"]
        cur = self._loop if self._loop in order else "None"
        new = order[(order.index(cur) + 1) % 3]
        self._show_loop(new)
        self._set_prop("LoopStatus", GLib.Variant("s", new))

    def _tick(self):
        state = self._get_state()
        if not state or state.get("PlaybackStatus") not in ("Playing", "Paused"):
            if self.get_visible():
                self.hide()
            return True

        meta = state.get("Metadata", {})
        tid = str(meta.get("mpris:trackid", ""))
        if tid != self._track_id:
            self._track_id = tid
            self._refresh_like()
        try:
            length = int(meta.get("mpris:length", 0) or 0)
            pos = int(state.get("Position", 0) or 0)
        except (TypeError, ValueError):
            length, pos = 0, 0
        self._length = length
        if not self._seeking:
            self.progress.set_range(0, max(length, 1))
            self.progress.set_value(min(max(pos, 0), max(length, 1)))
        self.progress.set_sensitive(length > 0)
        new_title = meta.get("xesam:title", "Unknown")
        artists = meta.get("xesam:artist", [])
        new_artist = ", ".join(artists) if artists else ""
        if (new_title, new_artist) != self._last_text:
            self._last_text = (new_title, new_artist)
            self.title.set_text(new_title)
            self.artist.set_text(new_artist)
            GLib.timeout_add(120, self._refit)

        icon = ("media-playback-pause-symbolic"
                if state["PlaybackStatus"] == "Playing"
                else "media-playback-start-symbolic")
        self.play_btn.set_image(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        sh = bool(state.get("Shuffle", False))
        if sh != self._shuffle:
            self._show_shuffle(sh)
        lp = str(state.get("LoopStatus", "None"))
        if lp != self._loop:
            self._show_loop(lp)

        if not self.get_visible():
            self.show_all()
            self._place()
            self.set_keep_above(True)
        return True


def _single_instance():
    """Returns an open lock file object, or None if another instance is running."""
    import fcntl
    rt = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    f = open(os.path.join(rt, "another-spotibar-%d.lock" % os.getuid()), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def main():
    lock = _single_instance()
    if lock is None:
        print("another-spotibar is already running.")
        return 0
    from . import setup
    if not setup.run():
        return 0
    win = SpotifyBar()
    win.connect("destroy", Gtk.main_quit)
    Gtk.main()
    lock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
