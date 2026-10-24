"""يولّد صوراً حقيقية لأشياء التجارب وكلمات الحروف عبر Gemini، ويزيل الخلفية البيضاء.

    export GEMINI_API_KEY=...      # لا تضعه في أي ملف داخل المستودع
    python3 tools/gen_images.py

الصور تُحفظ في img/<id>.png (شفافة، 192px) وتُضاف إلى nujoom.appcache. الموجود منها لا يُعاد توليده.
"""
import base64
import io
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "img"
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
SIZE = 192

# المعرّف ← وصف الشيء بالإنكليزية
OBJECTS = {
    "key": "a single brass door key", "paperclip": "a single steel paperclip", "scissors": "a pair of metal scissors",
    "bolt": "a single steel hex bolt", "pencil": "a wooden yellow pencil", "balloon": "a red rubber balloon",
    "ruler": "a clear plastic ruler", "leaf": "a single dry autumn leaf", "shirt": "a folded cotton t-shirt",
    "apple": "a red apple", "anchor": "a small iron anchor", "basketball": "an orange basketball",
    "ring": "a gold ring", "lemon": "a yellow lemon", "tennisball": "a yellow tennis ball", "wrench": "a steel wrench",
    "rabbit": "a cute white rabbit sitting", "door": "a wooden front door", "ice": "a few clear ice cubes",
    "camel": "a camel standing", "horse": "a brown horse standing", "sheep": "a fluffy white sheep",
    "bear": "a brown bear", "corn": "a yellow corn cob", "pomegranate": "a red pomegranate",
    "flower": "a pink daisy flower", "fish": "a colorful goldfish", "sun": "the bright yellow sun, simple",
    "rocket": "a toy space rocket", "frog": "a green frog sitting", "airplane": "a white passenger airplane",
    "envelope": "a closed paper envelope", "grapes": "a bunch of purple grapes", "cloud": "a fluffy white cloud on light blue circle",
    "elephant": "a grey elephant", "moon": "the full moon", "book": "a closed hardcover children's book",
    "banana": "a yellow banana", "bee": "a honey bee", "gift": "a wrapped gift box with a red ribbon",
    "rose": "a red rose", "hand": "an open child's hand, palm facing camera",
}


def prompt(desc):
    return ("A realistic, clear, well-lit product photo of %s, centered, whole object fully visible, "
            "isolated on a pure white background, no text, no shadow, friendly for young children." % desc)


def call(desc):
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt(desc)}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}},
    }).encode()
    req = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % MODEL, data=body,
        headers={"Content-Type": "application/json", "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.load(r)
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return base64.b64decode(part["inlineData"]["data"])
    raise RuntimeError("no image in response")


def cutout(raw):
    """يحوّل الخلفية البيضاء المتصلة بالحواف إلى شفافة ثم يقصّ ويصغّر."""
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((512, 512))
    w, h = im.size
    marker = (255, 0, 255)
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)):
        if min(im.getpixel(seed)) > 225:
            ImageDraw.floodfill(im, seed, marker, thresh=40)
    rgba = im.convert("RGBA")
    px = rgba.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][:3] == marker:
                px[x, y] = (255, 255, 255, 0)
    box = rgba.getbbox() or (0, 0, w, h)
    rgba = rgba.crop(box)
    side = max(rgba.size)
    sq = Image.new("RGBA", (side, side), (255, 255, 255, 0))
    sq.paste(rgba, ((side - rgba.size[0]) // 2, (side - rgba.size[1]) // 2))
    return sq.resize((SIZE, SIZE), Image.LANCZOS)


def one(item):
    name, desc = item
    path = OUT / (name + ".png")
    if path.exists():
        return name, "skip"
    for attempt in range(3):
        try:
            cutout(call(desc)).save(path, optimize=True)
            return name, "ok"
        except Exception as e:  # noqa: BLE001 - نعيد المحاولة لأي خطأ شبكة أو رد فارغ
            err = e
    return name, "FAILED: %s" % err


def update_manifest():
    path = ROOT / "nujoom.appcache"
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if not l.startswith("img/")]
    i = lines.index("NETWORK:")
    imgs = sorted("img/" + p.name for p in OUT.glob("*.png"))
    lines[i:i] = imgs + [""]
    text = "\n".join(lines).replace("\n\n\n", "\n\n") + "\n"
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("ضع المفتاح في GEMINI_API_KEY أولاً")
    OUT.mkdir(exist_ok=True)
    with ThreadPoolExecutor(4) as ex:
        for name, status in ex.map(one, OBJECTS.items()):
            print(name, status, flush=True)
    update_manifest()
    print("JS list:", json.dumps(sorted(p.stem for p in OUT.glob("*.png"))))
