"""يشغّل كل الفحوص (بلا إصلاح) ويطبع نتائجها؛ يفشل إن تعطّل أي فحص.

    python tools/selftest.py [--deep]

يُشغَّل في GitHub Actions على ويندوز للتأكد من أن أوامر PowerShell تعمل.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

from pcdoctor import checks, sysinfo  # noqa: E402
from pcdoctor.system import is_admin  # noqa: E402


def main() -> None:
    deep = "--deep" in sys.argv
    print(f"admin={is_admin()} deep={deep}")
    broken = []
    findings = {}
    for c in checks.CHECKS:
        t0 = time.time()
        f = checks.run_check(c, deep)
        findings[c.id] = f
        print(f"[{f.status:5}] {c.id:15} {time.time() - t0:5.1f}s  {f.summary}  fix={f.fix_kind}")
        for d in f.details[:6]:
            print("                 ", d)
        if f.status == checks.SKIP and f.summary.startswith("تعذّر الفحص"):
            broken.append(c.id)
    print("score:", checks.health_score(findings))
    for icon, name, value in sysinfo.collect():
        print(f"  {name}: {value}")
    if broken:
        sys.exit(f"broken checks: {', '.join(broken)}")


if __name__ == "__main__":
    main()
