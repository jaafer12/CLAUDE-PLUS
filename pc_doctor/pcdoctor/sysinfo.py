"""معلومات الجهاز لصفحة «معلومات الجهاز»."""

from __future__ import annotations

import getpass
import platform
import socket
import time

import psutil

from .checks import human
from .system import IS_WINDOWS, CommandError, ps_json


def _reg(key: str, name: str):
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


def _windows_name() -> str:
    key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    name = _reg(key, "ProductName") or "Windows"
    build = int(_reg(key, "CurrentBuildNumber") or 0)
    if build >= 22000:  # ويندوز 11 ما زال يكتب «Windows 10» في ProductName
        name = name.replace("Windows 10", "Windows 11")
    disp = _reg(key, "DisplayVersion") or _reg(key, "ReleaseId") or ""
    return f"{name} {disp} (البناء {build})".strip()


def _cpu_name() -> str:
    if IS_WINDOWS:
        n = _reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
        if n:
            return " ".join(n.split())
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "غير معروف"


def collect() -> list[tuple[str, str, str]]:
    """قائمة (رمز، العنوان، القيمة)."""
    vm = psutil.virtual_memory()
    freq = psutil.cpu_freq()
    boot = time.time() - psutil.boot_time()
    rows = [
        ("💻", "اسم الجهاز", socket.gethostname()),
        ("👤", "المستخدم", getpass.getuser()),
        ("🪟", "نظام التشغيل", _windows_name() if IS_WINDOWS else f"{platform.system()} {platform.release()}"),
        ("⚙️", "المعالج", _cpu_name()),
        ("🧮", "الأنوية", f"{psutil.cpu_count(logical=False) or '?'} نواة فعلية، {psutil.cpu_count()} منطقية"
                         + (f"، {freq.max / 1000:.2f} غيغاهرتز" if freq and freq.max else "")),
        ("🧠", "الذاكرة", human(vm.total)),
    ]
    if IS_WINDOWS:
        try:
            for g in ps_json("Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion"):
                ram = int(g.get("AdapterRAM") or 0)
                rows.append(("🎮", "كرت الشاشة", f"{g.get('Name')}" + (f" · {human(ram)}" if ram > 0 else "")
                             + f" · التعريف {g.get('DriverVersion')}"))
            for b in ps_json("Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product"):
                rows.append(("🧷", "اللوحة الأم", f"{b.get('Manufacturer')} {b.get('Product')}"))
            for b in ps_json("Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, "
                             "@{n='Date';e={$_.ReleaseDate.ToString('yyyy-MM-dd')}}"):
                rows.append(("🔧", "BIOS", f"{b.get('SMBIOSBIOSVersion')} ({b.get('Date')})"))
        except CommandError:
            pass
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in p.opts or not p.fstype:
            continue
        try:
            u = psutil.disk_usage(p.mountpoint)
        except OSError:
            continue
        if not IS_WINDOWS and p.mountpoint != "/":
            continue
        rows.append(("💽", f"القرص {p.mountpoint}", f"{p.fstype} · متاح {human(u.free)} من {human(u.total)}"))
    bat = psutil.sensors_battery()
    if bat:
        rows.append(("🔋", "البطارية", f"{bat.percent:.0f}٪" + (" · على الشاحن" if bat.power_plugged else "")))
    days, rem = divmod(int(boot), 86400)
    rows.append(("⏱️", "مدة التشغيل", f"{days} يوم و{rem // 3600} ساعة" if days else f"{rem // 3600} ساعة و{rem % 3600 // 60} دقيقة"))
    return rows
