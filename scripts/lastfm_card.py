"""Builds assets/lastfm.svg: a cute 'now spinning' card from Last.fm data.
Runs in GitHub Actions (needs env LASTFM_API_KEY). With --demo it renders sample data."""
import base64, json, os, sys, time, urllib.parse, urllib.request
from html import escape

USER = "u-u-u-u-u"
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "lastfm.svg")
API = "https://ws.audioscrobbler.com/2.0/"


def call(method, **kw):
    q = urllib.parse.urlencode({"method": method, "user": USER, "api_key": os.environ["LASTFM_API_KEY"], "format": "json", **kw})
    with urllib.request.urlopen(API + "?" + q, timeout=20) as r:
        return json.load(r)


PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"   # last.fm's grey star "no art" image


def art_b64(url):
    if not url or PLACEHOLDER in url:
        return None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (readme card)"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
            kind = r.headers.get_content_type() or ""
        if not kind.startswith("image/"):
            kind = "image/png" if data[:4] == b"\x89PNG" else "image/gif" if data[:3] == b"GIF" else "image/jpeg"
        print("art ok", url, kind, len(data))
        return f"data:{kind};base64," + base64.b64encode(data).decode()
    except Exception as e:
        print("art failed", url, e)
        return None


def fetch():
    rt = call("user.getrecenttracks", limit=5, extended=0)["recenttracks"]
    tracks = []
    for t in rt["track"][:5]:
        imgs = {i["size"]: i["#text"] for i in t.get("image", [])}
        print("track", t["name"], "-", t["artist"]["#text"], imgs.get("extralarge"))
        tracks.append({
            "name": t["name"], "artist": t["artist"]["#text"], "album": (t.get("album") or {}).get("#text", ""),
            "art": art_b64(imgs.get("extralarge") or imgs.get("large")),
            "now": t.get("@attr", {}).get("nowplaying") == "true",
            "uts": int(t["date"]["uts"]) if "date" in t else int(time.time()),
        })
    top = call("user.gettopartists", period="7day", limit=5)["topartists"]["artist"]
    info = call("user.getinfo")["user"]
    return {"tracks": tracks, "top": [(a["name"], int(a["playcount"])) for a in top],
            "total": int(info.get("playcount", 0))}


def demo():
    names = [("Kiss the Ladder", "Fleshwater"), ("Paleta", "rommulas"), ("Back 2 U (AM 01:27)", "NCT 127"),
             ("Switch - Bonus Track", "NCT 127"), ("Pink Pantheress", "Just for me")]
    now = int(time.time())
    return {"tracks": [{"name": n, "artist": a, "album": "KISS KISS (Single)", "art": None, "now": i == 0, "uts": now - i * 1800} for i, (n, a) in enumerate(names)],
            "top": [("NCT 127", 42), ("Fleshwater", 31), ("rommulas", 18), ("PinkPantheress", 12)], "total": 12345}


def ago(uts):
    s = max(0, int(time.time()) - uts)
    if s < 3600: return f"{max(1, s // 60)}m ago"
    if s < 86400: return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def cut(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


PINK, HOT, LAV, INK, MINT, YEL, BLUE = "#ffe4f1", "#ff5caa", "#a073ff", "#2a1838", "#46cd9b", "#ffcd32", "#46a0ff"
FONT = "'Trebuchet MS','Segoe UI','Nunito',Verdana,sans-serif"


def art(x, y, s, src, clip_id, rx=8):
    if src:
        return (f'<clipPath id="{clip_id}"><rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{rx}"/></clipPath>'
                f'<image href="{src}" x="{x}" y="{y}" width="{s}" height="{s}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{clip_id})"/>')
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{rx}" fill="url(#ph)"/>'
            f'<text x="{x + s / 2}" y="{y + s / 2 + s * .14}" text-anchor="middle" font-size="{s * .42}" fill="#fff" font-family="{FONT}">♪</text>')


def render(d):
    CHIBI = "data:image/png;base64," + base64.b64encode(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "shima-chibi.png"), "rb").read()).decode()
    W, H = 560, 372
    t0 = d["tracks"][0]
    status = ("● scrobbling now", HOT) if t0["now"] else (f"♡ last played {ago(t0['uts'])}", LAV)
    album_line = (f'<text x="168" y="174" font-family="{FONT}" font-size="11.5" font-style="italic" font-weight="700" fill="{LAV}">💿 {escape(cut(t0.get("album", ""), 34))}</text>' if t0.get("album") else "")
    moods = ["this one slaps ♡", "on loop rn ♪", "no skips ✧", "ear candy (˶ᵔᵕᵔ˶)", "vibing ♪(´▽｀)", "10/10 ♡"]
    h = sum(map(ord, t0["name"]))
    bubble = moods[h % len(moods)]
    mood = ["jersey club hours", "3am playlist", "edm saves all", "volume: max", "do not disturb"][h % 5]
    disc_art = (f'<image href="{t0["art"]}" x="462" y="90" width="76" height="76" preserveAspectRatio="xMidYMid slice" clip-path="url(#disc)"/>'
                if t0["art"] else '<circle cx="500" cy="128" r="38" fill="url(#ph)"/>')
    bars = "".join(f'<rect class="eq" style="animation-delay:-{i * .13:.2f}s" x="{168 + i * 9}" y="142" width="6" height="18" rx="3" fill="{[HOT, LAV, BLUE, MINT, YEL][i % 5]}"/>' for i in range(10))
    tiles = ""
    for i, t in enumerate(d["tracks"][1:5]):
        x = 28 + i * 130
        rot = [-4, 3, -2, 4][i]
        tiles += (f'<g class="bob" style="animation-delay:-{i * .4:.1f}s"><g transform="rotate({rot} {x + 56} 266)">'
                  f'<rect x="{x}" y="220" width="112" height="94" rx="12" fill="#fff" stroke="{[HOT, LAV, BLUE, MINT][i]}" stroke-width="2.5"/>'
                  f'{art(x + 31, 227, 50, t["art"], f"c{i}")}'
                  f'<text x="{x + 56}" y="291" text-anchor="middle" font-family="{FONT}" font-size="11.5" font-weight="700" fill="{INK}">{escape(cut(t["name"], 16))}</text>'
                  f'<text x="{x + 56}" y="305" text-anchor="middle" font-family="{FONT}" font-size="10.5" fill="{HOT}">{escape(cut(t["artist"], 17))}</text>'
                  f'</g></g>')
    pills, px = "", 112
    for i, (name, n) in enumerate(d["top"]):
        label = f"{cut(name, 12)} · {n}"
        w = len(label) * 6.2 + 16
        if px + w > W - 20: break
        pills += (f'<rect x="{px}" y="328" width="{w:.0f}" height="24" rx="12" fill="{[HOT, LAV, BLUE, MINT][i % 4]}" stroke="#fff" stroke-width="2"/>'
                  f'<text x="{px + w / 2:.0f}" y="344" text-anchor="middle" font-family="{FONT}" font-size="11" font-weight="700" fill="#fff">{escape(label)}</text>')
        px += w + 8
    hearts = "".join(f'<g transform="translate({x} {y}) scale({s})"><path class="pop" style="animation-delay:{i * .3}s" d="M0 4C-6-4-14 2-8 8L0 15 8 8C14 2 6-4 0 4z" fill="{c}" stroke="#fff" stroke-width="1.5"/></g>'
                     for i, (x, y, s, c) in enumerate([(40, 12, 1.3, HOT), (520, 12, 1.3, LAV), (110, 12, .8, "#fff"), (450, 12, .8, "#fff"), (532, 72, .8, HOT)]))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
.eq{{animation:eq .9s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}}@keyframes eq{{0%,100%{{transform:scaleY(.25)}}50%{{transform:scaleY(1)}}}}
.bob{{animation:bob 2.6s ease-in-out infinite}}@keyframes bob{{50%{{transform:translateY(-4px)}}}}
.pop{{animation:pop 1.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}@keyframes pop{{50%{{transform:scale(1.18)}}}}
.dot{{animation:dot 1s steps(1) infinite}}@keyframes dot{{50%{{opacity:.3}}}}
.prog{{animation:prog 6s linear infinite;transform-box:fill-box;transform-origin:0 50%}}@keyframes prog{{from{{transform:scaleX(.03)}}to{{transform:scaleX(1)}}}}
.bob2{{animation:bob2 1.8s ease-in-out infinite}}@keyframes bob2{{50%{{transform:translateY(-3px)}}}}
.spin{{animation:spin 3s linear infinite;transform-box:fill-box;transform-origin:center}}@keyframes spin{{to{{transform:rotate(360deg)}}}}
</style>
<defs>
<pattern id="ck" width="12" height="12" patternUnits="userSpaceOnUse"><rect width="6" height="6" fill="#fff" opacity=".5"/><rect x="6" y="6" width="6" height="6" fill="#fff" opacity=".5"/></pattern>
<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="7" cy="7" r="1.1" fill="{HOT}" opacity=".25"/></pattern>
<linearGradient id="pg" x1="0" x2="1"><stop offset="0" stop-color="#ff5caa"/><stop offset=".5" stop-color="#b89cff"/><stop offset="1" stop-color="#46a0ff"/></linearGradient>
<linearGradient id="ph" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb3dd"/><stop offset="1" stop-color="#b89cff"/></linearGradient>
<clipPath id="card"><rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26"/></clipPath>
</defs>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="#fff0f8"/>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="url(#dots)"/>
<g clip-path="url(#card)"><rect x="0" y="0" width="{W}" height="44" fill="#ffc2df"/><rect x="0" y="0" width="{W}" height="44" fill="url(#ck)"/></g>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="none" stroke="#fff" stroke-width="3"/>
<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="21" fill="none" stroke="{HOT}" stroke-width="1.3" stroke-dasharray="4 3"/>
<text x="{W / 2}" y="32" text-anchor="middle" font-family="{FONT}" font-size="21" font-weight="900" fill="#fff" stroke="{HOT}" stroke-width="5" stroke-linejoin="round" paint-order="stroke">♪ now spinning ♪</text>
{hearts}
<g transform="rotate(-4 80 116)"><rect x="26" y="58" width="108" height="124" fill="#fff" stroke="#ffc2df" stroke-width="2"/>
<rect x="56" y="51" width="48" height="15" fill="{LAV}" opacity=".8"/>
{art(33, 65, 94, t0["art"], "big", 2)}
<text x="80" y="175" text-anchor="middle" font-family="{FONT}" font-size="11" font-weight="900" fill="{HOT}">(◕‿◕)♪</text></g>
<rect x="166" y="64" width="{len(status[0]) * 7 + 22}" height="22" rx="11" fill="#fff" stroke="{status[1]}" stroke-width="2"/>
<text class="{'dot' if t0['now'] else ''}" x="177" y="79" font-family="{FONT}" font-size="12" font-weight="800" fill="{status[1]}">{escape(status[0])}</text>
<text x="168" y="114" font-family="{FONT}" font-size="22" font-weight="900" fill="{INK}">{escape(cut(t0["name"], 17))}</text>
<text x="168" y="138" font-family="{FONT}" font-size="16" font-weight="700" fill="{HOT}">{escape(cut(t0["artist"], 22))}</text>
{bars}
{album_line}
<rect x="168" y="182" width="214" height="8" rx="4" fill="#ffd6ea"/>
<rect class="prog" x="168" y="182" width="214" height="8" rx="4" fill="url(#pg)"/>
<text x="168" y="204" font-family="{FONT}" font-size="10" font-weight="800" fill="{LAV}">♪ on repeat</text>
<text x="380" y="204" text-anchor="end" font-family="{FONT}" font-size="10" font-weight="800" fill="{LAV}">♡ {mood}</text>
<g transform="translate(346 48)"><path d="M14 0H112A14 14 0 0 1 126 14V16A14 14 0 0 1 112 30H90L84 40L76 30H14A14 14 0 0 1 0 16V14A14 14 0 0 1 14 0Z" fill="#fff" stroke="{LAV}" stroke-width="2" stroke-linejoin="round"/>
<text x="63" y="20" text-anchor="middle" font-family="{FONT}" font-size="11.5" font-weight="800" fill="{HOT}">{bubble}</text></g>
<clipPath id="disc"><circle cx="500" cy="128" r="38"/></clipPath>
<g class="spin">{disc_art}<circle cx="500" cy="128" r="38" fill="none" stroke="#fff" stroke-width="3"/><circle cx="500" cy="128" r="9" fill="#fff0f8" stroke="#fff" stroke-width="2"/></g>
<g class="bob2"><image href="{CHIBI}" x="390" y="80" width="76" height="120"/></g>
<text x="500" y="186" text-anchor="middle" font-family="{FONT}" font-size="10.5" font-weight="800" fill="{LAV}">{d["total"]:,} plays</text>
<text x="30" y="212" font-family="{FONT}" font-size="11" font-weight="800" fill="{LAV}">recently ♡</text>
{tiles}
<text x="26" y="345" font-family="{FONT}" font-size="11.5" font-weight="800" fill="{LAV}">top this week:</text>
{pills}
</svg>'''


if __name__ == "__main__":
    data = demo() if "--demo" in sys.argv else fetch()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(render(data))
    print("wrote", OUT)
