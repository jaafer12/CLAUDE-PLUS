"""يبني البرنامج وملف التثبيت.

    python tools/build.py

الخطوات: إنشاء الأيقونة ← PyInstaller ← Inno Setup (على ويندوز).
الناتج: dist/PCDoctor-<الإصدار>-Setup.exe و dist/release_notes.md
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "pcdoctor"
BUILD = ROOT / "build"
DIST = ROOT / "dist"


def version() -> str:
    return re.search(r'__version__ = "([^"]+)"', (PKG / "version.py").read_text(encoding="utf-8")).group(1)


def make_icon() -> Path:
    """أيقونة: درع أزرق فيه نبضة قلب بيضاء."""
    from PIL import Image, ImageDraw

    s = 1024  # نرسم كبيراً ثم نصغّر لحواف ناعمة
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((32, 32, s - 32, s - 32), radius=220, fill=(37, 99, 235, 255))
    shield = [(512, 150), (820, 260), (800, 560), (512, 880), (224, 560), (204, 260)]
    d.polygon(shield, fill=(255, 255, 255, 255))
    inner = [(512, 215), (760, 302), (744, 548), (512, 805), (280, 548), (264, 302)]
    d.polygon(inner, fill=(59, 130, 246, 255))
    pulse = [(270, 520), (420, 520), (470, 400), (545, 660), (600, 470), (640, 520), (754, 520)]
    d.line(pulse, fill=(255, 255, 255, 255), width=56, joint="curve")
    for x, y in (pulse[0], pulse[-1]):
        d.ellipse((x - 28, y - 28, x + 28, y + 28), fill=(255, 255, 255, 255))
    im = im.resize((256, 256), Image.LANCZOS)
    BUILD.mkdir(exist_ok=True)
    out = BUILD / "app.ico"
    im.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    im.save(BUILD / "app.png")
    return out


def version_file(ver: str) -> Path:
    nums = tuple(int(x) for x in ver.split(".")) + (0,)
    text = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={nums}, prodvers={nums}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('FileDescription', 'PCDoctor - PC checkup and repair'),
    StringStruct('FileVersion', '{ver}'),
    StringStruct('ProductName', 'PCDoctor'),
    StringStruct('ProductVersion', '{ver}'),
    StringStruct('OriginalFilename', 'PCDoctor.exe')])]),
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
    lines += ["", "### التثبيت", f"نزّل `PCDoctor-{ver}-Setup.exe` من الأسفل وشغّله. "
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
            "--name", "PCDoctor", "--icon", str(icon), "--version-file", str(vfile),
            "--distpath", str(DIST), "--workpath", str(BUILD / "pyi"), "--specpath", str(BUILD),
            "--collect-data", "customtkinter",
            "--add-data", f"{PKG / 'changelog.json'}{sep}pcdoctor",
            "--add-data", f"{PKG / 'app.ico'}{sep}pcdoctor",
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
    print("building PCDoctor", ver)
    release_notes(ver)
    icon = make_icon()
    if "--icon-only" in sys.argv:
        return
    pyinstaller(icon, version_file(ver))
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup not found; skipped installer (dist/PCDoctor contains the app).")
        return
    subprocess.check_call([iscc, f"/DAppVersion={ver}", f"/DSourceDir={DIST / 'PCDoctor'}",
                           f"/DIconFile={icon}", f"/O{DIST}", str(ROOT / "installer" / "PCDoctor.iss")])
    print("installer:", DIST / f"PCDoctor-{ver}-Setup.exe")


if __name__ == "__main__":
    main()
