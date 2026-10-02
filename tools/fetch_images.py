"""Download a free-licensed photo for each word in tools/images.json.

Each entry maps a word id to a source:
  "w:<Wikipedia article>"  -> the article's lead image (free licences only)
  "f:<Commons file name>"  -> that exact file, used to override a poor lead image
The photos are saved as web/img/<slug>.webp, and web/img/credits.json records
author, licence and source page for each one (shown on the app's credits page).
Runs in GitHub Actions; needs Pillow.
"""
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

from PIL import Image

API = "https://en.wikipedia.org/w/api.php"
UA = "KalimaKalimaBot/1.0 (https://github.com/jaafer12/CLAUDE-PLUS; educational app for dyslexic learners)"
OUT = "web/img"
ALLOWED = re.compile(r"(cc0|public domain|^pd|cc[ -]by(?![^0-9]*n[cd]))", re.I)


def slug(word_id):
    return re.sub(r"[^a-z0-9]+", "-", word_id.lower()).strip("-")


def api(params):
    q = urllib.parse.urlencode({**params, "format": "json", "formatversion": 2})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def strip_html(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def main():
    mapping = json.load(open("tools/images.json", encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    cpath = os.path.join(OUT, "credits.json")
    credits = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
    problems = []

    for wid in list(credits):
        if not mapping.get(wid):
            path = os.path.join(OUT, slug(wid) + ".webp")
            if os.path.exists(path):
                os.remove(path)
            del credits[wid]

    for wid, src in mapping.items():
        if not src:
            continue
        path = os.path.join(OUT, slug(wid) + ".webp")
        old = credits.get(wid)
        if old and old.get("src") == src and os.path.exists(path):
            continue
        try:
            if src.startswith("w:"):
                r = api({"action": "query", "titles": src[2:], "prop": "pageimages",
                         "piprop": "name", "pilicense": "free", "redirects": 1})
                page = r["query"]["pages"][0]
                file = page.get("pageimage")
                if not file:
                    problems.append(f"{wid}: no free lead image on '{src[2:]}'")
                    continue
            else:
                file = src[2:]
            r = api({"action": "query", "titles": "File:" + file, "prop": "imageinfo",
                     "iiprop": "url|extmetadata", "iiurlwidth": 640})
            info = r["query"]["pages"][0]["imageinfo"][0]
            meta = info.get("extmetadata", {})
            lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
            if not ALLOWED.search(lic):
                problems.append(f"{wid}: licence not allowed ({lic}) for {file}")
                continue
            data = download(info.get("thumburl") or info["url"])
            im = Image.open(io.BytesIO(data))
            if im.mode in ("RGBA", "LA", "P"):
                im = im.convert("RGBA")
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im, mask=im.split()[-1])
                im = bg
            else:
                im = im.convert("RGB")
            im.thumbnail((560, 560))
            im.save(path, "WEBP", quality=74, method=6)
            credits[wid] = {
                "src": src,
                "file": file,
                "author": strip_html(meta.get("Artist", {}).get("value", ""))[:140] or "Unknown",
                "license": lic,
                "url": info.get("descriptionurl", ""),
            }
            print(f"ok   {wid:14} {file}  [{lic}]")
        except Exception as e:  # keep going; report at the end
            problems.append(f"{wid}: {e}")
        time.sleep(0.25)

    json.dump(dict(sorted(credits.items())), open(cpath, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"\n{len(credits)} photos")
    if problems:
        print("Problems:\n  " + "\n  ".join(problems))
    with open(os.path.join(OUT, "problems.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(problems) + "\n")


if __name__ == "__main__":
    sys.exit(main())
