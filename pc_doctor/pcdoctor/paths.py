"""مسارات الموارد والإعدادات، سواء شُغّل البرنامج من الكود أو من النسخة المثبّتة."""

import os
import sys
from pathlib import Path


def resource_dir() -> Path:
    """مجلد حزمة pcdoctor (داخل _internal في النسخة المجمّعة بـ PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "pcdoctor"
    return Path(__file__).resolve().parent


def data_dir() -> Path:
    """مجلد الإعدادات وسجلّ الفحوص الخاص بالمستخدم."""
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".config")
    path = Path(base) / "PCDoctor"
    path.mkdir(parents=True, exist_ok=True)
    return path
