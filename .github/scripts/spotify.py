"""Genera dist/spotify.svg con la canción actual (o la última escuchada)."""
import base64
import html
import json
import os
import urllib.parse
import urllib.request

CLIENT_ID = os.environ["SPOTIFY_CLIENT_ID"]
CLIENT_SECRET = os.environ["SPOTIFY_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["SPOTIFY_REFRESH_TOKEN"]


def http(url, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def access_token():
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    body = urllib.parse.urlencode(
        {"grant_type": "refresh_token", "refresh_token": REFRESH_TOKEN}
    ).encode()
    _, raw = http(
        "https://accounts.spotify.com/api/token",
        body,
        {"Authorization": f"Basic {auth}",
         "Content-Type": "application/x-www-form-urlencoded"},
    )
    return json.loads(raw)["access_token"]


def get_track(token):
    h = {"Authorization": f"Bearer {token}"}
    status, raw = http("https://api.spotify.com/v1/me/player/currently-playing", headers=h)
    if status == 200 and raw:
        data = json.loads(raw)
        if data.get("item") and data.get("currently_playing_type") == "track":
            return data["item"], data.get("is_playing", False)
    _, raw = http("https://api.spotify.com/v1/me/player/recently-played?limit=1", headers=h)
    items = json.loads(raw).get("items", [])
    return (items[0]["track"], False) if items else (None, False)


def cover_b64(track):
    images = track["album"]["images"]
    if not images:
        return ""
    url = min(images, key=lambda i: i.get("width") or 999)["url"] if len(images) > 2 else images[-1]["url"]
    _, raw = http(url)
    return base64.b64encode(raw).decode()


def cut(text, n):
    return text if len(text) <= n else text[: n - 1] + "…"


def render(track, playing):
    if not track:
        title, artist, img = "Nada sonando", "Spotify", ""
    else:
        title = track["name"]
        artist = ", ".join(a["name"] for a in track["artists"])
        img = cover_b64(track)
    status = "🎧 Escuchando ahora" if playing else "⏮ Último escuchado"
    title, artist = html.escape(cut(title, 30)), html.escape(cut(artist, 36))
    cover = (
        f'<image href="data:image/jpeg;base64,{img}" x="16" y="16" width="88" height="88" clip-path="url(#r)"/>'
        if img else '<rect x="16" y="16" width="88" height="88" rx="8" fill="#1DB954"/>'
    )
    bars = ""
    if playing:
        for i, d in enumerate(["0.9s", "0.7s", "1.1s", "0.8s"]):
            x = 120 + i * 8
            bars += (
                f'<rect x="{x}" y="88" width="5" height="16" rx="2" fill="#1DB954">'
                f'<animate attributeName="height" values="4;16;8;14;4" dur="{d}" repeatCount="indefinite"/>'
                f'<animate attributeName="y" values="100;88;96;90;100" dur="{d}" repeatCount="indefinite"/></rect>'
            )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120" viewBox="0 0 400 120">
<defs><clipPath id="r"><rect x="16" y="16" width="88" height="88" rx="8"/></clipPath></defs>
<rect width="400" height="120" rx="12" fill="#011627" stroke="#1DB954" stroke-opacity="0.4"/>
{cover}
<g font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">
<text x="120" y="36" fill="#1DB954" font-size="12" font-weight="600">{status}</text>
<text x="120" y="60" fill="#ffffff" font-size="16" font-weight="700">{title}</text>
<text x="120" y="80" fill="#a8b2c1" font-size="13">{artist}</text>
</g>
{bars}
</svg>
"""


if __name__ == "__main__":
    track, playing = get_track(access_token())
    os.makedirs("dist", exist_ok=True)
    with open("dist/spotify.svg", "w", encoding="utf-8") as f:
        f.write(render(track, playing))
    print("OK:", track["name"] if track else "sin canción", "| playing:", playing)
