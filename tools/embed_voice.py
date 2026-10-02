"""Copy the voice clip index (web/audio/voice.json) into web/app.html (the VOICE table).

Run after tools/gen_voice.py:
    python3 tools/embed_voice.py
"""
import json
import os
import re

index = json.load(open("web/audio/voice.json", encoding="utf-8")) if os.path.exists("web/audio/voice.json") else {}
table = {t: [v["clip"], v["dur"]] for t, v in index.items() if os.path.exists(f"web/audio/{v['clip']}.mp3")}
path = "web/app.html"
html = open(path, encoding="utf-8").read()
body = json.dumps(table, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html, n = re.subn(r"/\*VOICE\*/.*?/\*END\*/", lambda m: "/*VOICE*/" + body + "/*END*/", html, flags=re.S)
assert n == 1, "VOICE marker not found"
open(path, "w", encoding="utf-8").write(html)
print(f"embedded {len(table)} voice clips")
