from .i18n import tr
import base64, hashlib, json, os, re, secrets, time, webbrowser
import urllib.parse, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

REDIRECT_URI = "http://127.0.0.1:8888/callback"
SCOPES = ("user-library-read user-library-modify playlist-read-private "
          "playlist-read-collaborative playlist-modify-public playlist-modify-private")
from .paths import TOKEN_FILE, CLIENT_FILE
CLIENT_ID_RE = re.compile(r"^[0-9a-f]{32}$")


def get_client_id():
    try:
        with open(CLIENT_FILE) as f:
            cid = str(json.load(f).get("client_id", "")).strip().lower()
        return cid if CLIENT_ID_RE.match(cid) else None
    except (OSError, ValueError, AttributeError):
        return None


def save_client_id(cid):
    os.makedirs(os.path.dirname(CLIENT_FILE), exist_ok=True)
    with open(CLIENT_FILE, "w") as f:
        json.dump({"client_id": cid}, f)


def has_token():
    return os.path.exists(TOKEN_FILE)


def _token_request(data):
    data["client_id"] = get_client_id()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode(data).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


def _save(tok, old_refresh=None):
    tok["expires_at"] = time.time() + tok.get("expires_in", 3600)
    tok.setdefault("refresh_token", old_refresh)
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(tok, f)
    os.chmod(TOKEN_FILE, 0o600)
    return tok


def login():
    cid = get_client_id()
    if not cid:
        raise RuntimeError(tr("no_client"))
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": cid, "response_type": "code",
        "redirect_uri": REDIRECT_URI, "scope": SCOPES, "state": state,
        "code_challenge_method": "S256", "code_challenge": challenge})
    result = {}

    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(tr("login_done").encode())

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 8888), H)
    srv.timeout = 180
    print("Opening your browser...\n" + url)
    webbrowser.open(url)
    try:
        srv.handle_request()
    finally:
        srv.server_close()
    if result.get("state") != state or "code" not in result:
        raise RuntimeError(tr("login_fail") % (result.get("error") or tr("no_response")))
    return _save(_token_request({
        "grant_type": "authorization_code", "code": result["code"],
        "redirect_uri": REDIRECT_URI, "code_verifier": verifier}))


def get_token():
    with open(TOKEN_FILE) as f:
        tok = json.load(f)
    if tok["expires_at"] - 60 > time.time():
        return tok["access_token"]
    new = _token_request({"grant_type": "refresh_token",
                          "refresh_token": tok["refresh_token"]})
    return _save(new, tok["refresh_token"])["access_token"]


def api(method, path, params=None, body=None):
    url = "https://api.spotify.com/v1" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + get_token(),
        "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print("Spotify API error", e.code, e.read().decode()[:300])
        return None


if __name__ == "__main__":
    if not get_client_id():
        print("No client ID yet. Run `another-spotibar` first to open the setup window.")
    else:
        login()
        me = api("GET", "/me")
        print("Giriş OK:", me and me.get("display_name"))
