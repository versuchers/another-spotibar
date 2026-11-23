"""Minimal i18n: English (default) and Turkish."""
import json
import os

from .paths import LANG_FILE

STR = {
    "en": {
        "like": "Like",
        "settings": "Settings",
        "skin": "Skin",
        "language": "Language",
        "title_size": "Title size",
        "artist_size": "Artist size",
        "radius": "Corner radius",
        "progress_h": "Progress bar thickness",
        "save": "Save",
        "cancel": "Cancel",
        "colors": "Colors",
        "skin_name": "New skin name",
        "save_as": "Save as skin",
        "bad_name": "Name: letters, digits, - or _ only (max 40).",
        "name_builtin": "That name belongs to a built-in skin.",
        "save_fail_skin": "Could not save the skin.",
        "c_bg": "Background",
        "c_border": "Border",
        "c_title_color": "Title",
        "c_artist_color": "Artist",
        "c_button": "Buttons",
        "c_icon": "Icons",
        "c_icon_active": "Active icons",
        "c_mode_off": "Inactive icons",
        "c_liked": "Liked heart",
        "c_progress_fill": "Progress bar",
        "c_knob": "Progress knob",
        "c_row_text": "List text",
        "add_pl": "Add to playlist",
        "shuffle": "Shuffle",
        "shuffle_on": "Shuffle: on",
        "shuffle_off": "Shuffle: off",
        "loop_off": "Repeat: off",
        "loop_pl": "Repeat: playlist/album",
        "loop_track": "Repeat: track",
        "search_pl": "Search playlists...",
        "loading": "Loading...",
        "login_done": "Login complete, you can close this tab.",
        "no_client": "Client ID is missing or invalid.",
        "login_fail": "Login failed or timed out: %s",
        "no_response": "no response",
        "setup_title": "Spotify Bar setup",
        "steps": (
            "To run Spotify Bar you need to create your own Spotify app "
            "(one time, about 2 minutes):\n\n"
            "1. Open the Developer Dashboard below and log in.\n"
            "2. Click \"Create app\". Name and description can be anything.\n"
            "3. Add the address below to \"Redirect URIs\".\n"
            "4. Tick \"Web API\" and save.\n"
            "5. Copy the Client ID from the app's Settings page and paste it below."),
        "open_dash": "Open Developer Dashboard",
        "copy": "Copy",
        "id_hint": "Client ID (32 characters)",
        "save_login": "Save and log in",
        "login": "Log in",
        "need_login": "You need to log in to your Spotify account.",
        "bad_id": "Client ID must be 32 characters (a-f, 0-9).",
        "save_fail": "Could not save: %s",
        "waiting": "Approve the Spotify login in your browser (within 3 minutes)...",
        "err": "Error: %s",
        "lang_btn": "Türkçe",
    },
    "tr": {
        "like": "Beğen",
        "settings": "Ayarlar",
        "skin": "Skin",
        "language": "Dil",
        "title_size": "Başlık boyutu",
        "artist_size": "Sanatçı boyutu",
        "radius": "Köşe yuvarlaklığı",
        "progress_h": "İlerleme çubuğu kalınlığı",
        "save": "Kaydet",
        "cancel": "İptal",
        "colors": "Renkler",
        "skin_name": "Yeni skin adı",
        "save_as": "Skin olarak kaydet",
        "bad_name": "Ad: sadece harf, rakam, - veya _ (en çok 40).",
        "name_builtin": "Bu ad hazır bir skine ait.",
        "save_fail_skin": "Skin kaydedilemedi.",
        "c_bg": "Arka plan",
        "c_border": "Kenarlık",
        "c_title_color": "Başlık",
        "c_artist_color": "Sanatçı",
        "c_button": "Düğmeler",
        "c_icon": "İkonlar",
        "c_icon_active": "Aktif ikonlar",
        "c_mode_off": "Pasif ikonlar",
        "c_liked": "Beğenilmiş kalp",
        "c_progress_fill": "İlerleme çubuğu",
        "c_knob": "İlerleme topuzu",
        "c_row_text": "Liste yazısı",
        "add_pl": "Playlist'e ekle",
        "shuffle": "Karıştır",
        "shuffle_on": "Karıştır: açık",
        "shuffle_off": "Karıştır: kapalı",
        "loop_off": "Döngü: kapalı",
        "loop_pl": "Döngü: playlist/albüm",
        "loop_track": "Döngü: şarkı",
        "search_pl": "Playlist ara...",
        "loading": "Yükleniyor...",
        "login_done": "Giriş tamam, bu sekmeyi kapatabilirsin.",
        "no_client": "Client ID yok veya geçersiz.",
        "login_fail": "Giriş başarısız veya zaman aşımı: %s",
        "no_response": "yanıt yok",
        "setup_title": "Spotify Bar kurulumu",
        "steps": (
            "Spotify Bar'ın çalışması için kendi Spotify uygulamanı oluşturman gerekiyor "
            "(bir kerelik, yaklaşık 2 dakika):\n\n"
            "1. Aşağıdaki bağlantıdan Developer Dashboard'u aç ve giriş yap.\n"
            "2. \"Create app\" de. Ad ve açıklama serbest.\n"
            "3. \"Redirect URIs\" alanına aşağıdaki adresi ekle.\n"
            "4. \"Web API\" seçeneğini işaretleyip kaydet.\n"
            "5. Uygulamanın Settings sayfasındaki Client ID'yi aşağıya yapıştır."),
        "open_dash": "Developer Dashboard'u aç",
        "copy": "Kopyala",
        "id_hint": "Client ID (32 karakter)",
        "save_login": "Kaydet ve giriş yap",
        "login": "Giriş yap",
        "need_login": "Spotify hesabına giriş yapman gerekiyor.",
        "bad_id": "Client ID 32 karakterlik harf/rakam olmalı (a-f, 0-9).",
        "save_fail": "Kaydedilemedi: %s",
        "waiting": "Tarayıcıda Spotify girişini onayla (3 dakika içinde)...",
        "err": "Hata: %s",
        "lang_btn": "English",
    },
}

_lang = None


def get_lang():
    global _lang
    if _lang is None:
        try:
            with open(LANG_FILE) as f:
                v = json.load(f).get("lang")
            _lang = v if v in STR else "en"
        except (OSError, ValueError, AttributeError):
            _lang = "en"
    return _lang


def set_lang(lang):
    global _lang
    _lang = lang if lang in STR else "en"
    try:
        os.makedirs(os.path.dirname(LANG_FILE), exist_ok=True)
        with open(LANG_FILE, "w") as f:
            json.dump({"lang": _lang}, f)
    except OSError:
        pass


def tr(key):
    return STR[get_lang()].get(key) or STR["en"].get(key, key)
