"""إعدادات المستخدم المحفوظة في ‎%APPDATA%\\IDPhoto\\settings.json‎."""

import json
from dataclasses import asdict, dataclass, fields

from . import paths


@dataclass
class Settings:
    last_seen_version: str = ""  # آخر إصدار عُرضت له نافذة «ما الجديد»
    check_updates: bool = True
    last_update_check: float = 0.0
    skipped_version: str = ""
    preset: str = "iraq_passport"
    remove_yellow: bool = True
    even_lighting: bool = True
    straighten: bool = True
    sharpen: bool = True
    last_dir: str = ""


def _file():
    return paths.data_dir() / "settings.json"


def load() -> Settings:
    try:
        data = json.loads(_file().read_text(encoding="utf-8"))
        known = {f.name for f in fields(Settings)}
        return Settings(**{k: v for k, v in data.items() if k in known})
    except (OSError, ValueError, TypeError):
        return Settings()


def save(s: Settings) -> None:
    try:
        _file().write_text(json.dumps(asdict(s), ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
