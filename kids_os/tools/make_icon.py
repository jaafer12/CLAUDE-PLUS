"""يرسم أيقونة «نجوم» (icon.png) للشاشة الرئيسية في الآيباد."""
import math
from pathlib import Path
from PIL import Image, ImageDraw

S = 4  # رسم بدقة أعلى ثم تصغير لحواف ناعمة
size = 180 * S
img = Image.new("RGB", (size, size), "#1a237e")
d = ImageDraw.Draw(img)
for y in range(size):  # تدرّج سماوي
    t = y / size
    d.line([(0, y), (size, y)], fill=(int(26 + 40 * t), int(35 + 120 * t), int(126 + 110 * t)))
cx, cy, r = size / 2, size / 2 + 6 * S, 66 * S
pts = []
for i in range(10):
    a = -math.pi / 2 + i * math.pi / 5
    rr = r if i % 2 == 0 else r * 0.45
    pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
d.polygon(pts, fill="#ffd54f")
for dx, dy in ((-18, -8), (18, -8)):
    d.ellipse([cx + dx * S - 6 * S, cy + dy * S - 6 * S, cx + dx * S + 6 * S, cy + dy * S + 6 * S], fill="#263238")
d.arc([cx - 16 * S, cy - 4 * S, cx + 16 * S, cy + 22 * S], 20, 160, fill="#263238", width=4 * S)
out = Path(__file__).resolve().parent.parent / "icon.png"
img.resize((180, 180), Image.LANCZOS).save(out, optimize=True)
print("wrote", out)
