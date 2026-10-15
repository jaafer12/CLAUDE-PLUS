"""أدوات مساعدة للنظام: تشغيل الأوامر وPowerShell، وصلاحيات المسؤول، ونقطة الاستعادة."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
from typing import Any, Optional

IS_WINDOWS = os.name == "nt"
NO_WINDOW = 0x08000000 if IS_WINDOWS else 0  # CREATE_NO_WINDOW: لا تظهر نافذة سوداء


class CommandError(RuntimeError):
    pass


def _decode(data: bytes) -> str:
    """أوامر ويندوز مثل sfc تكتب بـ UTF-16، وغيرها بصفحة الرموز المحلية."""
    if not data:
        return ""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff") or data.count(b"\x00") > len(data) // 4:
        try:
            return data.decode("utf-16").replace("\r", "")
        except UnicodeDecodeError:
            pass
    for enc in ("utf-8", "mbcs" if IS_WINDOWS else "latin-1"):
        try:
            return data.decode(enc).replace("\r", "")
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", "replace")


def run(cmd: list[str], timeout: float = 120) -> tuple[int, str]:
    """يشغّل أمراً ويرجع (رمز الخروج، النص)."""
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=timeout, creationflags=NO_WINDOW,
                           stdin=subprocess.DEVNULL)
    except FileNotFoundError as e:
        raise CommandError(f"الأمر غير موجود: {cmd[0]}") from e
    except subprocess.TimeoutExpired as e:
        raise CommandError("انتهت مهلة الأمر") from e
    return p.returncode, (_decode(p.stdout) + _decode(p.stderr)).strip()


def powershell(script: str, timeout: float = 90) -> str:
    """يشغّل سكربت PowerShell ويرجع ناتجه نصاً (UTF-8)."""
    if not IS_WINDOWS:
        raise CommandError("PowerShell متاح على ويندوز فقط")
    full = ("$ProgressPreference='SilentlyContinue';$ErrorActionPreference='Stop';"
            "[Console]::OutputEncoding=[Text.Encoding]::UTF8;" + script)
    code, out = run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-Command", full], timeout=timeout)
    if code != 0:
        raise CommandError(out.splitlines()[0] if out else f"PowerShell فشل (الرمز {code})")
    return out


def ps_json(script: str, timeout: float = 90) -> Any:
    """يشغّل سكربت PowerShell ويحوّل ناتجه من JSON. القائمة ذات العنصر الواحد تبقى قائمة."""
    out = powershell(f"@({script}) | ConvertTo-Json -Depth 4 -Compress", timeout)
    if not out:
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else [data]


# ---------------------------------------------------------------- الصلاحيات

def is_admin() -> bool:
    if IS_WINDOWS:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except OSError:
            return False
    return hasattr(os, "geteuid") and os.geteuid() == 0


def relaunch_as_admin(args: str = "") -> bool:
    """يعيد تشغيل البرنامج بصلاحيات المسؤول (تظهر نافذة UAC). يرجع True إن بدأ التشغيل."""
    if not IS_WINDOWS:
        return False
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, args
    else:
        exe = sys.executable.replace("python.exe", "pythonw.exe")
        params = f'"{os.path.abspath(sys.argv[0])}" {args}'.strip()
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return rc > 32


# ---------------------------------------------------------------- نقطة الاستعادة

def create_restore_point(description: str = "PCDoctor") -> Optional[str]:
    """ينشئ نقطة استعادة للنظام قبل الإصلاح. يرجع None عند النجاح أو سبب الفشل."""
    if not IS_WINDOWS:
        return "غير متاح على هذا النظام"
    if not is_admin():
        return "يحتاج صلاحيات المسؤول"
    try:
        # ويندوز يرفض أكثر من نقطة كل 24 ساعة إلا إذا عُدّل هذا الإعداد
        powershell(
            "New-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\SystemRestore' "
            "-Name SystemRestorePointCreationFrequency -Value 0 -PropertyType DWord -Force | Out-Null;"
            "Enable-ComputerRestore -Drive \"$env:SystemDrive\\\" -ErrorAction SilentlyContinue;"
            f"Checkpoint-Computer -Description '{description}' -RestorePointType MODIFY_SETTINGS",
            timeout=300)
        return None
    except CommandError as e:
        return str(e)


def open_path(target: str, args: str = "") -> None:
    """يفتح ملفاً أو رابطاً أو أداة نظام (مثل ms-settings:windowsupdate).
    ShellExecute يعرض نافذة UAC للأدوات التي تحتاج صلاحيات (مثل مدير المهام)."""
    if IS_WINDOWS:
        if ctypes.windll.shell32.ShellExecuteW(None, "open", target, args or None, None, 1) <= 32:
            raise CommandError(f"تعذّر فتح {target}")
    else:
        subprocess.Popen(["xdg-open", target])
