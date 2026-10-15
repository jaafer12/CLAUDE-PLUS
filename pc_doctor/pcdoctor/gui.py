"""واجهة البرنامج (CustomTkinter)."""

from __future__ import annotations

import datetime
import os
import queue
import threading
import time
import tkinter as tk
import webbrowser
from typing import Callable, Optional

import customtkinter as ctk
import psutil

from . import checks, paths, settings, sysinfo, updater
from .checks import ERROR, INFO, OK, SKIP, WARN, Finding
from .system import IS_WINDOWS, create_restore_point, is_admin, relaunch_as_admin
from .version import APP_NAME, __version__

DAY = 24 * 3600
FAMILY = "Segoe UI" if IS_WINDOWS else "DejaVu Sans"
RLM = "‏"

# الألوان: (الوضع الفاتح، الوضع الداكن)
BG = ("#eef1f7", "#0d1220")
SIDEBAR = ("#ffffff", "#131a2b")
CARD = ("#ffffff", "#182036")
CARD_2 = ("#f5f7fb", "#1f2842")
BORDER = ("#e3e7ef", "#26304a")
TEXT = ("#111827", "#e9edf5")
MUTED = ("#6b7280", "#8d97ad")
ACCENT = ("#2563eb", "#3b82f6")
ACCENT_HOVER = ("#1d4ed8", "#2563eb")
NAV_ACTIVE = ("#e8efff", "#22305a")
STATUS = {
    OK: ("#16a34a", "#22c55e"),
    WARN: ("#d97706", "#f59e0b"),
    ERROR: ("#dc2626", "#ef4444"),
    INFO: ("#0284c7", "#38bdf8"),
    SKIP: ("#94a3b8", "#64748b"),
    "pending": ("#94a3b8", "#64748b"),
    "running": ("#2563eb", "#3b82f6"),
}
STATUS_TEXT = {OK: "سليم", WARN: "تنبيه", ERROR: "خطأ", INFO: "ملاحظة", SKIP: "تخطّي",
               "pending": "بانتظار الفحص", "running": "جارٍ الفحص…"}


def t(s: str) -> str:
    """يجعل النص العربي يُعرض من اليمين (الأرقام وعلامات الترقيم في مكانها الصحيح)."""
    s = s.replace("️", "")
    return f"{RLM}{s}{RLM}" if s else s


def col(pair) -> str:
    return pair[1] if ctk.get_appearance_mode() == "Dark" else pair[0]


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family=FAMILY, size=size, weight=weight)


def label(master, text: str = "", size: int = 13, weight: str = "normal", color=TEXT, wrap: int = 0, **kw):
    return ctk.CTkLabel(master, text=t(text), font=font(size, weight), text_color=color, anchor="e",
                        justify="right", wraplength=wrap, **kw)


def button(master, text: str, command: Callable, primary: bool = True, width: int = 140, height: int = 36, **kw):
    if primary:
        style = dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff")
    else:
        style = dict(fg_color=CARD_2, hover_color=BORDER, text_color=TEXT, border_width=1, border_color=BORDER)
    style.update(kw)
    return ctk.CTkButton(master, text=t(text), command=command, font=font(13, "bold"), width=width, height=height,
                         corner_radius=10, **style)


def card(master, **kw):
    return ctk.CTkFrame(master, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER, **kw)


# ==================================================================== حلقة الصحة

class HealthRing(tk.Canvas):
    def __init__(self, master, size: int = 190):
        super().__init__(master, width=size, height=size, highlightthickness=0, bd=0)
        self.size = size
        self.score: Optional[int] = None
        self.shown = 0.0
        self.redraw()

    def set_score(self, score: Optional[int]) -> None:
        self.score = score
        self._animate()

    def _animate(self) -> None:
        target = float(self.score or 0)
        if abs(self.shown - target) < 0.6:
            self.shown = target
            self.redraw()
            return
        self.shown += (target - self.shown) * 0.18
        self.redraw()
        self.after(16, self._animate)

    def redraw(self) -> None:
        self.delete("all")
        self.configure(bg=col(CARD))
        s, w = self.size, 16
        pad = w / 2 + 4
        self.create_oval(pad, pad, s - pad, s - pad, outline=col(CARD_2), width=w)
        if self.score is None:
            self.create_text(s / 2, s / 2 - 8, text="؟", fill=col(MUTED), font=(FAMILY, 40, "bold"))
            self.create_text(s / 2, s / 2 + 32, text=t("لم يُفحص بعد"), fill=col(MUTED), font=(FAMILY, 11))
            return
        status = OK if self.score >= 85 else WARN if self.score >= 60 else ERROR
        color = col(STATUS[status])
        extent = -3.599 * self.shown
        if self.shown > 0.5:
            self.create_arc(pad, pad, s - pad, s - pad, start=90, extent=extent, style="arc", outline=color,
                            width=w)
        self.create_text(s / 2, s / 2 - 6, text=f"{self.shown:.0f}", fill=col(TEXT), font=(FAMILY, 44, "bold"))
        self.create_text(s / 2, s / 2 + 34, text=t("من 100"), fill=col(MUTED), font=(FAMILY, 11))


# ==================================================================== بطاقة فحص

class CheckCard(ctk.CTkFrame):
    def __init__(self, master, app: "App", check: checks.Check):
        super().__init__(master, fg_color=CARD, corner_radius=12, border_width=1, border_color=BORDER)
        self.app, self.check = app, check
        self.finding: Optional[Finding] = None
        self.expanded = False

        self.strip = ctk.CTkFrame(self, width=5, height=1, corner_radius=3, fg_color=STATUS["pending"])
        self.strip.pack(side="right", fill="y", padx=(0, 6), pady=10)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="right", fill="both", expand=True, padx=(4, 4), pady=8)

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")
        self.icon = ctk.CTkLabel(top, text=check.icon.replace("️", ""), font=font(24), width=44,
                                 text_color=STATUS["pending"])
        self.icon.pack(side="right", padx=(2, 8))
        texts = ctk.CTkFrame(top, fg_color="transparent")
        texts.pack(side="right", fill="x", expand=True)
        self.title = label(texts, check.title, 14, "bold")
        self.title.pack(fill="x")
        self.summary = label(texts, STATUS_TEXT["pending"], 12, color=MUTED, wrap=560)
        self.summary.pack(fill="x")

        side = ctk.CTkFrame(top, fg_color="transparent")
        side.pack(side="left", padx=(6, 0))
        self.pill = ctk.CTkLabel(side, text=t(STATUS_TEXT["pending"]), font=font(11, "bold"), corner_radius=8,
                                 fg_color=CARD_2, text_color=MUTED, width=92, height=24)
        self.pill.pack(side="right", padx=4)
        self.more = ctk.CTkButton(side, text=t("التفاصيل ▾"), width=88, height=30, corner_radius=8,
                                  font=font(12), fg_color="transparent", hover_color=CARD_2, text_color=MUTED,
                                  command=self.toggle)
        self.fix_btn = button(side, "إصلاح", self.fix, width=130)

        self.details = ctk.CTkFrame(body, fg_color=CARD_2, corner_radius=10)

    def set_state(self, state: str) -> None:
        self.finding = None
        self.strip.configure(fg_color=STATUS[state])
        self.icon.configure(text_color=STATUS[state])
        self.summary.configure(text=t(STATUS_TEXT[state]), text_color=MUTED)
        self.pill.configure(text=t(STATUS_TEXT[state]), text_color=STATUS[state], fg_color=CARD_2)
        self.fix_btn.pack_forget()
        self.more.pack_forget()
        self._collapse()

    def set_fixing(self) -> None:
        self.fix_btn.configure(state="disabled", text=t("جارٍ الإصلاح…"))

    def set_finding(self, f: Finding) -> None:
        self.finding = f
        color = STATUS[f.status]
        self.strip.configure(fg_color=color)
        self.icon.configure(text_color=color)
        self.summary.configure(text=t(f.summary), text_color=TEXT if f.status in (WARN, ERROR) else MUTED)
        self.pill.configure(text=t(STATUS_TEXT[f.status]), text_color="#ffffff" if f.status != SKIP else MUTED,
                            fg_color=color if f.status != SKIP else CARD_2)
        self.fix_btn.pack_forget()
        self.more.pack_forget()
        if f.fix_kind and self.check.fix:
            self.fix_btn.configure(text=t(f.fix_label), state="normal",
                                   **(dict(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                                           border_width=0)
                                      if f.fix_kind == "auto" else
                                      dict(fg_color=CARD_2, hover_color=BORDER, text_color=TEXT, border_width=1)))
            self.fix_btn.pack(side="right", padx=4)
        if f.details or f.advice:
            self.more.pack(side="right", padx=2)
        if self.expanded:
            self._fill_details()

    def toggle(self) -> None:
        if self.expanded:
            self._collapse()
        else:
            self.expanded = True
            self.more.configure(text=t("إخفاء ▴"))
            self._fill_details()
            self.details.pack(fill="x", pady=(8, 2))

    def _collapse(self) -> None:
        self.expanded = False
        self.more.configure(text=t("التفاصيل ▾"))
        self.details.pack_forget()

    def _fill_details(self) -> None:
        for w in self.details.winfo_children():
            w.destroy()
        f = self.finding
        if f is None:
            return
        for line in f.details:
            bullet = line.strip().startswith("•")
            text = line.strip().lstrip("•").strip()
            row = ctk.CTkFrame(self.details, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=1)
            if bullet:
                ctk.CTkLabel(row, text="•", font=font(13), text_color=MUTED, width=14).pack(side="right")
            label(row, text, 12, color=TEXT, wrap=640).pack(side="right", fill="x", expand=True)
        if f.advice:
            tip = ctk.CTkFrame(self.details, fg_color="transparent")
            tip.pack(fill="x", padx=12, pady=(6, 8))
            ctk.CTkLabel(tip, text="💡", font=font(14), width=22).pack(side="right", anchor="n")
            label(tip, f.advice, 12, color=MUTED, wrap=640).pack(side="right", fill="x", expand=True)
        elif f.details:
            ctk.CTkFrame(self.details, fg_color="transparent", height=6).pack()

    def fix(self) -> None:
        self.app.fix(self.check.id)


# ==================================================================== الصفحات

class Page(ctk.CTkFrame):
    def __init__(self, master, app: "App", title: str, subtitle: str = ""):
        super().__init__(master, fg_color="transparent")
        self.app = app
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=28, pady=(22, 10))
        self.head = head
        label(head, title, 24, "bold").pack(fill="x")
        if subtitle:
            label(head, subtitle, 13, color=MUTED).pack(fill="x")

    def on_show(self) -> None:
        pass


class HomePage(Page):
    def __init__(self, master, app: "App"):
        super().__init__(master, app, "مرحباً بك 👋", "افحص حاسبتك، واكتشف المشكلات، وأصلحها بضغطة واحدة.")
        hero = card(self)
        hero.pack(fill="x", padx=28, pady=(4, 14))
        self.ring = HealthRing(hero)
        self.ring.pack(side="right", padx=26, pady=20)
        info = ctk.CTkFrame(hero, fg_color="transparent")
        info.pack(side="right", fill="both", expand=True, pady=20, padx=(0, 10))
        self.status_title = label(info, "لم يُفحص الجهاز بعد", 22, "bold")
        self.status_title.pack(fill="x", pady=(6, 2))
        self.status_text = label(info, "ابدأ فحصاً سريعاً لمعرفة حالة جهازك خلال أقل من دقيقة.", 13, color=MUTED,
                                 wrap=520)
        self.status_text.pack(fill="x")
        btns = ctk.CTkFrame(info, fg_color="transparent")
        btns.pack(fill="x", pady=(18, 4))
        self.b_quick = button(btns, "⚡  فحص سريع", lambda: app.start_scan(False), width=170, height=44)
        self.b_quick.pack(side="right", padx=(0, 10))
        self.b_deep = button(btns, "🔬  فحص شامل", lambda: app.start_scan(True), primary=False, width=170, height=44)
        self.b_deep.pack(side="right")
        label(info, "الفحص الشامل يضيف فحص ملفات النظام والأقراص، ويستغرق وقتاً أطول.", 11, color=MUTED).pack(
            fill="x", pady=(6, 0))

        # مؤشرات حيّة
        label(self, "الأداء الآن", 15, "bold").pack(fill="x", padx=30, pady=(4, 6))
        gauges = ctk.CTkFrame(self, fg_color="transparent")
        gauges.pack(fill="x", padx=22)
        self.gauges = {}
        gauges.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="g")
        for i, (key, icon, name) in enumerate((("cpu", "⚙", "المعالج"), ("ram", "🧠", "الذاكرة"),
                                               ("disk", "💽", "قرص النظام"), ("net", "🌐", "الشبكة"))):
            g = card(gauges)
            g.grid(row=0, column=3 - i, sticky="nsew", padx=6)
            top = ctk.CTkFrame(g, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 0))
            ctk.CTkLabel(top, text=icon, font=font(18), text_color=ACCENT).pack(side="right")
            label(top, name, 13, color=MUTED).pack(side="right", padx=6)
            val = label(g, "—", 22, "bold")
            val.pack(fill="x", padx=14)
            bar = ctk.CTkProgressBar(g, height=8, corner_radius=4, progress_color=ACCENT, fg_color=CARD_2)
            bar.set(0)
            bar.pack(fill="x", padx=14, pady=(2, 4))
            sub = label(g, "", 11, color=MUTED)
            sub.pack(fill="x", padx=14, pady=(0, 10))
            self.gauges[key] = (val, bar, sub)

        # ملخص الفئات
        label(self, "حالة الأقسام", 15, "bold").pack(fill="x", padx=30, pady=(16, 6))
        cats = ctk.CTkFrame(self, fg_color="transparent")
        cats.pack(fill="x", padx=22)
        icons = {"التخزين": "💽", "الأداء": "🚀", "الأمان": "🛡", "النظام": "🧩", "العتاد": "🔌", "الشبكة": "🌐"}
        self.cats = {}
        n = len(checks.CATEGORIES)
        cats.grid_columnconfigure(tuple(range(n)), weight=1, uniform="c")
        for i, name in enumerate(checks.CATEGORIES):
            c = card(cats)
            c.grid(row=0, column=n - 1 - i, sticky="nsew", padx=6)
            ic = ctk.CTkLabel(c, text=icons[name], font=font(22), text_color=STATUS["pending"])
            ic.pack(pady=(12, 0))
            ctk.CTkLabel(c, text=t(name), font=font(13, "bold"), text_color=TEXT).pack()
            st = ctk.CTkLabel(c, text="—", font=font(11), text_color=MUTED)
            st.pack(pady=(0, 12))
            c.bind("<Button-1>", lambda e: app.show("scan"))
            self.cats[name] = (ic, st)

        self._net = (psutil.net_io_counters(), time.time())
        psutil.cpu_percent(None)
        self.after(500, self._tick)

    def _tick(self) -> None:
        try:
            cpu = psutil.cpu_percent(None)
            vm = psutil.virtual_memory()
            sysdrive = (os.environ.get("SystemDrive", "C:") + "\\") if IS_WINDOWS else "/"
            du = psutil.disk_usage(sysdrive)
            net, now = psutil.net_io_counters(), time.time()
            old, t0 = self._net
            dt = max(0.1, now - t0)
            down = (net.bytes_recv - old.bytes_recv) / dt
            up = (net.bytes_sent - old.bytes_sent) / dt
            self._net = (net, now)
            self._gauge("cpu", f"{cpu:.0f}٪", cpu / 100, f"{psutil.cpu_count()} نواة")
            self._gauge("ram", f"{vm.percent:.0f}٪", vm.percent / 100,
                        f"{checks.human(vm.used)} من {checks.human(vm.total)}")
            self._gauge("disk", f"{du.percent:.0f}٪", du.percent / 100, f"متاح {checks.human(du.free)}")
            self._gauge("net", _rate(down), min(1.0, down / (5 * checks.MB)), f"تنزيل · رفع {_rate(up)}")
        except (OSError, psutil.Error):
            pass
        self.after(1500, self._tick)

    def _gauge(self, key: str, value: str, frac: float, sub: str) -> None:
        val, bar, sub_l = self.gauges[key]
        val.configure(text=t(value))
        bar.set(max(0.0, min(1.0, frac)))
        if key != "net":
            status = ERROR if frac >= 0.9 else WARN if frac >= 0.8 else None
            bar.configure(progress_color=STATUS[status] if status else ACCENT)
        sub_l.configure(text=t(sub))

    def set_busy(self, busy: bool) -> None:
        for b in (self.b_quick, self.b_deep):
            b.configure(state="disabled" if busy else "normal")

    def update_summary(self, findings: dict[str, Finding], when: Optional[str], scanning: bool = False) -> None:
        if scanning:
            self.status_title.configure(text=t("جارٍ فحص الجهاز…"))
            self.status_text.configure(text=t("يمكنك متابعة النتائج في صفحة «نتائج الفحص»."))
            return
        if not findings:
            return
        score = checks.health_score(findings)
        self.ring.set_score(score)
        errors = sum(f.status == ERROR for f in findings.values())
        warns = sum(f.status == WARN for f in findings.values())
        if score >= 90 and not errors:
            title = "جهازك بحالة ممتازة ✨"
        elif score >= 75:
            title = "جهازك بحالة جيدة"
        elif score >= 55:
            title = "جهازك يحتاج بعض الإصلاحات"
        else:
            title = "جهازك يحتاج انتباهاً عاجلاً"
        self.status_title.configure(text=t(title))
        parts = []
        if errors:
            parts.append(f"{errors} خطأ")
        if warns:
            parts.append(f"{warns} تنبيه")
        txt = ("وُجد " + " و".join(parts) + ".") if parts else "لم يُعثر على أي مشكلة."
        if when:
            txt += f"  آخر فحص: {when}"
        self.status_text.configure(text=t(txt))
        for name, (ic, st) in self.cats.items():
            fs = [findings[c.id] for c in checks.CHECKS if c.category == name and c.id in findings]
            e = sum(f.status == ERROR for f in fs)
            w = sum(f.status == WARN for f in fs)
            if e:
                ic.configure(text_color=STATUS[ERROR])
                st.configure(text=t(f"{e + w} مشكلة"), text_color=STATUS[ERROR])
            elif w:
                ic.configure(text_color=STATUS[WARN])
                st.configure(text=t(f"{w} تنبيه"), text_color=STATUS[WARN])
            elif fs:
                ic.configure(text_color=STATUS[OK])
                st.configure(text=t("سليم"), text_color=STATUS[OK])

    def on_theme(self) -> None:
        self.ring.redraw()


class ScanPage(Page):
    def __init__(self, master, app: "App"):
        super().__init__(master, app, "نتائج الفحص", "كل فحص يشرح المشكلة وطريقة إصلاحها. اضغط «التفاصيل» لمعرفة المزيد.")
        bar = card(self)
        bar.pack(fill="x", padx=28, pady=(0, 10))
        row = ctk.CTkFrame(bar, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(12, 6))
        self.status = label(row, "لم يبدأ الفحص بعد.", 14, "bold")
        self.status.pack(side="right", fill="x", expand=True)
        self.b_fix_all = button(row, "🛠  إصلاح الكل", app.fix_all, width=150)
        self.b_fix_all.pack(side="left", padx=(0, 8))
        self.b_rescan = button(row, "↻  إعادة الفحص", lambda: app.start_scan(app.last_deep), primary=False,
                               width=140)
        self.b_rescan.pack(side="left")
        self.progress = ctk.CTkProgressBar(bar, height=8, corner_radius=4, progress_color=ACCENT, fg_color=CARD_2)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=16, pady=(4, 6))
        frow = ctk.CTkFrame(bar, fg_color="transparent")
        frow.pack(fill="x", padx=16, pady=(0, 12))
        self.filter = ctk.CTkSegmentedButton(frow, values=[t("المشكلات فقط"), t("الكل")], font=font(12),
                                             command=lambda v: self.refilter(), selected_color=ACCENT,
                                             selected_hover_color=ACCENT_HOVER)
        self.filter.set(t("الكل"))
        self.filter.pack(side="right")
        self.counts = label(frow, "", 12, color=MUTED)
        self.counts.pack(side="left")

        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.headers: dict[str, ctk.CTkLabel] = {}
        self.cards: dict[str, CheckCard] = {}
        for cat in checks.CATEGORIES:
            self.headers[cat] = label(self.list, cat, 15, "bold", color=ACCENT)
            for c in checks.CHECKS:
                if c.category == cat:
                    self.cards[c.id] = CheckCard(self.list, app, c)
        self.refilter()
        self.update_counts({})

    def refilter(self) -> None:
        only_problems = self.filter.get() == t("المشكلات فقط")
        for w in list(self.headers.values()) + list(self.cards.values()):
            w.pack_forget()
        for cat in checks.CATEGORIES:
            visible = [cd for cd in self.cards.values() if cd.check.category == cat and
                       (not only_problems or (cd.finding and cd.finding.status in (WARN, ERROR, INFO)))]
            if not visible:
                continue
            self.headers[cat].pack(fill="x", padx=12, pady=(12, 4))
            for cd in visible:
                cd.pack(fill="x", padx=6, pady=4)

    def update_counts(self, findings: dict[str, Finding]) -> None:
        e = sum(f.status == ERROR for f in findings.values())
        w = sum(f.status == WARN for f in findings.values())
        o = sum(f.status == OK for f in findings.values())
        fixable = sum(1 for f in findings.values() if f.fix_kind == "auto" and f.status in (WARN, ERROR, INFO))
        self.counts.configure(text=t(f"✖ {e} خطأ    ! {w} تنبيه    ✔ {o} سليم") if findings else "")
        self.b_fix_all.configure(text=t(f"🛠  إصلاح الكل ({fixable})"),
                                 state="normal" if fixable and not self.app.busy else "disabled")

    def set_busy(self, busy: bool) -> None:
        self.b_rescan.configure(state="disabled" if busy else "normal")
        for cd in self.cards.values():
            if cd.fix_btn.winfo_ismapped():
                cd.fix_btn.configure(state="disabled" if busy else "normal")
        self.update_counts(self.app.findings)


class InfoPage(Page):
    def __init__(self, master, app: "App"):
        super().__init__(master, app, "معلومات الجهاز", "مواصفات حاسبتك. يمكنك نسخها وإرسالها لمن يساعدك في الصيانة.")
        row = ctk.CTkFrame(self.head, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))
        self.b_copy = button(row, "📋  نسخ المعلومات", self.copy, primary=False, width=160)
        self.b_copy.pack(side="right")
        button(row, "↻  تحديث", self.load, primary=False, width=110).pack(side="right", padx=8)
        self.grid_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True, padx=20, pady=(0, 14))
        self.grid_frame.grid_columnconfigure((0, 1), weight=1, uniform="c")
        self.rows: list[tuple[str, str, str]] = []
        self.loaded = False

    def on_show(self) -> None:
        if not self.loaded:
            self.load()

    def load(self) -> None:
        self.loaded = True
        for w in self.grid_frame.winfo_children():
            w.destroy()
        label(self.grid_frame, "جارٍ جمع المعلومات…", 13, color=MUTED).grid(row=0, column=0, columnspan=2, pady=30)
        q: queue.Queue = queue.Queue()
        threading.Thread(target=lambda: q.put(sysinfo.collect()), daemon=True).start()

        def poll():
            try:
                self.show_rows(q.get_nowait())
            except queue.Empty:
                self.after(150, poll)

        poll()

    def show_rows(self, rows) -> None:
        self.rows = rows
        for w in self.grid_frame.winfo_children():
            w.destroy()
        for i, (icon, name, value) in enumerate(rows):
            c = card(self.grid_frame)
            c.grid(row=i // 2, column=1 - i % 2, sticky="nsew", padx=6, pady=6)
            ctk.CTkLabel(c, text=icon.replace("️", ""), font=font(24), text_color=ACCENT, width=50).pack(
                side="right", padx=(4, 10), pady=12)
            box = ctk.CTkFrame(c, fg_color="transparent")
            box.pack(side="right", fill="both", expand=True, pady=10, padx=(10, 0))
            label(box, name, 12, color=MUTED).pack(fill="x")
            label(box, value, 14, "bold", wrap=330).pack(fill="x")

    def copy(self) -> None:
        text = "\n".join(f"{n}: {v}" for _, n, v in self.rows)
        self.clipboard_clear()
        self.clipboard_append(f"{APP_NAME} {__version__}\n{text}")
        self.app.toast("نُسخت المعلومات.")


class HistoryPage(Page):
    def __init__(self, master, app: "App"):
        super().__init__(master, app, "سجلّ الفحوص", "نتائج الفحوص السابقة والإصلاحات التي نُفِّذت.")
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.list.pack(fill="both", expand=True, padx=20, pady=(0, 14))

    def on_show(self) -> None:
        for w in self.list.winfo_children():
            w.destroy()
        items = settings.load_history()
        if not items:
            label(self.list, "لا توجد فحوص سابقة بعد.", 14, color=MUTED).pack(pady=40)
            return
        for it in items:
            c = card(self.list)
            c.pack(fill="x", padx=6, pady=5)
            score = int(it.get("score", 0))
            status = OK if score >= 85 else WARN if score >= 60 else ERROR
            ctk.CTkLabel(c, text=str(score), font=font(22, "bold"), width=64, height=64, corner_radius=32,
                         fg_color=STATUS[status], text_color="#ffffff").pack(side="right", padx=14, pady=12)
            box = ctk.CTkFrame(c, fg_color="transparent")
            box.pack(side="right", fill="x", expand=True, pady=10)
            mode = "فحص شامل" if it.get("deep") else "فحص سريع"
            label(box, f"{mode} · {it.get('time', '')}", 14, "bold").pack(fill="x")
            label(box, f"{it.get('errors', 0)} خطأ، {it.get('warnings', 0)} تنبيه", 12, color=MUTED).pack(fill="x")
            fixed = it.get("fixed") or []
            if fixed:
                label(box, "أُصلح: " + "، ".join(fixed), 12, color=STATUS[OK], wrap=640).pack(fill="x")


class SettingsPage(Page):
    def __init__(self, master, app: "App"):
        super().__init__(master, app, "الإعدادات")
        cfg = app.cfg
        box = card(self)
        box.pack(fill="x", padx=28, pady=(0, 12))

        def row(title: str, sub: str, widget_fn):
            r = ctk.CTkFrame(box, fg_color="transparent")
            r.pack(fill="x", padx=18, pady=10)
            w = widget_fn(r)
            w.pack(side="left")
            txt = ctk.CTkFrame(r, fg_color="transparent")
            txt.pack(side="right", fill="x", expand=True)
            label(txt, title, 14, "bold").pack(fill="x")
            if sub:
                label(txt, sub, 12, color=MUTED, wrap=520).pack(fill="x")

        themes = {"dark": "داكن", "light": "فاتح", "system": "حسب النظام"}
        rev = {t(v): k for k, v in themes.items()}

        def theme_widget(r):
            seg = ctk.CTkSegmentedButton(r, values=[t(v) for v in reversed(themes.values())], font=font(12),
                                         selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
                                         command=lambda v: app.set_theme(rev[v]))
            seg.set(t(themes.get(cfg.theme, "داكن")))
            return seg

        def switch(attr):
            def make(r):
                var = tk.BooleanVar(value=getattr(cfg, attr))

                def changed():
                    setattr(cfg, attr, var.get())
                    settings.save(cfg)

                return ctk.CTkSwitch(r, text="", variable=var, command=changed, progress_color=ACCENT, width=50)
            return make

        row("المظهر", "", theme_widget)
        row("إنشاء نقطة استعادة قبل الإصلاح", "يُنشئ نقطة استعادة للنظام قبل أول إصلاح يغيّر إعدادات ويندوز، "
            "فيمكنك التراجع عنه من «استعادة النظام».", switch("restore_point"))
        row("الفحص عند فتح البرنامج", "يبدأ فحصاً سريعاً تلقائياً كلما فتحت البرنامج.", switch("scan_on_start"))
        row("التحقق التلقائي من التحديثات", "يتحقق مرة يومياً ويعرض لك الإصدار الجديد وما فيه.", switch("check_updates"))

        box2 = card(self)
        box2.pack(fill="x", padx=28, pady=(0, 12))
        r = ctk.CTkFrame(box2, fg_color="transparent")
        r.pack(fill="x", padx=18, pady=16)
        ctk.CTkLabel(r, text="🩺", font=font(40)).pack(side="right", padx=(0, 12))
        txt = ctk.CTkFrame(r, fg_color="transparent")
        txt.pack(side="right", fill="x", expand=True)
        label(txt, APP_NAME, 18, "bold").pack(fill="x")
        label(txt, f"الإصدار {__version__}", 13, color=MUTED).pack(fill="x")
        btns = ctk.CTkFrame(box2, fg_color="transparent")
        btns.pack(fill="x", padx=18, pady=(0, 16))
        button(btns, "🎉  ما الجديد", lambda: WhatsNew(app, updater.changelog()), primary=False, width=150).pack(
            side="right")
        button(btns, "🔄  التحقق من التحديثات", lambda: app.check_updates(manual=True), width=200).pack(
            side="right", padx=8)
        button(btns, "📂  مجلد البيانات", lambda: _open(paths.data_dir()), primary=False, width=150).pack(side="right")


def _rate(n: float) -> str:
    for unit, size in (("MB/s", checks.MB), ("KB/s", 1024)):
        if n >= size:
            return f"{n / size:.1f} {unit}"
    return f"{n:.0f} B/s"


def _open(path) -> None:
    if IS_WINDOWS:
        os.startfile(str(path))  # type: ignore[attr-defined]
    else:
        webbrowser.open(str(path))


# ==================================================================== النافذة الرئيسية

class App(ctk.CTk):
    def __init__(self, auto_scan: Optional[str] = None):
        self.cfg = settings.load()
        ctk.set_appearance_mode(self.cfg.theme if self.cfg.theme in ("dark", "light", "system") else "dark")
        ctk.set_default_color_theme("blue")
        super().__init__(fg_color=BG)
        self.title(f"{APP_NAME} — الإصدار {__version__}")
        self.geometry("1180x780")
        self.minsize(1020, 680)
        self._set_icon()

        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self.findings: dict[str, Finding] = {}
        self.last_deep = False
        self.last_scan_time: Optional[str] = None
        self.restore_done = False
        self.admin = is_admin()
        self._toast: Optional[ctk.CTkFrame] = None

        self._build_sidebar()
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(side="right", fill="both", expand=True)
        self.pages: dict[str, Page] = {
            "home": HomePage(self.content, self),
            "scan": ScanPage(self.content, self),
            "info": InfoPage(self.content, self),
            "history": HistoryPage(self.content, self),
            "settings": SettingsPage(self.content, self),
        }
        self.current = ""
        self.show("home")
        self._load_last_scan()
        self.after(100, self._poll)
        self.after(400, lambda: self._startup(auto_scan))

    # ------------------------------------------------------------ البناء

    def _set_icon(self) -> None:
        ico = paths.resource_dir() / "app.ico"
        if IS_WINDOWS and ico.exists():
            try:
                self.iconbitmap(default=str(ico))
            except tk.TclError:
                pass

    def _build_sidebar(self) -> None:
        sb = ctk.CTkFrame(self, width=240, fg_color=SIDEBAR, corner_radius=0, border_width=0)
        sb.pack(side="right", fill="y")
        sb.pack_propagate(False)
        logo = ctk.CTkFrame(sb, fg_color="transparent")
        logo.pack(fill="x", padx=18, pady=(24, 26))
        ctk.CTkLabel(logo, text="🩺", font=font(32), text_color=ACCENT).pack(side="right")
        names = ctk.CTkFrame(logo, fg_color="transparent")
        names.pack(side="right", padx=8)
        label(names, APP_NAME, 18, "bold").pack(fill="x")
        label(names, f"الإصدار {__version__}", 11, color=MUTED).pack(fill="x")

        self.nav: dict[str, ctk.CTkButton] = {}
        for key, icon, name in (("home", "🏠", "الرئيسية"), ("scan", "🔍", "نتائج الفحص"),
                                ("info", "💻", "معلومات الجهاز"), ("history", "🕘", "سجلّ الفحوص"),
                                ("settings", "⚙", "الإعدادات")):
            b = ctk.CTkButton(sb, text=t(f"{name}   {icon}"), anchor="e", font=font(14), height=44, corner_radius=10,
                              fg_color="transparent", hover_color=NAV_ACTIVE, text_color=TEXT,
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=12, pady=3)
            self.nav[key] = b

        bottom = ctk.CTkFrame(sb, fg_color="transparent")
        bottom.pack(side="bottom", fill="x", padx=12, pady=16)
        if self.admin:
            ctk.CTkLabel(bottom, text=t("🛡 بصلاحيات المسؤول"), font=font(12, "bold"), text_color=STATUS[OK],
                         fg_color=("#e7f8ee", "#15302a"), corner_radius=10, height=36).pack(fill="x")
        else:
            label(bottom, "بعض الإصلاحات تحتاج صلاحيات المسؤول.", 11, color=MUTED, wrap=210).pack(fill="x", pady=(0, 6))
            button(bottom, "🛡  تشغيل كمسؤول", lambda: self.elevate(""), primary=False, width=210).pack(fill="x")
        self.update_btn = ctk.CTkButton(bottom, text="", font=font(12, "bold"), height=34, corner_radius=10,
                                        fg_color=STATUS[OK], hover_color=STATUS[OK], text_color="#ffffff")

    def show(self, key: str) -> None:
        if key == self.current:
            return
        if self.current:
            self.pages[self.current].pack_forget()
        self.current = key
        self.pages[key].pack(fill="both", expand=True)
        self.pages[key].on_show()
        for k, b in self.nav.items():
            b.configure(fg_color=NAV_ACTIVE if k == key else "transparent",
                        text_color=ACCENT if k == key else TEXT)

    def set_theme(self, theme: str) -> None:
        self.cfg.theme = theme
        settings.save(self.cfg)
        ctk.set_appearance_mode(theme)
        self.after(50, self.pages["home"].on_theme)  # type: ignore[attr-defined]

    def toast(self, text: str, kind: str = OK) -> None:
        if self._toast is not None:
            self._toast.destroy()
        icon = {OK: "✔", WARN: "!", ERROR: "✖"}.get(kind, "ℹ")
        f = ctk.CTkFrame(self, fg_color=CARD, corner_radius=12, border_width=2, border_color=STATUS[kind])
        ctk.CTkLabel(f, text=icon, font=font(16, "bold"), text_color=STATUS[kind]).pack(side="right", padx=(6, 14),
                                                                                         pady=10)
        label(f, text, 13, wrap=560).pack(side="right", padx=(16, 0), pady=10)
        f.place(relx=0.42, rely=0.97, anchor="s")
        f.lift()
        self._toast = f

        def hide(w=f):
            if self._toast is w:
                w.destroy()
                self._toast = None

        self.after(6500, hide)

    # ------------------------------------------------------------ بدء التشغيل

    def _startup(self, auto_scan: Optional[str]) -> None:
        previous = self.cfg.last_seen_version
        if previous != __version__:
            # أول تشغيل بعد التثبيت أو التحديث: نعرض «ما الجديد» مرة واحدة
            news = updater.entries_since(previous)
            self.cfg.last_seen_version = __version__
            settings.save(self.cfg)
            if news:
                WhatsNew(self, news, updated=bool(previous))
        if auto_scan:
            self.start_scan(auto_scan == "deep")
        elif self.cfg.scan_on_start:
            self.start_scan(False)
        if self.cfg.check_updates and time.time() - self.cfg.last_update_check > DAY:
            self.check_updates(manual=False)

    def _load_last_scan(self) -> None:
        hist = settings.load_history()
        if hist:
            last = hist[0]
            self.pages["home"].status_text.configure(  # type: ignore[attr-defined]
                text=t(f"آخر فحص: {last.get('time')} · النتيجة {last.get('score')} من 100. افحص مجدداً لمعرفة الحالة الآن."))

    # ------------------------------------------------------------ الصلاحيات

    def elevate(self, args: str) -> None:
        if relaunch_as_admin(args):
            self.destroy()
        elif not IS_WINDOWS:
            self.toast("التشغيل كمسؤول متاح على ويندوز فقط.", WARN)
        else:
            self.toast("لم يُمنح إذن المسؤول.", WARN)

    # ------------------------------------------------------------ الفحص

    def start_scan(self, deep: bool) -> None:
        if self.busy:
            return
        if deep and not self.admin and IS_WINDOWS:
            choice = Ask(self, "الفحص الشامل", "الفحص الشامل يحتاج صلاحيات المسؤول لفحص ملفات النظام والأقراص.\n"
                         "هل تريد إعادة فتح البرنامج كمسؤول؟", ["إعادة الفتح كمسؤول", "متابعة بدونها", "إلغاء"]).result
            if choice == 0:
                self.elevate("--deep-scan")
                return
            if choice != 1:
                return
        self.last_deep = deep
        self.findings = {}
        self._set_busy(True)
        scan: ScanPage = self.pages["scan"]  # type: ignore[assignment]
        for cd in scan.cards.values():
            cd.set_state("pending")
        scan.refilter()
        scan.progress.set(0)
        scan.status.configure(text=t("جارٍ الفحص…"))
        self.pages["home"].update_summary({}, None, scanning=True)  # type: ignore[attr-defined]
        self.show("scan")

        def work():
            for i, c in enumerate(checks.CHECKS):
                self.events.put(("checking", c.id, i))
                self.events.put(("result", c.id, checks.run_check(c, deep), i + 1))
            self.events.put(("scan_done",))

        threading.Thread(target=work, daemon=True).start()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        self.pages["home"].set_busy(busy)  # type: ignore[attr-defined]
        self.pages["scan"].set_busy(busy)  # type: ignore[attr-defined]

    def _poll(self) -> None:
        scan: ScanPage = self.pages["scan"]  # type: ignore[assignment]
        try:
            while True:
                ev = self.events.get_nowait()
                kind = ev[0]
                if kind == "checking":
                    cd = scan.cards[ev[1]]
                    cd.set_state("running")
                    scan.status.configure(text=t(f"جارٍ فحص: {cd.check.title}…"))
                elif kind == "result":
                    self.findings[ev[1]] = ev[2]
                    scan.cards[ev[1]].set_finding(ev[2])
                    scan.progress.set(ev[3] / len(checks.CHECKS))
                    scan.update_counts(self.findings)
                elif kind == "scan_done":
                    self._scan_done()
                elif kind == "status":
                    scan.status.configure(text=t(ev[1]))
                elif kind == "fixed":
                    self._fixed(ev[1], ev[2], ev[3], ev[4])
                elif kind == "fix_all_done":
                    self._set_busy(False)
                    self._after_fix()
                    if ev[1]:
                        self.toast(ev[1], OK)
                elif kind == "toast":
                    self.toast(ev[1], ev[2])
                elif kind == "update":
                    self._on_update(*ev[1])
        except queue.Empty:
            pass
        self.after(80, self._poll)

    def _scan_done(self) -> None:
        self._set_busy(False)
        scan: ScanPage = self.pages["scan"]  # type: ignore[assignment]
        self.last_scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        errors = sum(f.status == ERROR for f in self.findings.values())
        warns = sum(f.status == WARN for f in self.findings.values())
        score = checks.health_score(self.findings)
        scan.status.configure(text=t(f"انتهى الفحص · النتيجة {score} من 100" +
                                     (f" · {errors} خطأ و{warns} تنبيه" if errors or warns else " · لا مشكلات")))
        scan.refilter()
        self.pages["home"].update_summary(self.findings, self.last_scan_time)  # type: ignore[attr-defined]
        settings.add_history({"time": self.last_scan_time, "score": score, "deep": self.last_deep,
                              "errors": errors, "warnings": warns, "fixed": []})

    # ------------------------------------------------------------ الإصلاح

    def _check(self, cid: str) -> checks.Check:
        return next(c for c in checks.CHECKS if c.id == cid)

    def fix(self, cid: str) -> None:
        if self.busy:
            return
        check, f = self._check(cid), self.findings.get(cid)
        if f is None or check.fix is None:
            return
        if f.confirm and Ask(self, check.title, f.confirm, ["نعم، تابع", "إلغاء"]).result != 0:
            return
        if check.fix_needs_admin and not self.admin and IS_WINDOWS:
            if Ask(self, "يحتاج صلاحيات المسؤول", f"إصلاح «{check.title}» يحتاج صلاحيات المسؤول.\n"
                   "سيُعاد فتح البرنامج كمسؤول ويُفحص الجهاز تلقائياً، ثم اضغط «إصلاح» مرة أخرى.",
                   ["إعادة الفتح كمسؤول", "إلغاء"]).result == 0:
                self.elevate("--scan")
            return
        self._set_busy(True)
        self.pages["scan"].cards[cid].set_fixing()  # type: ignore[attr-defined]
        threading.Thread(target=self._fix_worker, args=([cid], False), daemon=True).start()

    def fix_all(self) -> None:
        if self.busy:
            return
        ids = [cid for cid, f in self.findings.items()
               if f.fix_kind == "auto" and f.status in (WARN, ERROR, INFO) and self._check(cid).fix]
        if not ids:
            return
        need_admin = [cid for cid in ids if self._check(cid).fix_needs_admin]
        if need_admin and not self.admin and IS_WINDOWS:
            names = "، ".join(self._check(c).title for c in need_admin)
            choice = Ask(self, "إصلاح الكل", f"هذه الإصلاحات تحتاج صلاحيات المسؤول: {names}.\n"
                         "يمكنك إعادة فتح البرنامج كمسؤول (سيُفحص الجهاز تلقائياً، ثم اضغط «إصلاح الكل»)، "
                         "أو إصلاح الباقي الآن.",
                         ["إعادة الفتح كمسؤول", "إصلاح الباقي فقط", "إلغاء"]).result
            if choice == 0:
                self.elevate("--scan")
                return
            if choice != 1:
                return
            ids = [c for c in ids if c not in need_admin]
            if not ids:
                return
        # إصلاح المساحة والملفات المؤقتة واحد، فلا نكرّره
        if "junk" in ids and "disk_space" in ids:
            ids.remove("disk_space")
        self._set_busy(True)
        for cid in ids:
            self.pages["scan"].cards[cid].set_fixing()  # type: ignore[attr-defined]
        threading.Thread(target=self._fix_worker, args=(ids, True), daemon=True).start()

    def _fix_worker(self, ids: list[str], batch: bool) -> None:
        ok = 0
        for cid in ids:
            check, f = self._check(cid), self.findings[cid]
            if (check.fix_needs_admin and f.fix_kind == "auto" and self.admin and self.cfg.restore_point
                    and not self.restore_done):
                self.events.put(("status", "جارٍ إنشاء نقطة استعادة للنظام قبل الإصلاح…"))
                err = create_restore_point(f"PCDoctor {__version__}")
                self.restore_done = True
                if err:
                    self.events.put(("toast", f"تعذّر إنشاء نقطة استعادة ({err})، وسيستمر الإصلاح.", WARN))
            self.events.put(("status", f"جارٍ إصلاح: {check.title}… قد يستغرق ذلك بعض الوقت."))
            try:
                msg = check.fix(f)  # type: ignore[misc]
                success = True
                ok += 1
            except Exception as e:  # noqa: BLE001
                msg, success = f"تعذّر الإصلاح: {e}", False
            # نعيد الفحص لنعرض الحالة بعد الإصلاح
            new = checks.run_check(check, self.last_deep) if f.fix_kind == "auto" else f
            self.events.put(("fixed", cid, msg, success, new))
            if cid == "junk" and "disk_space" in self.findings:
                self.events.put(("fixed", "disk_space", "", True,
                                 checks.run_check(self._check("disk_space"), self.last_deep)))
        if batch:
            self.events.put(("fix_all_done", f"انتهى الإصلاح: نجح {ok} من {len(ids)}."))
        else:
            self.events.put(("fix_all_done", ""))

    def _fixed(self, cid: str, msg: str, success: bool, new: Finding) -> None:
        self.findings[cid] = new
        scan: ScanPage = self.pages["scan"]  # type: ignore[assignment]
        scan.cards[cid].set_finding(new)
        if msg:
            self.toast(msg, OK if success else ERROR)
        if success and msg:
            hist = settings.load_history()
            if hist:
                hist[0].setdefault("fixed", [])
                title = self._check(cid).title
                if title not in hist[0]["fixed"]:
                    hist[0]["fixed"].append(title)
                hist[0]["score"] = checks.health_score(self.findings)
                settings.save_history(hist)

    def _after_fix(self) -> None:
        scan: ScanPage = self.pages["scan"]  # type: ignore[assignment]
        score = checks.health_score(self.findings)
        scan.status.configure(text=t(f"النتيجة الآن {score} من 100"))
        scan.update_counts(self.findings)
        self.pages["home"].update_summary(self.findings, self.last_scan_time)  # type: ignore[attr-defined]

    # ------------------------------------------------------------ التحديثات

    def check_updates(self, manual: bool) -> None:
        if manual:
            self.toast("جارٍ التحقق من التحديثات…", INFO)

        def work():
            try:
                self.events.put(("update", (updater.check(), manual, None)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update", (None, manual, e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update(self, upd: Optional[updater.Update], manual: bool, err: Optional[Exception]) -> None:
        if err is not None:
            if manual:
                self.toast(f"تعذّر التحقق من التحديثات. تأكد من الاتصال بالإنترنت. ({err})", WARN)
            return
        self.cfg.last_update_check = time.time()
        settings.save(self.cfg)
        if upd is None:
            if manual:
                self.toast(f"لديك أحدث إصدار ({__version__}).", OK)
            return
        self.update_btn.configure(text=t(f"⬆  تحديث متاح: {upd.version}"), command=lambda: UpdateDialog(self, upd))
        self.update_btn.pack(fill="x", pady=(8, 0))
        if manual or upd.version != self.cfg.skipped_version:
            UpdateDialog(self, upd)


# ==================================================================== النوافذ

class Dialog(ctk.CTkToplevel):
    def __init__(self, master, title: str, width: int, height: int):
        super().__init__(master, fg_color=BG)
        self.title(title)
        self.transient(master)
        self.geometry(f"{width}x{height}")
        self.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - width) // 2
        y = master.winfo_rooty() + (master.winfo_height() - height) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")
        self.bind("<Escape>", lambda e: self.destroy())
        # CTkToplevel على ويندوز يظهر أحياناً خلف النافذة الرئيسية
        self.after(150, self._focus)

    def _focus(self) -> None:
        try:
            self.lift()
            self.focus_force()
            self.grab_set()
        except tk.TclError:
            pass


class Ask(Dialog):
    """سؤال بأزرار؛ result رقم الزر المختار أو None."""

    def __init__(self, master, title: str, text: str, buttons: list[str]):
        super().__init__(master, title, 520, 250)
        self.result: Optional[int] = None
        label(self, title, 18, "bold").pack(fill="x", padx=24, pady=(22, 6))
        label(self, text, 13, color=MUTED, wrap=470).pack(fill="x", padx=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(side="bottom", fill="x", padx=24, pady=20)
        for i, b in enumerate(buttons):
            button(row, b, lambda i=i: self._choose(i), primary=(i == 0), width=150).pack(side="right", padx=(0, 8))
        self.wait_window()

    def _choose(self, i: int) -> None:
        self.result = i
        self.destroy()


class WhatsNew(Dialog):
    """نافذة «ما الجديد»: تُعرض تلقائياً بعد كل تحديث، ومن الإعدادات."""

    def __init__(self, master, entries: list[dict], updated: bool = False):
        super().__init__(master, "ما الجديد", 640, 560)
        hero = ctk.CTkFrame(self, fg_color=ACCENT, corner_radius=0, height=120)
        hero.pack(fill="x")
        ctk.CTkLabel(hero, text="🎉" if updated else "✨", font=font(36), text_color="#ffffff").pack(
            side="right", padx=(0, 24), pady=20)
        box = ctk.CTkFrame(hero, fg_color="transparent")
        box.pack(side="right", fill="x", expand=True, padx=(0, 12), pady=20)
        head = f"تم التحديث إلى الإصدار {__version__}" if updated else f"ما الجديد في {APP_NAME}"
        label(box, head, 20, "bold", color="#ffffff").pack(fill="x")
        label(box, "هذه أهم التغييرات في هذا الإصدار.", 13, color="#dbe7ff").pack(fill="x")

        lst = ctk.CTkScrollableFrame(self, fg_color="transparent")
        lst.pack(fill="both", expand=True, padx=16, pady=12)
        for e in entries:
            c = card(lst)
            c.pack(fill="x", padx=4, pady=6)
            top = ctk.CTkFrame(c, fg_color="transparent")
            top.pack(fill="x", padx=14, pady=(12, 6))
            ctk.CTkLabel(top, text=f"v{e['version']}", font=font(12, "bold"), fg_color=ACCENT, text_color="#ffffff",
                         corner_radius=8, width=70, height=26).pack(side="right")
            label(top, e.get("date", ""), 12, color=MUTED).pack(side="right", padx=10)
            for note in e.get("notes", []):
                row = ctk.CTkFrame(c, fg_color="transparent")
                row.pack(fill="x", padx=14, pady=2)
                ctk.CTkLabel(row, text="✔", font=font(13, "bold"), text_color=STATUS[OK], width=20).pack(
                    side="right", anchor="n", pady=2)
                label(row, note, 13, wrap=520).pack(side="right", fill="x", expand=True, padx=(0, 6))
            ctk.CTkFrame(c, fg_color="transparent", height=8).pack()
        button(self, "رائع، لنبدأ", self.destroy, width=180).pack(pady=(0, 16))


class UpdateDialog(Dialog):
    def __init__(self, master: App, upd: updater.Update):
        super().__init__(master, "تحديث جديد متاح", 560, 460)
        self.app, self.upd = master, upd
        label(self, f"⬆  الإصدار {upd.version} متاح الآن", 20, "bold").pack(fill="x", padx=24, pady=(22, 2))
        label(self, f"الإصدار المثبّت حالياً: {__version__}", 13, color=MUTED).pack(fill="x", padx=24)
        box = ctk.CTkTextbox(self, font=font(13), fg_color=CARD, border_color=BORDER, border_width=1,
                             corner_radius=12, wrap="word")
        box.pack(fill="both", expand=True, padx=24, pady=12)
        notes = upd.notes.strip() or "تحسينات وإصلاحات."
        box.insert("end", "\n".join(t(line.replace("## ", "").replace("### ", "").replace("- ", "• "))
                                    for line in notes.splitlines()))
        box.tag_config("r", justify="right")
        box.tag_add("r", "1.0", "end")
        box.configure(state="disabled")
        self.bar = ctk.CTkProgressBar(self, progress_color=ACCENT, fg_color=CARD_2)
        self.bar.set(0)
        self.bar.pack(fill="x", padx=24)
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=16)
        self.b_now = button(row, "تحديث الآن", self.install, width=140)
        self.b_later = button(row, "لاحقاً", self.destroy, primary=False, width=110)
        self.b_skip = button(row, "تخطّي هذا الإصدار", self.skip, primary=False, width=150)
        for b in (self.b_now, self.b_later, self.b_skip):
            b.pack(side="right", padx=(0, 8))
        if not IS_WINDOWS:
            self.b_now.configure(text=t("فتح صفحة التنزيل"), command=lambda: webbrowser.open(upd.page or upd.url))

    def skip(self) -> None:
        self.app.cfg.skipped_version = self.upd.version
        settings.save(self.app.cfg)
        self.destroy()

    def install(self) -> None:
        for b in (self.b_now, self.b_later, self.b_skip):
            b.configure(state="disabled")
        self.b_now.configure(text=t("جارٍ التنزيل…"))
        q: queue.Queue = queue.Queue()

        def work():
            try:
                q.put(("ok", updater.download(self.upd, lambda f: q.put(("p", f)))))
            except Exception as e:  # noqa: BLE001
                q.put(("err", e))

        def poll():
            try:
                while True:
                    kind, data = q.get_nowait()
                    if kind == "p":
                        self.bar.set(data)
                    elif kind == "ok":
                        updater.run_installer(data)
                        self.app.destroy()
                        return
                    else:
                        self.app.toast(f"فشل تنزيل التحديث: {data}", ERROR)
                        for b in (self.b_now, self.b_later, self.b_skip):
                            b.configure(state="normal")
                        self.b_now.configure(text=t("تحديث الآن"))
                        return
            except queue.Empty:
                pass
            self.after(100, poll)

        threading.Thread(target=work, daemon=True).start()
        poll()


def main(auto_scan: Optional[str] = None) -> None:
    """auto_scan: "quick" أو "deep" لبدء الفحص فور فتح البرنامج (بعد إعادة فتحه كمسؤول مثلاً)."""
    App(auto_scan).mainloop()
