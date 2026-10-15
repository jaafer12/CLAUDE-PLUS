"""فحوص الحاسبة وإصلاحاتها.

كل فحص يرجع Finding بحالته (سليم / تنبيه / خطأ) وتفاصيله، ويمكن أن يقدّم إصلاحاً:
- auto: إصلاح آمن يُنفَّذ مباشرة ويدخل في «إصلاح الكل».
- action: إجراء يحتاج قرار المستخدم (إعادة تشغيل، فتح أداة النظام…) ولا يدخل في «إصلاح الكل».
"""

from __future__ import annotations

import os
import shutil
import socket
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from glob import glob
from pathlib import Path
from typing import Any, Callable, Optional

import psutil

from .system import IS_WINDOWS, CommandError, is_admin, open_path, powershell, ps_json, run

OK, WARN, ERROR, INFO, SKIP = "ok", "warn", "error", "info", "skip"
GB = 1024 ** 3
MB = 1024 ** 2


def human(n: float) -> str:
    for unit, size in (("غيغابايت", GB), ("ميغابايت", MB), ("كيلوبايت", 1024)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{int(n)} بايت"


@dataclass
class Finding:
    status: str
    summary: str
    details: list[str] = field(default_factory=list)
    advice: str = ""
    fix_kind: Optional[str] = None  # None / "auto" / "action"
    fix_label: str = "إصلاح"
    confirm: str = ""  # رسالة تأكيد قبل الإصلاح
    data: Any = None  # تُمرَّر إلى دالة الإصلاح


@dataclass
class Check:
    id: str
    title: str
    category: str
    icon: str
    scan: Callable[[bool], Finding]  # المعامل: فحص شامل (أبطأ)
    fix: Optional[Callable[[Finding], str]] = None
    fix_needs_admin: bool = False
    windows_only: bool = True
    deep_only: bool = False  # يعمل في الفحص الشامل فقط


class Skip(Exception):
    """الفحص غير متاح هنا (نظام آخر أو بلا صلاحيات)."""


# ================================================================ التخزين

def _drives() -> list:
    out = []
    for p in psutil.disk_partitions(all=False):
        if "cdrom" in p.opts or not p.fstype:
            continue
        if not IS_WINDOWS and not (p.mountpoint == "/" or p.mountpoint.startswith("/home")):
            continue
        try:
            out.append((p.mountpoint, psutil.disk_usage(p.mountpoint)))
        except (PermissionError, OSError):
            continue
    return out


def scan_disk_space(deep: bool) -> Finding:
    status, details = OK, []
    for mount, u in _drives():
        free_pct = 100 - u.percent
        mark = "✔"
        if free_pct < 10 or u.free < 5 * GB:
            status, mark = ERROR, "✖"
        elif free_pct < 20:
            status, mark = (WARN if status == OK else status), "!"
        details.append(f"{mark}  {mount}  متاح {human(u.free)} من {human(u.total)} ({free_pct:.0f}٪)")
    if status == OK:
        return Finding(OK, "المساحة الفارغة كافية في كل الأقراص", details)
    return Finding(status, "المساحة الفارغة قليلة، وهذا يبطئ ويندوز ويمنع التحديثات", details,
                   advice="احذف الملفات المؤقتة، وانقل الصور والفيديو إلى قرص آخر، وأزل البرامج التي لا تستعملها.",
                   fix_kind="auto", fix_label="تنظيف الملفات المؤقتة")


def _junk_locations() -> list[tuple[str, list[str]]]:
    if not IS_WINDOWS:
        return [("مصغّرات الصور", [str(Path.home() / ".cache" / "thumbnails")])]
    env = os.environ.get
    local, windir = env("LOCALAPPDATA", ""), env("WINDIR", r"C:\Windows")
    return [
        ("ملفات المستخدم المؤقتة", [tempfile.gettempdir()]),
        ("ملفات ويندوز المؤقتة", [os.path.join(windir, "Temp")]),
        ("تقارير الأعطال", [os.path.join(local, "CrashDumps"),
                            os.path.join(local, "Microsoft", "Windows", "WER", "ReportArchive"),
                            os.path.join(env("PROGRAMDATA", r"C:\ProgramData"), "Microsoft", "Windows", "WER",
                                         "ReportArchive")]),
        ("ذاكرة المتصفحات المؤقتة",
         glob(os.path.join(local, "Google", "Chrome", "User Data", "*", "Cache", "Cache_Data"))
         + glob(os.path.join(local, "Microsoft", "Edge", "User Data", "*", "Cache", "Cache_Data"))
         + glob(os.path.join(local, "BraveSoftware", "Brave-Browser", "User Data", "*", "Cache", "Cache_Data"))
         + glob(os.path.join(local, "Mozilla", "Firefox", "Profiles", "*", "cache2"))),
        ("ملفات تحديث ويندوز المنزّلة", [os.path.join(windir, "SoftwareDistribution", "Download")]),
        ("ذاكرة الإنترنت المؤقتة", [os.path.join(local, "Microsoft", "Windows", "INetCache")]),
    ]


def _dir_size(path: str) -> tuple[int, int]:
    total = count = 0
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                        elif e.is_file(follow_symlinks=False):
                            total += e.stat(follow_symlinks=False).st_size
                            count += 1
                    except OSError:
                        continue
        except OSError:
            continue
    return total, count


def _recycle_bin_size() -> int:
    if not IS_WINDOWS:
        return 0
    import ctypes

    class SHQUERYRBINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint32), ("i64Size", ctypes.c_int64), ("i64NumItems", ctypes.c_int64)]

    info = SHQUERYRBINFO(ctypes.sizeof(SHQUERYRBINFO), 0, 0)
    if ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info)) == 0:
        return int(info.i64Size)
    return 0


def scan_junk(deep: bool) -> Finding:
    total, details = 0, []
    for name, dirs in _junk_locations():
        size = sum(_dir_size(d)[0] for d in dirs if os.path.isdir(d))
        if size > MB:
            details.append(f"{name}: {human(size)}")
        total += size
    rb = _recycle_bin_size()
    if rb > MB:
        details.append(f"سلة المحذوفات: {human(rb)}")
    total += rb
    if total < 300 * MB:
        return Finding(OK, f"الملفات غير الضرورية قليلة ({human(total)})", details)
    return Finding(WARN if total < 3 * GB else ERROR, f"يمكن تحرير {human(total)} من الملفات غير الضرورية", details,
                   advice="هذه ملفات مؤقتة يعيد ويندوز والبرامج إنشاءها عند الحاجة، وحذفها آمن.",
                   fix_kind="auto", fix_label="تنظيف", data=total)


def _delete_tree_contents(path: str, min_age: float) -> int:
    """يحذف محتويات المجلد (لا المجلد نفسه)، ويتجاوز الملفات المستعملة والأحدث من min_age ثانية."""
    freed = 0
    now = time.time()
    for root, dirs, files in os.walk(path, topdown=False):
        for f in files:
            p = os.path.join(root, f)
            try:
                st = os.stat(p, follow_symlinks=False)
                if now - st.st_mtime < min_age:
                    continue
                os.remove(p)
                freed += st.st_size
            except OSError:
                continue
        if root != path:
            try:
                os.rmdir(root)
            except OSError:
                pass
    return freed


def fix_junk(f: Finding) -> str:
    freed = 0
    for name, dirs in _junk_locations():
        for d in dirs:
            if os.path.isdir(d):
                # الملفات المؤقتة الحديثة قد تكون لبرنامج يعمل الآن (مثل مثبّت)، فنتركها
                freed += _delete_tree_contents(d, min_age=3600)
    rb = _recycle_bin_size()
    if IS_WINDOWS and rb:
        import ctypes
        # SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        if ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x7) == 0:
            freed += rb
    return f"حُرِّرت {human(freed)}. بعض الملفات المستعملة حالياً تُركت وستُحذف في مرة لاحقة."


# ================================================================ الأداء

def _top_processes(key: str, n: int = 5) -> list[tuple[str, float]]:
    agg: dict[str, float] = {}
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            name = p.info["name"] or "?"
            if key == "mem":
                agg[name] = agg.get(name, 0) + (p.info["memory_info"].rss if p.info["memory_info"] else 0)
            else:
                agg[name] = agg.get(name, 0) + p.cpu_percent(None)
        except (psutil.Error, AttributeError):
            continue
    agg.pop("System Idle Process", None)
    agg.pop("Idle", None)
    return sorted(agg.items(), key=lambda x: -x[1])[:n]


def scan_memory(deep: bool) -> Finding:
    vm = psutil.virtual_memory()
    details = [f"المستعمل {human(vm.used)} من {human(vm.total)} ({vm.percent:.0f}٪)", "أكثر البرامج استهلاكاً للذاكرة:"]
    details += [f"   • {name}: {human(size)}" for name, size in _top_processes("mem")]
    if vm.total < 4 * GB:
        advice = "ذاكرة الجهاز أقل من 4 غيغابايت؛ زيادتها تحسّن السرعة كثيراً."
    else:
        advice = "أغلق البرامج وألسنة المتصفح التي لا تحتاجها، وعطّل البرامج التي تبدأ مع ويندوز."
    if vm.percent >= 90:
        return Finding(ERROR, f"الذاكرة شبه ممتلئة ({vm.percent:.0f}٪) والجهاز سيبطؤ", details, advice)
    if vm.percent >= 80:
        return Finding(WARN, f"استهلاك الذاكرة مرتفع ({vm.percent:.0f}٪)", details, advice)
    return Finding(OK, f"الذاكرة جيدة ({vm.percent:.0f}٪ مستعملة من {human(vm.total)})", details)


def scan_cpu(deep: bool) -> Finding:
    for p in psutil.process_iter():
        try:
            p.cpu_percent(None)
        except psutil.Error:
            pass
    load = psutil.cpu_percent(interval=1.5)
    cores = psutil.cpu_count() or 1
    top = [(n, v / cores) for n, v in _top_processes("cpu")]
    details = [f"الحمل الحالي {load:.0f}٪ على {cores} نواة", "أكثر البرامج استهلاكاً للمعالج:"]
    details += [f"   • {n}: {v:.0f}٪" for n, v in top if v >= 0.5] or ["   • لا يوجد برنامج يستهلك المعالج الآن"]
    if load >= 85:
        return Finding(WARN, f"المعالج مشغول جداً ({load:.0f}٪)", details,
                       "إن بقي الحمل عالياً بلا سبب فقد يكون برنامجاً عالقاً أو برنامجاً ضاراً؛ افحص الجهاز بمكافح الفيروسات.")
    return Finding(OK, f"المعالج يعمل بحمل طبيعي ({load:.0f}٪)", details)


def scan_uptime(deep: bool) -> Finding:
    days = (time.time() - psutil.boot_time()) / 86400
    text = f"آخر إعادة تشغيل منذ {days:.0f} يوم" if days >= 1 else f"آخر إعادة تشغيل منذ {days * 24:.0f} ساعة"
    if days >= 7:
        return Finding(WARN, text, [], "إعادة التشغيل تكمل التحديثات وتحرّر الذاكرة. «إيقاف التشغيل» مع التشغيل السريع لا يُحتسب إعادة تشغيل.",
                       fix_kind="action", fix_label="إعادة التشغيل",
                       confirm="سيُعاد تشغيل الحاسبة بعد دقيقة. احفظ عملك أولاً. هل تريد المتابعة؟")
    return Finding(OK, text)


def fix_restart(f: Finding) -> str:
    if IS_WINDOWS:
        run(["shutdown", "/r", "/t", "60", "/c", "طبيب الحاسبة: إعادة تشغيل لإكمال الإصلاح"])
        return "ستُعاد الحاسبة بعد دقيقة. لإلغاء ذلك اكتب في «تشغيل»: shutdown /a"
    raise CommandError("غير متاح على هذا النظام")


STARTUP_KEYS = [
    ("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"),
]
APPROVED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved"


def _startup_items() -> list[str]:
    import winreg

    hives = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}

    def disabled(hive, sub, name) -> bool:
        try:
            with winreg.OpenKey(hives[hive], f"{APPROVED}\\{sub}") as k:
                val, _ = winreg.QueryValueEx(k, name)
                return bool(val) and val[0] % 2 == 1  # 0x03 = معطّل
        except OSError:
            return False

    items = []
    for hive, key in STARTUP_KEYS:
        sub = "Run32" if "WOW6432Node" in key else "Run"
        try:
            with winreg.OpenKey(hives[hive], key) as k:
                for i in range(winreg.QueryInfoKey(k)[1]):
                    name = winreg.EnumValue(k, i)[0]
                    if name and not disabled(hive, sub, name):
                        items.append(name)
        except OSError:
            continue
    for folder in (os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup"),
                   os.path.join(os.environ.get("PROGRAMDATA", ""), r"Microsoft\Windows\Start Menu\Programs\Startup")):
        try:
            for f in os.listdir(folder):
                if f.lower() != "desktop.ini" and not disabled("HKCU", "StartupFolder", f):
                    items.append(os.path.splitext(f)[0])
        except OSError:
            continue
    return sorted(set(items), key=str.lower)


def scan_startup(deep: bool) -> Finding:
    items = _startup_items()
    details = [f"   • {n}" for n in items]
    n = len(items)
    fix = dict(fix_kind="action", fix_label="إدارة برامج البدء")
    if n > 12:
        return Finding(ERROR, f"{n} برنامجاً تبدأ مع ويندوز، وهذا يبطئ الإقلاع كثيراً", details,
                       "عطّل البرامج التي لا تحتاجها من تبويب «تطبيقات بدء التشغيل» في مدير المهام.", **fix)
    if n > 7:
        return Finding(WARN, f"{n} برامج تبدأ مع ويندوز", details,
                       "تعطيل غير الضروري منها يسرّع الإقلاع.", **fix)
    return Finding(OK, f"عدد برامج البدء مناسب ({n})", details)


def fix_startup(f: Finding) -> str:
    open_path("taskmgr.exe", "/0 /startup")
    return "فُتح مدير المهام؛ اختر تبويب «تطبيقات بدء التشغيل» وعطّل ما لا تحتاجه."


# ================================================================ الأمان

def scan_antivirus(deep: bool) -> Finding:
    products = ps_json("Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct "
                       "-ErrorAction SilentlyContinue | Select-Object displayName, productState")
    names = [p["displayName"] for p in products if p.get("displayName")]
    # البايت الأوسط من productState: 0x10 = الحماية تعمل
    active = [p["displayName"] for p in products if (int(p.get("productState") or 0) >> 8) & 0x10]
    third_party = [n for n in active if "defender" not in n.lower()]
    details = [f"   • {n}{'  (يعمل)' if n in active else '  (متوقف)'}" for n in names]

    try:
        mp = ps_json("Get-MpComputerStatus | Select-Object AMServiceEnabled, RealTimeProtectionEnabled, "
                     "AntivirusSignatureAge, QuickScanAge, IsTamperProtected")[0]
    except (CommandError, IndexError, ValueError):
        mp = None

    if third_party:
        return Finding(OK, f"الحماية من الفيروسات تعمل ({', '.join(third_party)})", details)
    if mp is None:
        if active:
            return Finding(OK, "الحماية من الفيروسات تعمل", details)
        return Finding(ERROR, "لا توجد حماية فعّالة من الفيروسات", details,
                       "ثبّت برنامج حماية أو فعّل Microsoft Defender من «أمان Windows».",
                       fix_kind="action", fix_label="فتح أمان Windows", data={"open": True})

    problems, todo = [], {}
    if not mp.get("RealTimeProtectionEnabled"):
        problems.append("الحماية في الوقت الحقيقي متوقفة")
        todo["realtime"] = True
    sig_age = int(mp.get("AntivirusSignatureAge") or 0)
    if sig_age > 3:
        problems.append(f"تعريفات الفيروسات قديمة (منذ {sig_age} يوم)")
        todo["signatures"] = True
    scan_age = int(mp.get("QuickScanAge") if mp.get("QuickScanAge") is not None else 999)
    if scan_age > 7:
        problems.append("لم يُجرَ فحص سريع منذ أكثر من أسبوع" if scan_age < 999 else "لم يُجرَ أي فحص للفيروسات")
        todo["scan"] = True
    details = [f"   • {p}" for p in problems] + details
    if not problems:
        return Finding(OK, "Microsoft Defender يعمل وتعريفاته حديثة", details)
    status = ERROR if "realtime" in todo else WARN
    return Finding(status, "Microsoft Defender يحتاج انتباهاً", details,
                   "يمكن تحديث التعريفات وتشغيل فحص سريع تلقائياً (يستغرق الفحص بضع دقائق).",
                   fix_kind="auto", fix_label="تحديث وفحص", data=todo)


def fix_antivirus(f: Finding) -> str:
    todo = f.data or {}
    if todo.get("open"):
        open_path("windowsdefender:")
        return "فُتح «أمان Windows»."
    done = []
    if todo.get("realtime"):
        try:
            powershell("Set-MpPreference -DisableRealtimeMonitoring $false", timeout=60)
            done.append("شُغِّلت الحماية في الوقت الحقيقي")
        except CommandError:
            open_path("windowsdefender://threat")
            done.append("تعذّر تشغيل الحماية تلقائياً (قد تمنعه «الحماية من العبث»)، ففُتح «أمان Windows» لتشغيلها يدوياً")
    if todo.get("signatures"):
        powershell("Update-MpSignature", timeout=600)
        done.append("حُدِّثت تعريفات الفيروسات")
    if todo.get("scan"):
        powershell("Start-MpScan -ScanType QuickScan", timeout=3600)
        threats = ps_json("Get-MpThreatDetection | Where-Object { $_.InitialDetectionTime -gt (Get-Date).AddHours(-2) }"
                          " | Select-Object ThreatID")
        done.append("انتهى الفحص السريع" + (f" ووُجد {len(threats)} تهديد عالجه Defender" if threats else " ولم يُعثر على تهديدات"))
    return "، ".join(done) + "."


def scan_firewall(deep: bool) -> Finding:
    profiles = ps_json("Get-NetFirewallProfile | Select-Object Name, Enabled")
    names = {"Domain": "شبكة المجال", "Private": "الشبكة الخاصة", "Public": "الشبكة العامة"}
    off = [names.get(p["Name"], p["Name"]) for p in profiles if not p.get("Enabled")]
    details = [f"   • {names.get(p['Name'], p['Name'])}: {'يعمل' if p.get('Enabled') else 'متوقف'}" for p in profiles]
    if off:
        return Finding(ERROR, "جدار الحماية متوقف في: " + "، ".join(off), details,
                       "جدار الحماية يمنع الاتصالات الضارة من الشبكة والإنترنت.",
                       fix_kind="auto", fix_label="تشغيل جدار الحماية")
    return Finding(OK, "جدار الحماية يعمل في كل الشبكات", details)


def fix_firewall(f: Finding) -> str:
    powershell("Set-NetFirewallProfile -Profile Domain,Private,Public -Enabled True")
    return "شُغِّل جدار الحماية."


def scan_windows_update(deep: bool) -> Finding:
    svc = ps_json("Get-Service wuauserv | Select-Object @{n='Start';e={[string]$_.StartType}}")[0]
    if svc.get("Start") == "Disabled":
        return Finding(ERROR, "خدمة تحديث ويندوز معطّلة", [],
                       "بلا تحديثات يبقى الجهاز مكشوفاً للثغرات الأمنية.",
                       fix_kind="auto", fix_label="تفعيل التحديثات", data="service")
    days = None
    try:
        out = powershell("$h = Get-HotFix | Where-Object InstalledOn | Sort-Object InstalledOn -Descending | "
                         "Select-Object -First 1; if ($h) { [int]((Get-Date) - $h.InstalledOn).TotalDays }")
        days = int(out) if out.strip().lstrip("-").isdigit() else None
    except CommandError:
        pass
    if days is not None and days > 60:
        return Finding(WARN, f"آخر تحديث لويندوز منذ {days} يوماً", [],
                       "افتح «Windows Update» واضغط «التحقق من وجود تحديثات».",
                       fix_kind="action", fix_label="فتح Windows Update", data="open")
    return Finding(OK, "تحديثات ويندوز تعمل" + (f" (آخر تحديث منذ {days} يوم)" if days is not None else ""))


def fix_windows_update(f: Finding) -> str:
    if f.data == "service":
        powershell("Set-Service wuauserv -StartupType Manual; Start-Service wuauserv")
        return "فُعِّلت خدمة تحديث ويندوز."
    open_path("ms-settings:windowsupdate")
    return "فُتحت صفحة Windows Update."


def _reg_value(hive: str, key: str, name: str):
    import winreg

    root = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}[hive]
    try:
        with winreg.OpenKey(root, key) as k:
            return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None


UAC_KEY = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"


def scan_uac(deep: bool) -> Finding:
    if _reg_value("HKLM", UAC_KEY, "EnableLUA") == 0:
        return Finding(ERROR, "التحكم بحساب المستخدم (UAC) معطّل", [],
                       "بدونه تستطيع البرامج الضارة تغيير النظام دون أن تسألك. يحتاج تفعيله إعادة تشغيل.",
                       fix_kind="auto", fix_label="تفعيل UAC")
    return Finding(OK, "التحكم بحساب المستخدم (UAC) يعمل")


def fix_uac(f: Finding) -> str:
    powershell(f"Set-ItemProperty -Path 'HKLM:\\{UAC_KEY}' -Name EnableLUA -Value 1")
    return "فُعِّل UAC، ويعمل بعد إعادة تشغيل الحاسبة."


def _hosts_path() -> Path:
    return Path(os.environ.get("WINDIR", r"C:\Windows")) / "System32" / "drivers" / "etc" / "hosts"


def scan_hosts(deep: bool) -> Finding:
    try:
        lines = _hosts_path().read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as e:
        raise Skip("تعذّر قراءة ملف hosts") from e
    entries = []
    for line in lines:
        line = line.split("#", 1)[0].strip()
        parts = line.split()
        if len(parts) >= 2 and not all(h.lower() in ("localhost", "localhost.localdomain") for h in parts[1:]):
            entries.append(" ".join(parts))
    if entries:
        return Finding(WARN, f"ملف hosts فيه {len(entries)} توجيه مخصّص", [f"   • {e}" for e in entries[:15]],
                       "بعض البرامج الضارة تستعمله لتوجيه المواقع إلى صفحات مزيّفة. إن لم تضف هذه الأسطر بنفسك فأعده إلى الأصل (تُحفظ نسخة احتياطية).",
                       fix_kind="action", fix_label="إعادة إلى الأصل",
                       confirm="سيُعاد ملف hosts إلى محتواه الافتراضي وتُحفظ نسخة منه باسم hosts.pcdoctor.bak. هل تريد المتابعة؟")
    return Finding(OK, "ملف hosts سليم")


HOSTS_DEFAULT = """# Copyright (c) 1993-2009 Microsoft Corp.
#
# This is a sample HOSTS file used by Microsoft TCP/IP for Windows.
#
# localhost name resolution is handled within DNS itself.
#\t127.0.0.1       localhost
#\t::1             localhost
"""


def fix_hosts(f: Finding) -> str:
    p = _hosts_path()
    shutil.copy2(p, p.with_name("hosts.pcdoctor.bak"))
    p.write_text(HOSTS_DEFAULT, encoding="utf-8")
    run(["ipconfig", "/flushdns"])
    return f"أُعيد ملف hosts إلى الأصل، والنسخة القديمة في {p.with_name('hosts.pcdoctor.bak')}."


PROXY_KEY = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def scan_proxy(deep: bool) -> Finding:
    if _reg_value("HKCU", PROXY_KEY, "ProxyEnable") == 1:
        server = _reg_value("HKCU", PROXY_KEY, "ProxyServer") or "?"
        return Finding(WARN, "الإنترنت يمرّ عبر خادم وسيط (Proxy)", [f"   • {server}"],
                       "إن لم تضبطه أنت أو جهة عملك فقد يكون من برنامج ضار يراقب التصفح.",
                       fix_kind="action", fix_label="إيقاف الخادم الوسيط",
                       confirm="سيُوقف الخادم الوسيط. إن كانت شبكة عملك تحتاجه فلن يعمل الإنترنت حتى تعيده. هل تريد المتابعة؟")
    return Finding(OK, "لا يوجد خادم وسيط يغيّر اتصالك")


def fix_proxy(f: Finding) -> str:
    import winreg

    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PROXY_KEY, 0, winreg.KEY_SET_VALUE) as k:
        winreg.SetValueEx(k, "ProxyEnable", 0, winreg.REG_DWORD, 0)
    return "أُوقف الخادم الوسيط."


# ================================================================ النظام

CRITICAL_SERVICES = {
    "Audiosrv": "الصوت", "AudioEndpointBuilder": "أجهزة الصوت", "Dhcp": "عنوان الشبكة (DHCP)",
    "Dnscache": "أسماء المواقع (DNS)", "EventLog": "سجلّ الأحداث", "Winmgmt": "إدارة ويندوز (WMI)",
    "BFE": "محرّك التصفية", "mpssvc": "جدار الحماية", "nsi": "واجهة الشبكة", "CryptSvc": "التشفير",
    "LanmanWorkstation": "مشاركة الملفات", "Themes": "السمات", "Schedule": "المهام المجدولة",
    "Power": "الطاقة", "PlugPlay": "التوصيل والتشغيل", "WSearch": "البحث في ويندوز",
    "Spooler": "الطباعة",
}


def scan_services(deep: bool) -> Finding:
    names = ",".join(f"'{n}'" for n in CRITICAL_SERVICES)
    svcs = ps_json(f"Get-Service -Name {names} -ErrorAction SilentlyContinue | "
                   "Select-Object Name, @{n='Status';e={[string]$_.Status}}, @{n='Start';e={[string]$_.StartType}}")
    stopped = [s for s in svcs if s.get("Start") == "Automatic" and s.get("Status") != "Running"]
    disabled = [s for s in svcs if s.get("Start") == "Disabled" and s["Name"] not in ("WSearch", "Spooler")]
    bad = stopped + disabled
    if not bad:
        return Finding(OK, f"خدمات ويندوز الأساسية تعمل ({len(svcs)})")
    details = [f"   • {CRITICAL_SERVICES.get(s['Name'], s['Name'])} ({s['Name']}): "
               f"{'معطّلة' if s in disabled else 'متوقفة'}" for s in bad]
    return Finding(ERROR, f"{len(bad)} من خدمات ويندوز الأساسية لا تعمل", details,
                   "توقّف هذه الخدمات يسبب مشكلات مثل انقطاع الصوت أو الإنترنت أو الطباعة.",
                   fix_kind="auto", fix_label="تشغيل الخدمات", data=[s["Name"] for s in bad])


def fix_services(f: Finding) -> str:
    failed = []
    for name in f.data or []:
        try:
            powershell(f"$s = Get-Service '{name}'; if ($s.StartType -eq 'Disabled') "
                       f"{{ Set-Service '{name}' -StartupType Automatic }}; Start-Service '{name}'", timeout=60)
        except CommandError:
            failed.append(CRITICAL_SERVICES.get(name, name))
    if failed:
        return "شُغِّلت الخدمات، ما عدا: " + "، ".join(failed) + ". أعد تشغيل الحاسبة ثم افحص مجدداً."
    return "شُغِّلت كل الخدمات."


def scan_system_files(deep: bool) -> Finding:
    if not is_admin():
        raise Skip("يحتاج صلاحيات المسؤول")
    mode = "-ScanHealth" if deep else "-CheckHealth"
    out = powershell(f"(Repair-WindowsImage -Online {mode}).ImageHealthState", timeout=3600 if deep else 300)
    state = out.strip().splitlines()[-1] if out.strip() else ""
    how = "فحص شامل" if deep else "فحص سريع (للفحص الكامل اختر «فحص شامل»)"
    if state == "Healthy":
        return Finding(OK, "ملفات نظام ويندوز سليمة", [f"   • {how}"])
    return Finding(ERROR, "في ملفات نظام ويندوز تلف", [f"   • الحالة: {state or 'غير معروفة'}"],
                   "الإصلاح يستعمل DISM ثم SFC، ويستغرق 15–40 دقيقة ويحتاج إنترنت.",
                   fix_kind="auto", fix_label="إصلاح ملفات النظام")


def fix_system_files(f: Finding) -> str:
    powershell("Repair-WindowsImage -Online -RestoreHealth | Out-Null", timeout=7200)
    run(["sfc", "/scannow"], timeout=7200)
    return "انتهى إصلاح ملفات النظام (DISM و SFC). أعد تشغيل الحاسبة لإكماله."


def scan_events(deep: bool) -> Finding:
    days = 30 if deep else 7
    events = ps_json(
        f"Get-WinEvent -FilterHashtable @{{LogName='System'; StartTime=(Get-Date).AddDays(-{days}); "
        "Id=41,1001,7,51,55,153,129,6008} -ErrorAction SilentlyContinue | "
        "Select-Object Id, ProviderName", timeout=120)
    whea = ps_json(f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='Microsoft-Windows-WHEA-Logger';"
                   f" StartTime=(Get-Date).AddDays(-{days}); Level=1,2,3}} -ErrorAction SilentlyContinue | "
                   "Select-Object Id", timeout=60)
    crashes = ps_json(f"Get-WinEvent -FilterHashtable @{{LogName='Application'; Id=1000; "
                      f"StartTime=(Get-Date).AddDays(-{days})}} -MaxEvents 300 -ErrorAction SilentlyContinue | "
                      "ForEach-Object { $_.Properties[0].Value }", timeout=120)

    def count(ids, *providers):
        return sum(1 for e in events if e.get("Id") in ids
                   and (not providers or any(p in (e.get("ProviderName") or "").lower() for p in providers)))

    bsod = count({1001}, "systemerrorreporting", "bugcheck")
    power = max(count({41}, "kernel-power"), count({6008}, "eventlog"))
    disk = count({7, 51}, "disk") + count({55}, "ntfs")
    disk_mild = count({153}, "disk") + count({129}, "stor")
    details, status = [], OK
    if bsod:
        details.append(f"   • شاشة زرقاء (انهيار النظام): {bsod} مرة")
        status = ERROR
    if whea:
        details.append(f"   • أخطاء في العتاد (WHEA): {len(whea)}")
        status = ERROR
    if disk:
        details.append(f"   • أخطاء في القرص أو نظام الملفات: {disk}")
        status = ERROR
    if disk_mild:
        details.append(f"   • تأخّر أو إعادة محاولة في القراءة من القرص: {disk_mild}")
        status = WARN if status == OK else status
    if power:
        details.append(f"   • إطفاء مفاجئ بلا إيقاف تشغيل صحيح: {power} مرة")
        status = WARN if status == OK else status
    apps: dict[str, int] = {}
    for c in crashes:
        apps[str(c)] = apps.get(str(c), 0) + 1
    if apps:
        top = sorted(apps.items(), key=lambda x: -x[1])[:5]
        details.append("   • برامج انهارت: " + "، ".join(f"{n} ({k})" for n, k in top))
    if status == OK:
        return Finding(OK, f"لا أخطاء خطيرة في سجلّ النظام خلال آخر {days} يوم", details)
    advice = []
    if disk or disk_mild:
        advice.append("أخطاء القرص قد تعني أنه يتلف: خذ نسخة احتياطية من ملفاتك فوراً.")
    if bsod or whea:
        advice.append("الشاشة الزرقاء وأخطاء العتاد تنتج غالباً عن تعريفات قديمة أو حرارة عالية أو ذاكرة تالفة؛ حدّث التعريفات ونظّف المراوح.")
    if power:
        advice.append("الإطفاء المفاجئ يكون من انقطاع الكهرباء أو البطارية أو ارتفاع الحرارة.")
    return Finding(status, f"وُجدت أخطاء في سجلّ النظام خلال آخر {days} يوم", details, " ".join(advice),
                   fix_kind="action", fix_label="فتح عارض الأحداث")


def fix_events(f: Finding) -> str:
    open_path("eventvwr.msc")
    return "فُتح عارض الأحداث."


REBOOT_KEYS = [
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
    r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired",
]


def scan_pending_reboot(deep: bool) -> Finding:
    import winreg

    pending = False
    for key in REBOOT_KEYS:
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key))
            pending = True
        except OSError:
            pass
    if pending:
        return Finding(WARN, "توجد تحديثات أو إصلاحات تنتظر إعادة تشغيل الحاسبة", [],
                       "بعض التحديثات لا تكتمل إلا بعد إعادة التشغيل.",
                       fix_kind="action", fix_label="إعادة التشغيل",
                       confirm="سيُعاد تشغيل الحاسبة بعد دقيقة. احفظ عملك أولاً. هل تريد المتابعة؟")
    return Finding(OK, "لا شيء ينتظر إعادة التشغيل")


# ================================================================ العتاد

def scan_drivers(deep: bool) -> Finding:
    devs = ps_json("Get-CimInstance Win32_PnPEntity | Where-Object { $_.ConfigManagerErrorCode -ne 0 -and "
                   "$_.ConfigManagerErrorCode -ne 22 } | Select-Object Name, ConfigManagerErrorCode", timeout=120)
    if not devs:
        return Finding(OK, "كل الأجهزة وتعريفاتها تعمل")
    codes = {1: "غير مهيّأ", 10: "لا يبدأ", 28: "بلا تعريف", 31: "تعريف لا يعمل", 43: "أوقفه ويندوز لخلل",
             45: "غير موصول", 39: "التعريف تالف", 18: "يحتاج إعادة تثبيت"}
    details = [f"   • {d.get('Name') or 'جهاز غير معروف'}: {codes.get(d.get('ConfigManagerErrorCode'), 'خطأ')} "
               f"(الرمز {d.get('ConfigManagerErrorCode')})" for d in devs]
    only_unplugged = all(d.get("ConfigManagerErrorCode") == 45 for d in devs)
    return Finding(INFO if only_unplugged else WARN, f"{len(devs)} جهاز فيه مشكلة في التعريف", details,
                   "يبحث الإصلاح عن تغييرات العتاد ويعيد تثبيت التعريفات المتاحة. للأجهزة «بلا تعريف» نزّل التعريف من موقع الشركة المصنّعة أو من Windows Update (التحديثات الاختيارية).",
                   fix_kind="auto", fix_label="إعادة فحص الأجهزة")


def fix_drivers(f: Finding) -> str:
    run(["pnputil", "/scan-devices"], timeout=300)
    return "أُعيد فحص الأجهزة. إن بقيت المشكلة فافتح «إدارة الأجهزة» وحدّث تعريف الجهاز."


def scan_disk_health(deep: bool) -> Finding:
    disks = ps_json("Get-PhysicalDisk | Select-Object FriendlyName, MediaType, HealthStatus, Size")
    details, status = [], OK
    media = {"SSD": "SSD", "HDD": "قرص صلب", "Unspecified": ""}
    for d in disks:
        h = d.get("HealthStatus")
        h_ar = {"Healthy": "سليم", "Warning": "تحذير", "Unhealthy": "تالف"}.get(str(h), str(h))
        details.append(f"   • {d.get('FriendlyName')} {media.get(str(d.get('MediaType')), '')} "
                       f"{human(float(d.get('Size') or 0))}: {h_ar}")
        if h == "Unhealthy":
            status = ERROR
        elif h == "Warning" and status == OK:
            status = WARN
    if is_admin():
        try:
            rel = ps_json("Get-PhysicalDisk | Get-StorageReliabilityCounter | "
                          "Select-Object Wear, Temperature, ReadErrorsUncorrected")
            for r in rel:
                if r.get("Wear") and int(r["Wear"]) >= 80:
                    details.append(f"   • استهلاك SSD: {r['Wear']}٪")
                    status = WARN if status == OK else status
                if r.get("Temperature") and int(r["Temperature"]) >= 60:
                    details.append(f"   • حرارة القرص {r['Temperature']}°م")
                    status = WARN if status == OK else status
                if r.get("ReadErrorsUncorrected"):
                    details.append(f"   • أخطاء قراءة غير مصحّحة: {r['ReadErrorsUncorrected']}")
                    status = ERROR
        except CommandError:
            pass
    if status == OK:
        return Finding(OK, "الأقراص سليمة", details)
    return Finding(status, "القرص يظهر علامات تلف", details,
                   "خذ نسخة احتياطية من ملفاتك المهمة الآن، وفكّر في استبدال القرص. لا يمكن إصلاح تلف العتاد برمجياً.")


def scan_file_system(deep: bool) -> Finding:
    if not is_admin():
        raise Skip("يحتاج صلاحيات المسؤول")
    vols = ps_json("Get-Volume | Where-Object { $_.DriveLetter -and $_.DriveType -eq 'Fixed' -and "
                   "$_.FileSystem -eq 'NTFS' } | Select-Object DriveLetter", timeout=60)
    bad = []
    for v in vols:
        letter = v["DriveLetter"]
        out = powershell(f"Repair-Volume -DriveLetter {letter} -Scan", timeout=1800)
        if "NoErrorsFound" not in out:
            bad.append(letter)
    if bad:
        return Finding(ERROR, "أخطاء في نظام الملفات على: " + "، ".join(f"{b}:" for b in bad), [],
                       "يُصلَح القرص الآن، وقرص النظام يُصلَح عند إعادة التشغيل القادمة.",
                       fix_kind="auto", fix_label="إصلاح القرص", data=bad)
    return Finding(OK, "نظام الملفات سليم في كل الأقراص", [f"   • {v['DriveLetter']}:" for v in vols])


def fix_file_system(f: Finding) -> str:
    for letter in f.data or []:
        powershell(f"Repair-Volume -DriveLetter {letter} -SpotFix", timeout=3600)
    return "بدأ إصلاح القرص. إن كان قرص النظام فأعد تشغيل الحاسبة ليكتمل الإصلاح."


def scan_battery(deep: bool) -> Finding:
    bat = psutil.sensors_battery()
    if bat is None:
        raise Skip("لا توجد بطارية")
    details = [f"   • الشحن الآن {bat.percent:.0f}٪{' (موصول بالشاحن)' if bat.power_plugged else ''}"]
    if not IS_WINDOWS:
        return Finding(OK, "البطارية تعمل", details)
    report = Path(tempfile.gettempdir()) / "pcdoctor_battery.xml"
    run(["powercfg", "/batteryreport", "/xml", "/output", str(report)], timeout=60)
    try:
        root = ET.parse(report).getroot()
    except (OSError, ET.ParseError):
        return Finding(OK, "البطارية تعمل", details)
    finally:
        report.unlink(missing_ok=True)

    def find(tag):
        for el in root.iter():
            if el.tag.endswith(tag) and el.text and el.text.isdigit():
                return int(el.text)
        return 0

    design, full = find("DesignCapacity"), find("FullChargeCapacity")
    if not design or not full:
        return Finding(OK, "البطارية تعمل", details)
    health = min(100, full * 100 / design)
    details.append(f"   • السعة الحالية {full:,} من {design:,} ميلي واط ساعة")
    advice = "البطارية تفقد سعتها مع العمر؛ عند انخفاضها كثيراً يجب استبدالها."
    if health < 40:
        return Finding(ERROR, f"صحة البطارية ضعيفة ({health:.0f}٪)", details, advice)
    if health < 65:
        return Finding(WARN, f"صحة البطارية متوسطة ({health:.0f}٪)", details, advice)
    return Finding(OK, f"صحة البطارية جيدة ({health:.0f}٪)", details)


# ================================================================ الشبكة

def _tcp(host: str, port: int, timeout: float = 3) -> Optional[float]:
    t = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.perf_counter() - t) * 1000
    except OSError:
        return None


def scan_network(deep: bool) -> Finding:
    ping = _tcp("1.1.1.1", 443) or _tcp("8.8.8.8", 53)
    try:
        socket.setdefaulttimeout(4)
        socket.getaddrinfo("www.microsoft.com", 443)
        dns_ok = True
    except OSError:
        dns_ok = False
    finally:
        socket.setdefaulttimeout(None)
    if ping is None:
        up = [n for n, s in psutil.net_if_stats().items() if s.isup and not n.lower().startswith(("loopback", "lo"))]
        return Finding(ERROR, "لا يوجد اتصال بالإنترنت", [f"   • محوّلات الشبكة العاملة: {', '.join(up) or 'لا يوجد'}"],
                       "تأكد من الراوتر أو الواي فاي. يعيد الإصلاح ضبط إعدادات الشبكة في ويندوز.",
                       fix_kind="auto", fix_label="إصلاح الشبكة", data="full")
    details = [f"   • زمن الاستجابة: {ping:.0f} مللي ثانية"]
    if not dns_ok:
        return Finding(ERROR, "الإنترنت متصل لكن أسماء المواقع لا تُترجَم (DNS)", details,
                       "لهذا لا تفتح المواقع رغم وجود اتصال.", fix_kind="auto", fix_label="إصلاح DNS", data="dns")
    if ping > 250:
        return Finding(WARN, f"الاتصال بطيء (الاستجابة {ping:.0f} مللي ثانية)", details,
                       "أعد تشغيل الراوتر واقترب منه، أو أغلق البرامج التي تنزّل في الخلفية.")
    return Finding(OK, f"الإنترنت يعمل جيداً ({ping:.0f} مللي ثانية)", details)


def fix_network(f: Finding) -> str:
    run(["ipconfig", "/flushdns"])
    if f.data == "dns":
        return "مُسحت ذاكرة DNS. إن بقيت المشكلة فأعد تشغيل الراوتر."
    run(["ipconfig", "/release"], timeout=60)
    run(["ipconfig", "/renew"], timeout=90)
    if is_admin():
        run(["netsh", "winsock", "reset"])
        run(["netsh", "int", "ip", "reset"])
        return "أُعيد ضبط إعدادات الشبكة. أعد تشغيل الحاسبة لإكمال الإصلاح."
    return "جُدِّد عنوان الشبكة ومُسحت ذاكرة DNS."


# ================================================================ القائمة

CHECKS: list[Check] = [
    Check("disk_space", "مساحة الأقراص", "التخزين", "💽", scan_disk_space, fix_junk, windows_only=False),
    Check("junk", "الملفات غير الضرورية", "التخزين", "🧹", scan_junk, fix_junk, windows_only=False),
    Check("memory", "الذاكرة (RAM)", "الأداء", "🧠", scan_memory, windows_only=False),
    Check("cpu", "المعالج", "الأداء", "⚙️", scan_cpu, windows_only=False),
    Check("startup", "برامج بدء التشغيل", "الأداء", "🚀", scan_startup, fix_startup),
    Check("uptime", "مدة التشغيل", "الأداء", "⏱️", scan_uptime, fix_restart, windows_only=False),
    Check("antivirus", "الحماية من الفيروسات", "الأمان", "🛡️", scan_antivirus, fix_antivirus, fix_needs_admin=True),
    Check("firewall", "جدار الحماية", "الأمان", "🧱", scan_firewall, fix_firewall, fix_needs_admin=True),
    Check("windows_update", "تحديثات ويندوز", "الأمان", "🔄", scan_windows_update, fix_windows_update,
          fix_needs_admin=True),
    Check("uac", "التحكم بحساب المستخدم", "الأمان", "🔐", scan_uac, fix_uac, fix_needs_admin=True),
    Check("hosts", "ملف hosts", "الأمان", "📄", scan_hosts, fix_hosts, fix_needs_admin=True),
    Check("proxy", "الخادم الوسيط", "الأمان", "🕵️", scan_proxy, fix_proxy),
    Check("services", "خدمات ويندوز", "النظام", "🧩", scan_services, fix_services, fix_needs_admin=True),
    Check("system_files", "سلامة ملفات النظام", "النظام", "🗂️", scan_system_files, fix_system_files,
          fix_needs_admin=True),
    Check("events", "أخطاء النظام والأعطال", "النظام", "📋", scan_events, fix_events),
    Check("pending_reboot", "إعادة تشغيل معلّقة", "النظام", "♻️", scan_pending_reboot, fix_restart),
    Check("drivers", "الأجهزة والتعريفات", "العتاد", "🔌", scan_drivers, fix_drivers, fix_needs_admin=True),
    Check("disk_health", "صحة الأقراص", "العتاد", "🩺", scan_disk_health),
    Check("file_system", "نظام الملفات", "العتاد", "🧾", scan_file_system, fix_file_system, fix_needs_admin=True,
          deep_only=True),
    Check("battery", "البطارية", "العتاد", "🔋", scan_battery, windows_only=False),
    Check("network", "الإنترنت والشبكة", "الشبكة", "🌐", scan_network, fix_network, windows_only=False),
]

CATEGORIES = ["التخزين", "الأداء", "الأمان", "النظام", "العتاد", "الشبكة"]


def run_check(check: Check, deep: bool) -> Finding:
    if check.windows_only and not IS_WINDOWS:
        return Finding(SKIP, "متاح على ويندوز فقط")
    if check.deep_only and not deep:
        return Finding(SKIP, "يعمل في «الفحص الشامل» فقط")
    try:
        return check.scan(deep)
    except Skip as e:
        return Finding(SKIP, str(e))
    except (CommandError, OSError, ValueError, KeyError, IndexError, TypeError) as e:
        return Finding(SKIP, f"تعذّر الفحص: {e}")


def health_score(findings: dict[str, Finding]) -> int:
    score = 100
    for f in findings.values():
        score -= {ERROR: 12, WARN: 4}.get(f.status, 0)
    return max(0, score)
