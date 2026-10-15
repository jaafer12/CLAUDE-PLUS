"""إعدادات المستخدم المحفوظة في ‎%APPDATA%\\PCDoctor\\settings.json‎، وسجلّ الفحوص."""

import json
from dataclasses import asdict, dataclass, fields

from . import paths


@dataclass
class Settings:
    last_seen_version: str = ""  # آخر إصدار عُرضت له نافذة «ما الجديد»
    check_updates: bool = True
    last_update_check: float = 0.0
    skipped_version: str = ""
    theme: str = "dark"  # dark / light / system
    restore_point: bool = True  # إنشاء نقطة استعادة قبل إصلاحات النظام
    scan_on_start: bool = False


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


# ---------------------------------------------------------------- سجلّ الفحوص

HISTORY_LIMIT = 30


def _history_file():
    return paths.data_dir() / "history.json"


def load_history() -> list[dict]:
    try:
        data = json.loads(_history_file().read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def save_history(items: list[dict]) -> None:
    try:
        _history_file().write_text(json.dumps(items[:HISTORY_LIMIT], ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    except OSError:
        pass


def add_history(entry: dict) -> None:
    save_history([entry] + load_history())
