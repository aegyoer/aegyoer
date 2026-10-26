"""Builds assets/letterboxd.svg: a cute little movie theater card from a public Letterboxd profile.
- the screen shows what you watched most recently
- "top 4" shows the 4 favourite films on your profile
- "history" is a film strip of your diary that scrolls
Runs in GitHub Actions (no key needed). With --demo it renders sample data."""
import base64, os, re, sys, urllib.request
from datetime import date, datetime
from html import escape, unescape

USER = "fents"
# leave empty to use the 4 favourites on your letterboxd profile,
# or type your own like: TOP4 = ["Perfect Blue", "Paprika", "Spirited Away", "Tokyo Godfathers"]
TOP4 = []

FEED = f"https://letterboxd.com/{USER}/rss/"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "letterboxd.svg")
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

HOT, LAV, INK, MINT, YEL, BLUE = "#ff5caa", "#a073ff", "#2a1838", "#46cd9b", "#ffcd32", "#46a0ff"
FONT = "'Trebuchet MS','Segoe UI','Nunito',Verdana,sans-serif"
SIZES = {"big": (230, 345), "mid": (150, 225), "small": (70, 105)}


# ------------------------------------------------------------------ fetching
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read(), r.headers.get_content_type() or ""


def poster_b64(url, size):
    if not url:
        return None
    w, h = SIZES[size]
    for u in [re.sub(r"-0-\d+-0-\d+-crop", f"-0-{w}-0-{h}-crop", url), url]:
        try:
            data, kind = get(u)
            if not kind.startswith("image/"):
                kind = "image/png" if data[:4] == b"\x89PNG" else "image/jpeg"
            print("poster ok", u, len(data))
            return f"data:{kind};base64," + base64.b64encode(data).decode()
        except Exception as e:
            print("poster failed", u, e)
    return None


def tag(item, name):
    m = re.search(rf"<{name}>(.*?)</{name}>", item, re.S)
    return unescape(m.group(1).strip()) if m else ""


def read_feed():
    xml = get(FEED)[0].decode("utf-8", "replace")
    films = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        title = tag(item, "letterboxd:filmTitle")
        if not title:              # lists are in the feed too, skip them
            continue
        desc = re.sub(r"^<!\[CDATA\[|\]\]>$", "", tag(item, "description"))
        img = re.search(r'<img src="([^"]+)"', desc)
        review = " ".join(re.sub(r"<[^>]+>", " ", p) for p in re.findall(r"<p>(.*?)</p>", desc, re.S) if "<img" not in p)
        review = re.sub(r"\s+", " ", unescape(review)).replace("This review may contain spoilers. I can handle the truth.", "").strip()
        if re.match(r"^(Re)?[Ww]atched on ", review):
            review = ""
        rating = tag(item, "letterboxd:memberRating")
        films.append({
            "title": title, "year": tag(item, "letterboxd:filmYear"),
            "rating": float(rating) if rating else None,
            "liked": tag(item, "letterboxd:memberLike") == "Yes",
            "rewatch": tag(item, "letterboxd:rewatch") == "Yes",
            "watched": tag(item, "letterboxd:watchedDate"), "review": review,
            "img": img.group(1) if img else None,
            "slug": (re.search(r"/film/([^/]+)/", tag(item, "link")) or [None, None])[1],
        })
    if not films:
        raise SystemExit("no films found in the feed")
    return films


POSTER_RE = r'(https://a\.ltrbxd\.com/resized/[^"\'\s]+?\.jpg(?:\?[^"\'\s]*)?)'


def poster_for_slug(slug):
    for u in [f"https://letterboxd.com/ajax/poster/film/{slug}/std/150x225/",
              f"https://letterboxd.com/film/{slug}/poster/std/150/",
              f"https://letterboxd.com/film/{slug}/"]:
        try:
            html = get(u)[0].decode("utf-8", "replace")
            m = re.search(POSTER_RE, html)
            if m:
                return unescape(m.group(1))
        except Exception as e:
            print("poster page failed", u, e)
    return None


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def top4(films):
    by_title = {f["title"].lower(): f for f in films}
    picks = []
    if TOP4:
        picks = [(t, slugify(t)) for t in TOP4[:4]]
    else:
        try:
            html = get(f"https://letterboxd.com/{USER}/")[0].decode("utf-8", "replace")
            sec = re.search(r'id="favourites".*?</section>', html, re.S)
            sec = sec.group(0) if sec else ""
            slugs = (re.findall(r'data-(?:film|item)-slug="([^"]+)"', sec)
                     or re.findall(r'data-target-link="/film/([^/"]+)/', sec)
                     or re.findall(r'href="/film/([^/"]+)/"', sec))
            slugs = list(dict.fromkeys(slugs))[:4]
            names = re.findall(r'data-item-name="([^"]+)"', sec) or re.findall(r'<img[^>]*alt="([^"]+)"', sec)
            for i, sl in enumerate(slugs):
                n = unescape(names[i]) if i < len(names) else sl.replace("-", " ").title()
                picks.append((re.sub(r"\s*\(\d{4}\)$", "", n), sl))
            print("favourites from profile:", picks)
        except Exception as e:
            print("couldn't read profile favourites:", e)
    if not picks:   # fall back to your highest rated films in the diary
        seen, best = set(), []
        for f in sorted(films, key=lambda f: (f["rating"] or 0, f["liked"]), reverse=True):
            if f["title"] not in seen:
                seen.add(f["title"]); best.append(f)
        picks = [(f["title"], f["slug"]) for f in best[:4]]
        print("favourites fell back to top rated:", picks)
    out = []
    for title, slug in picks:
        f = by_title.get(title.lower())
        url = f["img"] if f and f["img"] else (poster_for_slug(slug) if slug else None)
        out.append({"title": title, "poster": poster_b64(url, "mid")})
    return out


def fetch():
    films = read_feed()
    films[0]["poster"] = poster_b64(films[0]["img"], "big")
    for f in films[1:14]:
        f["poster"] = poster_b64(f["img"], "small")
    return films[:14], top4(films)


def demo():
    rows = [("Perfect Blue", "1997", 5, True, "mima my beloved... i will never be normal about this movie", "2026-10-24"),
            ("Paprika", "2006", 4.5, True, "", "2026-10-22"), ("Spirited Away", "2001", 5, True, "", "2026-10-20"),
            ("Lost in Translation", "2003", 4, False, "", "2026-10-18"), ("Millennium Actress", "2001", 4.5, True, "", "2026-10-15"),
            ("Tokyo Godfathers", "2003", 3.5, False, "", "2026-10-11"), ("Kiki's Delivery Service", "1989", 4, True, "", "2026-10-09"),
            ("Chungking Express", "1994", 4.5, True, "", "2026-10-05"), ("Your Name", "2016", 3.5, False, "", "2026-10-02"),
            ("Akira", "1988", 4, False, "", "2026-09-28"), ("Whisper of the Heart", "1995", 5, True, "", "2026-09-25")]
    films = [{"title": t, "year": y, "rating": r, "liked": l, "rewatch": False, "watched": d, "review": rv, "poster": None}
             for t, y, r, l, rv, d in rows]
    top = [{"title": t, "poster": None} for t in ["Perfect Blue", "Paprika", "Whisper of the Heart", "Chungking Express"]]
    return films, top


# ------------------------------------------------------------------ drawing helpers
def cut(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def wrap(s, n, lines):
    words, out, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + len(w) + 1 > n:
            out.append(cur); cur = w
            if len(out) == lines:
                break
        else:
            cur = (cur + " " + w).strip()
    else:
        out.append(cur)
    out = out[:lines]
    if len(" ".join(out)) < len(s.strip()):
        out[-1] = cut(out[-1], n - 1) + "…"
    return out


def nice_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%b %d").lower()
    except ValueError:
        return ""


STAR = "M0 -7L2.1 -2.3 7 -2.2 3.2 1 4.4 6 0 3.3 -4.4 6 -3.2 1 -7 -2.2 -2.1 -2.3Z"


def stars(x, y, rating, s, uid, empty="#ffe0ef", edge="#ffb3d6"):
    out = ""
    for k in range(5):
        fill = 0 if rating is None else max(0, min(1, rating - k))
        out += f'<g transform="translate({x + k * 17 * s:.1f} {y}) scale({s})"><path d="{STAR}" fill="{empty}" stroke="{edge}" stroke-width="1.2" stroke-linejoin="round"/>'
        if fill >= 1:
            out += f'<path d="{STAR}" fill="{HOT}" stroke="#fff" stroke-width="1" stroke-linejoin="round"/>'
        elif fill > 0:
            out += (f'<clipPath id="h{uid}{k}"><rect x="-8" y="-8" width="8" height="16"/></clipPath>'
                    f'<path d="{STAR}" fill="{HOT}" clip-path="url(#h{uid}{k})"/>')
        out += "</g>"
    return out


def poster(x, y, w, h, src, cid, rx=4):
    if src:
        return (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"/></clipPath>'
                f'<image href="{src}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice" clip-path="url(#{cid})"/>')
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="url(#ph)"/>'
            f'<text x="{x + w / 2}" y="{y + h / 2 + w * .14:.1f}" text-anchor="middle" font-size="{w * .4:.1f}" fill="#fff" font-family="{FONT}">✦</text>')


def heart(x, y, s, c, delay=0, cls="pop"):
    return (f'<g transform="translate({x} {y}) scale({s})"><path class="{cls}" style="animation-delay:{delay}s" '
            f'd="M0 4C-6-4-14 2-8 8L0 15 8 8C14 2 6-4 0 4z" fill="{c}" stroke="#fff" stroke-width="1.5"/></g>')


def ribbon(cx, cy, label, c):
    w = len(label) * 7.6 + 34
    x0, x1 = cx - w / 2, cx + w / 2
    return (f'<path d="M{x0 - 16} {cy - 9}h22v18h-22l7-9z" fill="{c}" opacity=".55"/><path d="M{x1 + 16} {cy - 9}h-22v18h22l-7-9z" fill="{c}" opacity=".55"/>'
            f'<rect x="{x0}" y="{cy - 13}" width="{w:.0f}" height="26" rx="6" fill="{c}" stroke="#fff" stroke-width="2.5"/>'
            f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" font-family="{FONT}" font-size="13.5" font-weight="900" fill="#fff">{escape(label)}</text>')


def twinkle(x, y, c, d, s=1):
    return f'<path class="tw" style="animation-delay:{d}s" transform="translate({x} {y}) scale({s})" d="M0-6L1.5-1.5 6 0 1.5 1.5 0 6-1.5 1.5-6 0-1.5-1.5Z" fill="{c}"/>'


# ------------------------------------------------------------------ the card
def render(films, top):
    W, H = 560, 600
    f0 = films[0]

    # --- valance + curtains + marquee
    scallops = "".join(f'<circle cx="{x}" cy="24" r="12" fill="url(#cur)"/>' for x in range(0, W + 12, 22))
    tassels = "".join(f'<circle cx="{x}" cy="38" r="2.6" fill="{YEL}"/>' for x in range(0, W + 12, 22))
    folds = "".join(f'<path d="M{x} 30 Q{x + 6} 120 {x - 4} 196" stroke="#fff" stroke-opacity=".35" stroke-width="2" fill="none"/>' for x in (16, 30))
    curtain = (f'<path d="M0 20H58Q50 120 30 192Q46 222 50 254Q38 266 26 256Q14 266 0 256Z" fill="url(#cur)"/>{folds}'
               f'<path d="M22 186q14 4 22 0" stroke="{YEL}" stroke-width="5" stroke-linecap="round" fill="none"/>'
               f'{heart(33, 180, .8, LAV)}')
    # bulbs in order going clockwise around the sign, so the light chases around one at a time
    xs = list(range(180, 384, 14))
    ring = ([(x, 18) for x in xs] + [(388, 32), (388, 46)] + [(x, 60) for x in reversed(xs)] + [(172, 46), (172, 32)])
    dur = 2.4
    bulbs = "".join(f'<circle cx="{x}" cy="{y}" r="3" fill="#6b5a2e"/>'
                    f'<g class="bulb" style="animation-delay:{i * dur / len(ring):.3f}s"><circle cx="{x}" cy="{y}" r="6" fill="{YEL}" opacity=".35"/>'
                    f'<circle cx="{x}" cy="{y}" r="3.4" fill="#fff6c2"/></g>' for i, (x, y) in enumerate(ring))
    marquee = (f'<rect x="164" y="10" width="232" height="58" rx="14" fill="{INK}" stroke="#fff" stroke-width="3"/>{bulbs}'
               f'<text x="280" y="46" text-anchor="middle" font-family="{FONT}" font-size="18" font-weight="900" fill="#fff" stroke="{HOT}" stroke-width="4" stroke-linejoin="round" paint-order="stroke">gunner\'s cinema</text>')

    # --- the screen: most recent watch
    if f0["review"]:
        quote = wrap("“" + f0["review"] + "”", 38, 2)
    else:
        quote = [["no thoughts just vibes ♡", "absolute cinema ✧", "i'm normal about this ♡", "need to rewatch already ✧", "cinema (◕‿◕)"][sum(map(ord, f0["title"])) % 5]]
    qlines = "".join(f'<text x="186" y="{192 + i * 16}" font-family="{FONT}" font-size="12" font-weight="700" font-style="italic" fill="#ffd6ea">{escape(l)}</text>' for i, l in enumerate(quote))
    when = nice_date(f0["watched"])
    sub = (f"watched {when}" if when else "") + (" · rewatch ↻" if f0["rewatch"] else "")
    liked = heart(328, 154, .8, HOT) if f0["liked"] else ""
    screen = (f'<rect x="62" y="80" width="436" height="160" rx="12" fill="{INK}" stroke="#fff" stroke-width="4"/>'
              f'<rect x="70" y="88" width="420" height="144" rx="8" fill="url(#glow)"/>'
              f'<rect x="80" y="96" width="86" height="128" rx="4" fill="#fff"/>{poster(83, 99, 80, 122, f0.get("poster"), "big")}'
              f'<rect x="184" y="98" width="128" height="22" rx="11" fill="{HOT}"/>'
              f'<text x="248" y="113" text-anchor="middle" font-family="{FONT}" font-size="11.5" font-weight="900" fill="#fff">recently watched ♡</text>'
              f'<text x="186" y="146" font-family="{FONT}" font-size="21" font-weight="900" fill="#fff">{escape(cut(f0["title"], 24))}</text>'
              f'<text x="186" y="167" font-family="{FONT}" font-size="13" font-weight="800" fill="#c9b3ff">{escape(f0["year"])}</text>'
              f'{stars(232, 162, f0["rating"], .95, "m", "#4a3460", "#6d5590")}{liked}'
              f'<text x="482" y="113" text-anchor="end" font-family="{FONT}" font-size="10" font-weight="700" fill="#9d88c0">{escape(sub)}</text>'
              f'{qlines}{twinkle(478, 216, YEL, .2, .9)}{twinkle(464, 200, "#fff", .8, .6)}')

    # --- top 4 trading cards
    rank_c = [YEL, HOT, LAV, BLUE]
    cards = ""
    for i, f in enumerate(top[:4]):
        cx = 100 + i * 120
        x, y = cx - 46, 286
        rot = [-4, 3, -3, 4][i]
        crown = (f'<path d="M{x - 12} {y - 14}l3-10 5 6 4-9 4 9 5-6 3 10z" fill="{YEL}" stroke="#fff" stroke-width="1.5" stroke-linejoin="round"/>' if i == 0 else "")
        cards += (f'<g class="bob" style="animation-delay:-{i * .5:.1f}s"><g transform="rotate({rot} {cx} 356)">'
                  f'<rect x="{x}" y="{y}" width="92" height="140" rx="10" fill="#fff" stroke="{rank_c[i]}" stroke-width="3"/>'
                  f'{poster(x + 8, y + 8, 76, 108, f.get("poster"), f"t{i}")}'
                  f'<text x="{cx}" y="{y + 131}" text-anchor="middle" font-family="{FONT}" font-size="10.5" font-weight="800" fill="{INK}">{escape(cut(f["title"], 14))}</text>'
                  f'{crown}<circle cx="{x}" cy="{y}" r="13" fill="{rank_c[i]}" stroke="#fff" stroke-width="2.5"/>'
                  f'<text x="{x}" y="{y + 5}" text-anchor="middle" font-family="{FONT}" font-size="13" font-weight="900" fill="#fff">{i + 1}</text>'
                  f'</g></g>')
    cards += heart(160, 300, .7, HOT, .2) + heart(400, 420, .7, LAV, .6) + twinkle(282, 432, YEL, .4) + twinkle(526, 300, BLUE, .1) + twinkle(36, 420, HOT, .7)

    # --- history film strip (scrolls forever)
    hist = films[:]
    while len(hist) * 58 < 560:
        hist = hist + films
    n, step = len(hist), 58
    frames = ""
    for rep in range(2):
        for j, f in enumerate(hist):
            fx = 14 + (rep * n + j) * step
            frames += (f'<rect x="{fx}" y="480" width="48" height="66" rx="3" fill="#4a3460"/>'
                       f'{poster(fx + 4, 483, 40, 60, f.get("poster"), f"s{rep}_{j}", 2)}'
                       f'<text x="{fx + 24}" y="566" text-anchor="middle" font-family="{FONT}" font-size="9.5" font-weight="800" fill="{LAV}">{escape(nice_date(f["watched"]))}</text>'
                       f'{stars(fx + 24 - 2 * 17 * .36, 578, f["rating"], .36, f"r{rep}_{j}")}')
            if f["liked"]:
                frames += f'<text x="{fx + 44}" y="489" text-anchor="middle" font-size="10" fill="{HOT}">♥</text>'
    holes = "".join(f'<rect x="{x}" y="{y}" width="8" height="5" rx="1.5" fill="#fff" opacity=".85"/>' for x in range(0, n * step * 2 + 40, 14) for y in (472, 551))
    strip = (f'<g clip-path="url(#inner)"><g class="roll" style="animation-duration:{n * 2.4:.1f}s">'
             f'<rect x="0" y="466" width="{n * step * 2 + 40}" height="94" fill="none"/>'
             f'<rect x="0" y="468" width="{n * step * 2 + 40}" height="90" fill="{INK}"/>{holes}{frames}</g></g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">
<style>
.bob{{animation:bob 2.6s ease-in-out infinite}}@keyframes bob{{50%{{transform:translateY(-4px)}}}}
.pop{{animation:pop 1.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}@keyframes pop{{50%{{transform:scale(1.2)}}}}
.tw{{animation:tw 1.6s ease-in-out infinite}}@keyframes tw{{0%,100%{{opacity:.1}}50%{{opacity:1}}}}
.bulb{{opacity:.08;animation:bulb 2.4s linear infinite}}@keyframes bulb{{0%{{opacity:1}}14%{{opacity:.08}}100%{{opacity:.08}}}}
.roll{{animation:roll linear infinite}}@keyframes roll{{to{{transform:translateX(-{n * step}px)}}}}
</style>
<defs>
<pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="7" cy="7" r="1.1" fill="{LAV}" opacity=".25"/></pattern>
<linearGradient id="ph" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ffb3dd"/><stop offset="1" stop-color="#b89cff"/></linearGradient>
<linearGradient id="cur" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff7cbf"/><stop offset=".5" stop-color="#ffa6d4"/><stop offset="1" stop-color="#ff7cbf"/></linearGradient>
<radialGradient id="glow" cx=".5" cy="0" r="1"><stop offset="0" stop-color="#5b3f78"/><stop offset="1" stop-color="{INK}"/></radialGradient>
<clipPath id="card"><rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26"/></clipPath>
<clipPath id="inner"><rect x="12" y="460" width="{W - 24}" height="130"/></clipPath>
</defs>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="#fbf5ff"/>
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="url(#dots)"/>
<g clip-path="url(#card)">
{curtain}<g transform="translate({W} 0) scale(-1 1)">{curtain}</g>
<rect x="0" y="0" width="{W}" height="24" fill="url(#cur)"/>{scallops}{tassels}
</g>
{screen}
{marquee}
{ribbon(280, 266, "♡ top 4 ♡", LAV)}
{cards}
{ribbon(280, 452, "✧ history ✧", HOT)}
{strip}
<rect x="4" y="4" width="{W - 8}" height="{H - 8}" rx="26" fill="none" stroke="#fff" stroke-width="3"/>
<rect x="10" y="10" width="{W - 20}" height="{H - 20}" rx="21" fill="none" stroke="{LAV}" stroke-width="1.3" stroke-dasharray="4 3"/>
</svg>'''


if __name__ == "__main__":
    try:
        films, top = demo() if "--demo" in sys.argv else fetch()
    except Exception as e:
        # letterboxd hiccup: keep the old card instead of breaking it
        print("couldn't read letterboxd:", e)
        sys.exit(0)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w").write(render(films, top))
    print("wrote", OUT)
