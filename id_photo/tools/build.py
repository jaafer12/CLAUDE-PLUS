"""يبني البرنامج وملف التثبيت.

    python tools/build.py

الخطوات: تنزيل نموذج إزالة الخلفية ← إنشاء الأيقونة ← PyInstaller ← Inno Setup (على ويندوز).
الناتج: dist/IDPhoto-<الإصدار>-Setup.exe و dist/release_notes.md
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "idphoto"
BUILD = ROOT / "build"
DIST = ROOT / "dist"

sys.path.insert(0, str(ROOT))
from idphoto.processor import SEG_MODEL_MD5, SEG_MODEL_NAME, SEG_MODEL_URL  # noqa: E402


def version() -> str:
    return re.search(r'__version__ = "([^"]+)"', (PKG / "version.py").read_text(encoding="utf-8")).group(1)


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch_model() -> None:
    dest = PKG / "models" / SEG_MODEL_NAME
    if dest.exists() and md5(dest) == SEG_MODEL_MD5:
        return
    print("downloading", SEG_MODEL_URL)
    urllib.request.urlretrieve(SEG_MODEL_URL, dest)
    if md5(dest) != SEG_MODEL_MD5:
        sys.exit("model checksum mismatch")


def make_icon() -> Path:
    """أيقونة بسيطة: صورة شخصية بخلفية بيضاء داخل إطار أزرق."""
    from PIL import Image, ImageDraw

    size = 256
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8, 8, 248, 248), radius=44, fill=(28, 100, 180, 255))
    d.rounded_rectangle((52, 30, 204, 226), radius=10, fill=(255, 255, 255, 255))
    d.ellipse((96, 62, 160, 134), fill=(60, 70, 90, 255))  # الرأس
    d.pieslice((70, 140, 186, 270), 180, 360, fill=(60, 70, 90, 255))  # الكتفان
    d.rectangle((52, 205, 204, 226), fill=(255, 255, 255, 255))
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "app.ico"
    im.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return out


def version_file(ver: str) -> Path:
    nums = tuple(int(x) for x in ver.split(".")) + (0,)
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'IDPhoto - official ID photo maker'),
    StringStruct('FileVersion', '{ver}'),
    StringStruct('ProductName', 'IDPhoto'),
    StringStruct('ProductVersion', '{ver}'),
    StringStruct('OriginalFilename', 'IDPhoto.exe')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])]
)
"""
    path = BUILD / "version_info.txt"
    path.write_text(text, encoding="utf-8")
    return path


def release_notes(ver: str) -> Path:
    entries = json.loads((PKG / "changelog.json").read_text(encoding="utf-8"))
    entry = next((e for e in entries if e["version"] == ver), None)
    if entry is None:
        sys.exit(f"changelog.json has no entry for {ver}; run tools/bump_version.py")
    lines = [f"## ما الجديد في الإصدار {ver}", ""] + [f"- {n}" for n in entry["notes"]]
    lines += ["", "### التثبيت", f"نزّل `IDPhoto-{ver}-Setup.exe` من الأسفل وشغّله. "
              "البرنامج يتحقق من التحديثات تلقائياً بعد ذلك."]
    DIST.mkdir(exist_ok=True)
    path = DIST / "release_notes.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def pyinstaller(icon: Path, vfile: Path) -> None:
    sep = os.pathsep
    shutil.copy(icon, PKG / "app.ico")
    try:
        subprocess.check_call([
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
            "--name", "IDPhoto", "--icon", str(icon), "--version-file", str(vfile),
            "--distpath", str(DIST), "--workpath", str(BUILD / "pyi"), "--specpath", str(BUILD),
            "--hidden-import", "PIL._tkinter_finder",
            "--add-data", f"{PKG / 'changelog.json'}{sep}idphoto",
            "--add-data", f"{PKG / 'app.ico'}{sep}idphoto",
            "--add-data", f"{PKG / 'models'}{sep}idphoto/models",
            str(ROOT / "main.py"),
        ], cwd=ROOT)
    finally:
        (PKG / "app.ico").unlink(missing_ok=True)


def find_iscc() -> str | None:
    for c in (shutil.which("iscc"), r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
              r"C:\Program Files\Inno Setup 6\ISCC.exe"):
        if c and Path(c).exists():
            return c
    return None


def main() -> None:
    ver = version()
    print("building IDPhoto", ver)
    release_notes(ver)
    fetch_model()
    icon = make_icon()
    pyinstaller(icon, version_file(ver))
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup not found; skipped installer (dist/IDPhoto contains the app).")
        return
    subprocess.check_call([iscc, f"/DAppVersion={ver}", f"/DSourceDir={DIST / 'IDPhoto'}",
                           f"/DIconFile={icon}", f"/O{DIST}", str(ROOT / "installer" / "IDPhoto.iss")])
    print("installer:", DIST / f"IDPhoto-{ver}-Setup.exe")


if __name__ == "__main__":
    main()
