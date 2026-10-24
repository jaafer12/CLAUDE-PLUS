"""يبني نظام «نجوم» في ملف واحد مستقل: dist/index.html

    python3 tools/build.py

1. يولّد js/quran.js من tools/data/quran_short.json (النص كما هو من المصدر، بلا تعديل).
2. يضع كل شيء داخل index.html نفسه: التنسيق، الخط، الأكواد، وكل الصور (base64)،
   فلا تضيع أي صورة على الآيباد ويعمل النظام بلا إنترنت من ملف واحد.
3. يكتب dist/nujoom.appcache ببصمة المحتوى، وينسخ icon.png.
"""
import base64
import hashlib
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")


def read(rel, mode="r"):
    with open(os.path.join(ROOT, rel), mode, **({} if "b" in mode else {"encoding": "utf-8"})) as f:
        return f.read()


def make_quran():
    data = json.loads(read("tools/data/quran_short.json"))
    order = sorted(int(n) for n in data)
    js = ("/* يُولَّد تلقائياً بواسطة tools/build.py من tools/data/quran_short.json — لا تعدّله يدوياً.\n"
          "   النص العثماني (حفص) من موسوعة القرآن الكريم quranenc.com، رخصة CC BY-SA 4.0. */\n"
          "OS.QURAN = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n"
          "OS.QURAN_ORDER = " + json.dumps(order) + ";\n")
    with open(os.path.join(ROOT, "js", "quran.js"), "w", encoding="utf-8") as f:
        f.write(js)


def data_uri(rel, mime):
    return "data:%s;base64,%s" % (mime, base64.b64encode(read(rel, "rb")).decode("ascii"))


def photo_data():
    """يرجع سطر JS يضع كل الصور المذكورة في js/photos.js داخل الملف."""
    m = re.search(r"OS\.photos = (\{.*\});", read("js/photos.js"), re.S)
    ids = sorted(json.loads(m.group(1)).keys()) if m else []
    out = {}
    for pid in ids:
        rel = "img/%s.jpg" % pid
        if os.path.exists(os.path.join(ROOT, rel)):
            out[pid] = data_uri(rel, "image/jpeg")
    return "OS.photoData = " + json.dumps(out) + ";\n", len(out)


def bundle():
    html = read("index.html")
    css = read("css/os.css").replace('url("../fonts/amiri-quran.woff")',
                                     'url("%s")' % data_uri("fonts/amiri-quran.woff", "application/font-woff"))
    html = html.replace('<link rel="stylesheet" href="css/os.css">', "<style>\n" + css + "\n</style>")

    photos_js, n_photos = photo_data()

    def inline(m):
        src = m.group(1)
        code = read(src)
        if src == "js/photos.js":
            code += photos_js
        return "<script>\n" + code.replace("</script", "<\\/script") + "\n</script>"

    html = re.sub(r'<script src="([^"]+)"></script>', inline, html)
    os.makedirs(DIST, exist_ok=True)
    with open(os.path.join(DIST, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    shutil.copy(os.path.join(ROOT, "icon.png"), os.path.join(DIST, "icon.png"))
    digest = hashlib.sha1(html.encode("utf-8") + read("icon.png", "rb")).hexdigest()[:12]
    with open(os.path.join(DIST, "nujoom.appcache"), "w", encoding="utf-8") as f:
        f.write("CACHE MANIFEST\n# version: %s\n\nindex.html\nicon.png\n\nNETWORK:\n*\n" % digest)
    print("dist/index.html: %d KB, %d photos inside" % (len(html.encode("utf-8")) // 1024, n_photos))


if __name__ == "__main__":
    make_quran()
    bundle()
