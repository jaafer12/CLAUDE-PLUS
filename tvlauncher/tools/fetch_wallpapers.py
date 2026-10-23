"""Download featured nature and city photos from Wikimedia Commons for the TV backgrounds.

Writes <out>/day/NN.webp and <out>/night/NN.webp (1920x1080) plus <out>/credits.json,
which maps each file to "author · licence" (shown on screen). Runs in GitHub Actions
before the APK build; needs Pillow. If Commons is unreachable the app simply falls back
to its drawn landscape, so this script never fails the build.
"""
import html
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
UA = "JaaferTV/1.0 (https://github.com/jaafer12/CLAUDE-PLUS; personal TV launcher backgrounds)"
ALLOWED = re.compile(r"(cc0|public domain|^pd|cc[ -]by(?![^0-9]*n[cd])|^fal$|free art|no restrictions|copyrighted free use|^attribution$)", re.I)
FEATURED = 'incategory:"Featured pictures on Wikimedia Commons" filetype:bitmap'

QUERIES = {
    "day": [
        ("mountain lake landscape", 2),
        ("sea coast cliffs", 2),
        ("forest valley autumn", 2),
        ("city skyline", 2),
        ("desert dunes", 1),
        ("waterfall", 1),
    ],
    "night": [
        ("city skyline night", 3),
        ("milky way night sky", 2),
        ("aurora borealis", 1),
        ("blue hour city", 2),
    ],
}


def get_json(params):
    params = dict(params, format="json", formatversion="2")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download(url):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # rate limits and transient errors: back off and retry
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(5 * (attempt + 1))
    return None


def plain(text):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text or ""))).strip()


def candidates(query):
    data = get_json({
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{FEATURED} {query}",
        "gsrnamespace": "6",
        "gsrlimit": "25",
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "1920",
        "iiextmetadatafilter": "Artist|LicenseShortName",
    })
    pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
    for page in pages:
        info = (page.get("imageinfo") or [None])[0]
        if not info or info.get("mime") != "image/jpeg":
            continue
        w, h = info.get("width", 0), info.get("height", 1)
        if w < 2400 or not 1.4 <= w / h <= 2.0:
            continue
        meta = info.get("extmetadata", {})
        licence = plain(meta.get("LicenseShortName", {}).get("value"))
        if not ALLOWED.search(licence):
            continue
        artist = plain(meta.get("Artist", {}).get("value"))[:60] or "Wikimedia Commons"
        yield page["title"], info.get("thumburl") or info["url"], f"{artist} · {licence}"


def to_wallpaper(data):
    img = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = img.size
    target = 16 / 9
    if w / h > target:
        nw = int(h * target)
        img = img.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / target)
        img = img.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return img.resize((1920, 1080), Image.LANCZOS)


def main(out):
    credits = {}
    seen = set()
    for part, queries in QUERIES.items():
        os.makedirs(os.path.join(out, part), exist_ok=True)
        n = 0
        for query, want in queries:
            got = 0
            try:
                found = list(candidates(query))
            except Exception as e:
                print(f"search failed for {query!r}: {e}")
                continue
            for title, url, credit in found:
                if got >= want or title in seen:
                    continue
                data = download(url)
                if not data:
                    continue
                try:
                    img = to_wallpaper(data)
                except Exception as e:
                    print(f"  skip {title}: {e}")
                    continue
                n += 1
                got += 1
                seen.add(title)
                name = f"{part}/{n:02d}.webp"
                img.save(os.path.join(out, name), "WEBP", quality=80, method=6)
                credits[name] = credit
                print(f"{name}  {title}  ({credit})")
                time.sleep(1)
    with open(os.path.join(out, "credits.json"), "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=1)
    print(f"{len(credits)} wallpapers")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "app/src/main/assets/wallpapers")
