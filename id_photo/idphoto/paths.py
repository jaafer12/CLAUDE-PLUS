"""مسارات الموارد والإعدادات، سواء شُغّل البرنامج من الكود أو من النسخة المثبّتة."""

import os
import sys
from pathlib import Path


def resource_dir() -> Path:
    """مجلد حزمة idphoto (داخل _internal في النسخة المجمّعة بـ PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "idphoto"
    return Path(__file__).resolve().parent


def models_dir() -> Path:
    return resource_dir() / "models"


def data_dir() -> Path:
    """مجلد الإعدادات الخاص بالمستخدم."""
    base = os.environ.get("APPDATA") or os.path.join(Path.home(), ".config")
    path = Path(base) / "IDPhoto"
    path.mkdir(parents=True, exist_ok=True)
    return path


def setup_model_env() -> None:
    """يجعل rembg يقرأ نموذج القصّ المرفق مع البرنامج بدلاً من تنزيله.

    rembg يبحث في ‎$U2NET_HOME/models/<name>/<name>.onnx‎ ثم في ‎$U2NET_HOME/<name>.onnx‎.
    إن لم يكن النموذج مرفقاً (تشغيل من الكود) يُنزَّل مرة واحدة إلى ‎~/.u2net‎.
    """
    bundled = models_dir()
    if (bundled / "u2net_human_seg.onnx").exists():
        os.environ.setdefault("U2NET_HOME", str(bundled))
