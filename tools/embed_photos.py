"""Copy photo credits from web/img/credits.json into web/app.html (the PHOTOS table).

Run after the "Fetch word photos" workflow has committed new photos:
    python3 tools/embed_photos.py
"""
import json
import os
import re

credits = json.load(open("web/img/credits.json", encoding="utf-8"))
table = {
    wid: [c["author"], c["license"], c["url"]]
    for wid, c in sorted(credits.items())
    if os.path.exists(os.path.join("web/img", re.sub(r"[^a-z0-9]+", "-", wid.lower()).strip("-") + ".webp"))
}
path = "web/app.html"
html = open(path, encoding="utf-8").read()
body = json.dumps(table, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html, n = re.subn(r"/\*PHOTOS\*/.*?/\*END\*/", lambda m: "/*PHOTOS*/" + body + "/*END*/", html, flags=re.S)
assert n == 1, "PHOTOS marker not found"
open(path, "w", encoding="utf-8").write(html)
print(f"embedded {len(table)} photos")
