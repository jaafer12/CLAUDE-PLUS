"""يرفع رقم الإصدار ويضيف ملاحظات «ما الجديد».

    python tools/bump_version.py patch "إصلاح ..." "تحسين ..."
    python tools/bump_version.py minor "ميزة جديدة ..."
    python tools/bump_version.py major "..."

بعد الدفع إلى GitHub يبني سير العمل ملف التثبيت الجديد وينشره،
فيظهر التحديث للمستخدمين ثم تظهر لهم نافذة «ما الجديد» بهذه الملاحظات.
"""

import datetime
import json
import re
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "idphoto"
VERSION_FILE = PKG / "version.py"
CHANGELOG = PKG / "changelog.json"


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("major", "minor", "patch"):
        sys.exit(__doc__)
    part, notes = sys.argv[1], sys.argv[2:]

    text = VERSION_FILE.read_text(encoding="utf-8")
    old = re.search(r'__version__ = "(\d+)\.(\d+)\.(\d+)"', text)
    major, minor, patch = (int(x) for x in old.groups())
    if part == "major":
        major, minor, patch = major + 1, 0, 0
    elif part == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    new = f"{major}.{minor}.{patch}"
    VERSION_FILE.write_text(text.replace(old.group(0), f'__version__ = "{new}"'), encoding="utf-8")

    entries = json.loads(CHANGELOG.read_text(encoding="utf-8"))
    entries.insert(0, {"version": new, "date": datetime.date.today().isoformat(), "notes": notes})
    CHANGELOG.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{'.'.join(old.groups())} -> {new}")


if __name__ == "__main__":
    main()
