"""ينزّل صورة حقيقية برخصة حرة من ويكيميديا كومنز لكل شيء في tools/photos.json.

كل سطر:  "المعرّف": "w:<مقال ويكيبيديا>"  (الصورة الرئيسية للمقال)
          أو        "f:<اسم ملف في كومنز>"  (ملف محدّد بدل صورة مقال غير مناسبة)

تُحفظ الصور مربعة 240px بصيغة JPEG (Safari 9 لا يدعم WebP) في img/<id>.jpg،
ويُكتب js/photos.js بأسماء المصوّرين والرخص، وتُضاف الصور إلى nujoom.appcache.
يعمل في GitHub Actions (حاوية Claude لا تصل إلى ويكيميديا)؛ يحتاج Pillow.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://en.wikipedia.org/w/api.php"
UA = "NujoomKidsBot/1.0 (https://github.com/jaafer12/CLAUDE-PLUS; offline learning system for children)"
OUT = os.path.join(ROOT, "img")
SIZE = 240
ALLOWED = re.compile(r"(cc0|public domain|^pd|cc[ -]by(?![^0-9]*n[cd])|^fal$|free art|no restrictions|copyrighted free use|^attribution$)", re.I)


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
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def square(data):
    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    else:
        im = im.convert("RGB")
    w, h = im.size
    s = min(w, h)
    im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
    return im.resize((SIZE, SIZE), Image.LANCZOS)


def write_js(credits):
    with open(os.path.join(ROOT, "js", "photos.js"), "w", encoding="utf-8") as f:
        f.write("/* يُولَّد تلقائياً بواسطة tools/fetch_photos.py — لا تعدّله يدوياً. */\n")
        f.write("OS.photos = " + json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True) + ";\n")


def write_manifest():
    path = os.path.join(ROOT, "nujoom.appcache")
    lines = [l for l in open(path, encoding="utf-8").read().splitlines() if not l.startswith("img/")]
    i = lines.index("NETWORK:")
    imgs = sorted("img/" + n for n in os.listdir(OUT) if n.endswith(".jpg"))
    while i > 0 and lines[i - 1] == "":
        i -= 1
        lines.pop(i)
    lines[i:i] = imgs + [""] if imgs else [""]
    open(path, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    mapping = json.load(open(os.path.join(ROOT, "tools", "photos.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    cpath = os.path.join(OUT, "credits.json")
    credits = json.load(open(cpath, encoding="utf-8")) if os.path.exists(cpath) else {}
    problems = []

    for pid in list(credits):
        if not mapping.get(pid):
            p = os.path.join(OUT, pid + ".jpg")
            if os.path.exists(p):
                os.remove(p)
            del credits[pid]

    for pid, src in mapping.items():
        path = os.path.join(OUT, pid + ".jpg")
        old = credits.get(pid)
        if old and old.get("src") == src and os.path.exists(path):
            continue
        try:
            if src.startswith("w:"):
                r = api({"action": "query", "titles": src[2:], "prop": "pageimages",
                         "piprop": "name", "pilicense": "free", "redirects": 1})
                file = r["query"]["pages"][0].get("pageimage")
                if not file:
                    problems.append("%s: no free lead image on '%s'" % (pid, src[2:]))
                    continue
            else:
                file = src[2:]
            r = api({"action": "query", "titles": "File:" + file, "prop": "imageinfo",
                     "iiprop": "url|extmetadata", "iiurlwidth": 640})
            info = r["query"]["pages"][0]["imageinfo"][0]
            meta = info.get("extmetadata", {})
            lic = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
            if not ALLOWED.search(lic):
                problems.append("%s: licence not allowed (%s) for %s" % (pid, lic, file))
                continue
            square(download(info.get("thumburl") or info["url"])).save(path, "JPEG", quality=80, optimize=True, progressive=False)
            credits[pid] = {
                "src": src, "file": file, "license": lic, "url": info.get("descriptionurl", ""),
                "author": strip_html(meta.get("Artist", {}).get("value", ""))[:120] or "Unknown",
            }
            print("ok   %-12s %s  [%s]" % (pid, file, lic))
        except Exception as e:  # نكمل ونبلّغ في النهاية
            problems.append("%s: %s" % (pid, e))
        time.sleep(0.25)

    json.dump(dict(sorted(credits.items())), open(cpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    write_js(credits)
    write_manifest()
    print("\n%d photos" % len(credits))
    if problems:
        print("Problems:\n  " + "\n  ".join(problems))
    with open(os.path.join(OUT, "problems.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(problems) + "\n")


if __name__ == "__main__":
    sys.exit(main())
