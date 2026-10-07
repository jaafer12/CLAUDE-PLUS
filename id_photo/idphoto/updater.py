"""التحقق من التحديثات عبر إصدارات GitHub، وسجلّ «ما الجديد»."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import paths
from .version import GITHUB_REPO, RELEASE_TAG_PREFIX, __version__

API = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=30"
USER_AGENT = f"IDPhoto/{__version__}"


def parse_version(v: str) -> tuple[int, ...]:
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums[:3]) + (0,) * (3 - len(nums[:3]))


# ---------------------------------------------------------------- ما الجديد

def changelog() -> list[dict]:
    path = paths.resource_dir() / "changelog.json"
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return sorted(entries, key=lambda e: parse_version(e["version"]), reverse=True)


def entries_since(last_seen: str) -> list[dict]:
    """ملاحظات كل إصدار أحدث من آخر إصدار رآه المستخدم (حتى الإصدار الحالي)."""
    current = parse_version(__version__)
    seen = parse_version(last_seen) if last_seen else None
    out = []
    for e in changelog():
        v = parse_version(e["version"])
        if v > current:
            continue
        if seen is None:  # تثبيت جديد: نعرض الإصدار الحالي فقط
            return [e] if v == current else []
        if v > seen:
            out.append(e)
    return out


# ---------------------------------------------------------------- التحديث

@dataclass
class Update:
    version: str
    notes: str
    url: str  # رابط ملف التثبيت
    size: int
    page: str


def check(timeout: float = 10) -> Optional[Update]:
    """يرجع آخر تحديث متاح أحدث من الإصدار الحالي، أو None."""
    req = urllib.request.Request(API, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        releases = json.load(r)
    best: Optional[Update] = None
    for rel in releases:
        tag = rel.get("tag_name", "")
        if rel.get("draft") or rel.get("prerelease") or not tag.startswith(RELEASE_TAG_PREFIX):
            continue
        version = tag[len(RELEASE_TAG_PREFIX):]
        asset = next((a for a in rel.get("assets", []) if a["name"].lower().endswith("setup.exe")), None)
        if asset is None:
            continue
        if best is None or parse_version(version) > parse_version(best.version):
            best = Update(version, rel.get("body") or "", asset["browser_download_url"], asset.get("size", 0),
                          rel.get("html_url", ""))
    if best and parse_version(best.version) > parse_version(__version__):
        return best
    return None


def download(update: Update, progress: Callable[[float], None]) -> Path:
    dest = Path(tempfile.gettempdir()) / f"IDPhoto-{update.version}-Setup.exe"
    req = urllib.request.Request(update.url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or update.size or 0)
        done = 0
        while chunk := r.read(1 << 16):
            f.write(chunk)
            done += len(chunk)
            if total:
                progress(done / total)
    return dest


def run_installer(installer: Path) -> None:
    """يشغّل ملف التثبيت بصمت. على المستدعي إغلاق البرنامج بعدها مباشرة؛
    المثبّت ينتظر إغلاقه ثم يعيد فتحه بعد التحديث."""
    if os.name != "nt":
        raise RuntimeError("التحديث التلقائي متاح على ويندوز فقط.")
    subprocess.Popen([str(installer), "/SILENT", "/CLOSEAPPLICATIONS", "/NORESTART"],
                     close_fds=True)
