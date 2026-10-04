"""واجهة البرنامج (Tkinter)."""

from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from PIL import Image, ImageTk

from . import paths, processor, settings, updater
from .version import APP_NAME, __version__

FONT = ("Tahoma", 10)
FONT_BOLD = ("Tahoma", 11, "bold")
FONT_TITLE = ("Tahoma", 14, "bold")
PREVIEW = 380
DAY = 24 * 3600
IMAGE_TYPES = [("الصور", "*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.heic"), ("كل الملفات", "*.*")]


class App(tk.Tk):
    def __init__(self, open_path: Optional[str] = None):
        super().__init__()
        self.cfg = settings.load()
        self.title(f"{APP_NAME} — الإصدار {__version__}")
        self.minsize(760, 560)
        self.geometry("980x700")
        self.option_add("*Font", FONT)
        self._set_icon()

        self.source: Optional[Image.Image] = None
        self.source_path: Optional[Path] = None
        self.result: Optional[processor.Result] = None
        self.events: queue.Queue = queue.Queue()
        self.busy = False
        self._previews: dict[str, ImageTk.PhotoImage] = {}

        self._build_menu()
        self._build_body()
        self.after(100, self._poll)
        self.after(300, lambda: self._startup(open_path))

    # ------------------------------------------------------------ البناء

    def _set_icon(self) -> None:
        ico = paths.resource_dir() / "app.ico"
        if os.name == "nt" and ico.exists():
            try:
                self.iconbitmap(default=str(ico))
            except tk.TclError:
                pass

    def _build_menu(self) -> None:
        bar = tk.Menu(self)
        m_file = tk.Menu(bar, tearoff=False)
        m_file.add_command(label="فتح صورة…", accelerator="Ctrl+O", command=self.open_image)
        m_file.add_command(label="حفظ الصورة…", accelerator="Ctrl+S", command=self.save_image)
        m_file.add_command(label="حفظ ورقة طباعة 10×15…", command=self.save_sheet)
        m_file.add_separator()
        m_file.add_command(label="خروج", command=self.destroy)
        bar.add_cascade(label="ملف", menu=m_file)

        m_help = tk.Menu(bar, tearoff=False)
        m_help.add_command(label="ما الجديد", command=lambda: WhatsNew(self, updater.changelog()))
        m_help.add_command(label="التحقق من التحديثات", command=lambda: self.check_updates(manual=True))
        self.var_auto = tk.BooleanVar(value=self.cfg.check_updates)
        m_help.add_checkbutton(label="التحقق التلقائي من التحديثات", variable=self.var_auto,
                               command=self._toggle_auto_update)
        m_help.add_separator()
        m_help.add_command(label="حول البرنامج", command=self.about)
        bar.add_cascade(label="مساعدة", menu=m_help)
        self.config(menu=bar)
        self.bind_all("<Control-o>", lambda e: self.open_image())
        self.bind_all("<Control-s>", lambda e: self.save_image())

    def _build_body(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        # شريط الأزرار (من اليمين إلى اليسار)
        tools = ttk.Frame(root)
        tools.pack(fill="x")
        self.btn_open = ttk.Button(tools, text="📂 فتح صورة", command=self.open_image)
        self.btn_run = ttk.Button(tools, text="✨ معالجة", command=self.run, state="disabled")
        self.btn_save = ttk.Button(tools, text="💾 حفظ الصورة", command=self.save_image, state="disabled")
        self.btn_sheet = ttk.Button(tools, text="🖨 ورقة طباعة", command=self.save_sheet, state="disabled")
        for b in (self.btn_open, self.btn_run, self.btn_save, self.btn_sheet):
            b.pack(side="right", padx=4, ipady=4)

        # الخيارات
        box = ttk.LabelFrame(root, text="الخيارات", padding=8)
        box.pack(fill="x", pady=8)
        opts = ttk.Frame(box)
        opts.pack(fill="x")
        checks = ttk.Frame(box)
        checks.pack(fill="x", pady=(6, 0))
        ttk.Label(opts, text=":المقاس").pack(side="right", padx=(0, 6))
        self.preset_keys = list(processor.PRESETS)
        labels = [processor.PRESETS[k].label for k in self.preset_keys]
        self.var_preset = tk.StringVar(value=processor.PRESETS.get(self.cfg.preset, processor.PRESETS["iraq_passport"]).label)
        cb = ttk.Combobox(opts, values=labels, textvariable=self.var_preset, state="readonly", width=28, justify="right")
        cb.pack(side="right", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._options_changed())

        self.var_yellow = tk.BooleanVar(value=self.cfg.remove_yellow)
        self.var_light = tk.BooleanVar(value=self.cfg.even_lighting)
        self.var_straight = tk.BooleanVar(value=self.cfg.straighten)
        self.var_sharp = tk.BooleanVar(value=self.cfg.sharpen)
        for text, var in (("إزالة الصبغة الصفراء", self.var_yellow), ("إضاءة متساوية", self.var_light),
                          ("تعديل ميلان الرأس", self.var_straight), ("شحذ للطباعة", self.var_sharp)):
            ttk.Checkbutton(checks, text=text, variable=var, command=self._options_changed).pack(side="right", padx=8)

        # المعاينة
        pv = ttk.Frame(root)
        pv.pack(fill="both", expand=True)
        pv.columnconfigure((0, 1), weight=1)
        pv.rowconfigure(1, weight=1)
        ttk.Label(pv, text="النتيجة", font=FONT_BOLD).grid(row=0, column=0)
        ttk.Label(pv, text="الصورة الأصلية", font=FONT_BOLD).grid(row=0, column=1)
        self.cv_result = tk.Canvas(pv, bg="#e9ecef", highlightthickness=0, width=PREVIEW, height=PREVIEW)
        self.cv_source = tk.Canvas(pv, bg="#e9ecef", highlightthickness=0, width=PREVIEW, height=PREVIEW)
        self.cv_result.grid(row=1, column=0, sticky="nsew", padx=6, pady=6)
        self.cv_source.grid(row=1, column=1, sticky="nsew", padx=6, pady=6)
        for cv in (self.cv_result, self.cv_source):
            cv.bind("<Configure>", lambda e: self._redraw())

        # شريط الحالة
        status = ttk.Frame(root)
        status.pack(fill="x")
        self.var_status = tk.StringVar(value="افتح صورة شخصية أمامية للبدء.")
        ttk.Label(status, textvariable=self.var_status, anchor="e", width=1).pack(side="right", fill="x", expand=True)
        self.progress = ttk.Progressbar(status, mode="indeterminate", length=160)
        self.progress.pack(side="left")

    # ------------------------------------------------------------ بدء التشغيل

    def _startup(self, open_path: Optional[str]) -> None:
        previous = self.cfg.last_seen_version
        if previous != __version__:
            # أول تشغيل بعد التثبيت أو التحديث: نعرض «ما الجديد» مرة واحدة
            news = updater.entries_since(previous)
            self.cfg.last_seen_version = __version__
            settings.save(self.cfg)
            if news:
                WhatsNew(self, news, updated=bool(previous))
        if open_path:
            self.load(Path(open_path))
        if self.cfg.check_updates and time.time() - self.cfg.last_update_check > DAY:
            self.check_updates(manual=False)

    # ------------------------------------------------------------ العمليات

    def open_image(self) -> None:
        if self.busy:
            return
        p = filedialog.askopenfilename(title="اختر صورة", filetypes=IMAGE_TYPES,
                                       initialdir=self.cfg.last_dir or str(Path.home()))
        if p:
            self.load(Path(p))

    def load(self, path: Path) -> None:
        try:
            self.source = processor.load_image(path)
        except processor.PhotoError as e:
            messagebox.showerror(APP_NAME, str(e), parent=self)
            return
        self.source_path = path
        self.cfg.last_dir = str(path.parent)
        settings.save(self.cfg)
        self.result = None
        self.btn_run.config(state="normal")
        self.btn_save.config(state="disabled")
        self.btn_sheet.config(state="disabled")
        self._redraw()
        self.run()

    def _read_options(self) -> processor.Options:
        label = self.var_preset.get()
        key = next(k for k in self.preset_keys if processor.PRESETS[k].label == label)
        return processor.Options(preset=key, remove_yellow=self.var_yellow.get(), even_lighting=self.var_light.get(),
                                 straighten=self.var_straight.get(), sharpen=self.var_sharp.get())

    def _options_changed(self) -> None:
        o = self._read_options()
        self.cfg.preset, self.cfg.remove_yellow, self.cfg.even_lighting = o.preset, o.remove_yellow, o.even_lighting
        self.cfg.straighten, self.cfg.sharpen = o.straighten, o.sharpen
        settings.save(self.cfg)
        if self.source is not None and not self.busy:
            self.run()

    def run(self) -> None:
        if self.source is None or self.busy:
            return
        self._set_busy(True)
        opts = self._read_options()
        src = self.source

        def work():
            try:
                res = processor.process(src, opts, lambda s: self.events.put(("status", s)))
                self.events.put(("done", res))
            except processor.PhotoError as e:
                self.events.put(("error", str(e)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("error", f"حدث خطأ غير متوقع أثناء المعالجة:\n{e}"))

        threading.Thread(target=work, daemon=True).start()

    def _poll(self) -> None:
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind == "status":
                    self.var_status.set(data)
                elif kind == "done":
                    self._set_busy(False)
                    self.result = data
                    self.btn_save.config(state="normal")
                    self.btn_sheet.config(state="normal")
                    p = data.preset
                    msg = f"جاهزة: {p.label} — {data.image.width}×{data.image.height} بكسل بدقة {data.dpi} نقطة/إنج."
                    if data.warnings:
                        msg += "  ⚠ " + " ".join(data.warnings)
                    self.var_status.set(msg)
                    self._redraw()
                elif kind == "error":
                    self._set_busy(False)
                    self.var_status.set("تعذّرت المعالجة.")
                    messagebox.showerror(APP_NAME, data, parent=self)
                elif kind == "update":
                    self._on_update(*data)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.btn_open.config(state=state)
        self.btn_run.config(state=state if self.source is not None else "disabled")
        if busy:
            self.btn_save.config(state="disabled")
            self.btn_sheet.config(state="disabled")
            self.progress.start(12)
        else:
            self.progress.stop()

    def _default_name(self, suffix: str) -> str:
        stem = self.source_path.stem if self.source_path else "photo"
        return f"{stem}_{suffix}.jpg"

    def save_image(self) -> None:
        if self.result is None:
            return
        p = filedialog.asksaveasfilename(title="حفظ الصورة", defaultextension=".jpg",
                                         initialdir=self.cfg.last_dir, initialfile=self._default_name("رسمية"),
                                         filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if p:
            processor.save(self.result, p)
            self.var_status.set(f"حُفظت الصورة: {p}")

    def save_sheet(self) -> None:
        if self.result is None:
            return
        p = filedialog.asksaveasfilename(title="حفظ ورقة الطباعة", defaultextension=".jpg",
                                         initialdir=self.cfg.last_dir, initialfile=self._default_name("طباعة_10x15"),
                                         filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")])
        if p:
            sheet = processor.Result(processor.print_sheet(self.result), self.result.dpi, self.result.preset, [])
            processor.save(sheet, p)
            self.var_status.set(f"حُفظت ورقة الطباعة (10×15 سم): {p}")

    # ------------------------------------------------------------ المعاينة

    def _redraw(self) -> None:
        self._draw(self.cv_source, self.source, "source")
        self._draw(self.cv_result, self.result.image if self.result else None, "result")

    def _draw(self, cv: tk.Canvas, img: Optional[Image.Image], key: str) -> None:
        cv.delete("all")
        w, h = max(cv.winfo_width(), 50), max(cv.winfo_height(), 50)
        if img is None:
            cv.create_text(w // 2, h // 2, text="—", fill="#868e96", font=FONT_TITLE)
            return
        im = img.copy()
        im.thumbnail((w - 16, h - 16), Image.LANCZOS)
        self._previews[key] = ImageTk.PhotoImage(im)
        cv.create_rectangle(w // 2 - im.width // 2 - 1, h // 2 - im.height // 2 - 1,
                            w // 2 + im.width // 2 + 1, h // 2 + im.height // 2 + 1, outline="#adb5bd")
        cv.create_image(w // 2, h // 2, image=self._previews[key])

    # ------------------------------------------------------------ التحديثات

    def _toggle_auto_update(self) -> None:
        self.cfg.check_updates = self.var_auto.get()
        settings.save(self.cfg)

    def check_updates(self, manual: bool) -> None:
        if manual:
            self.var_status.set("جارٍ التحقق من التحديثات…")

        def work():
            try:
                self.events.put(("update", (updater.check(), manual, None)))
            except Exception as e:  # noqa: BLE001
                self.events.put(("update", (None, manual, e)))

        threading.Thread(target=work, daemon=True).start()

    def _on_update(self, upd: Optional[updater.Update], manual: bool, err: Optional[Exception]) -> None:
        if err is None:
            self.cfg.last_update_check = time.time()
            settings.save(self.cfg)
        if err is not None:
            if manual:
                self.var_status.set("")
                messagebox.showwarning(APP_NAME, f"تعذّر التحقق من التحديثات. تأكد من الاتصال بالإنترنت.\n\n{err}",
                                       parent=self)
            return
        if upd is None:
            if manual:
                self.var_status.set("")
                messagebox.showinfo(APP_NAME, f"لديك أحدث إصدار ({__version__}).", parent=self)
            return
        if not manual and upd.version == self.cfg.skipped_version:
            return
        UpdateDialog(self, upd)

    def about(self) -> None:
        messagebox.showinfo(
            "حول البرنامج",
            f"{APP_NAME}\nالإصدار {__version__}\n\n"
            "يحوّل الصورة الشخصية إلى صورة رسمية بخلفية بيضاء نقية،\n"
            "مع إزالة الصبغة الصفراء وتوحيد الإضاءة،\n"
            "دون أي تجميل أو تغيير في ملامح الوجه.",
            parent=self,
        )


def _center(win: tk.Toplevel, master: tk.Misc) -> None:
    win.update_idletasks()
    x = master.winfo_rootx() + (master.winfo_width() - win.winfo_width()) // 2
    y = master.winfo_rooty() + (master.winfo_height() - win.winfo_height()) // 3
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


class WhatsNew(tk.Toplevel):
    """نافذة «ما الجديد»: تُعرض تلقائياً بعد كل تحديث، ومن قائمة المساعدة."""

    def __init__(self, master: tk.Misc, entries: list[dict], updated: bool = False):
        super().__init__(master)
        self.title("ما الجديد")
        self.transient(master)
        self.resizable(True, True)
        self.geometry("560x420")

        head = f"🎉 تم التحديث إلى الإصدار {__version__}" if updated else f"ما الجديد في {APP_NAME}"
        ttk.Label(self, text=head, font=FONT_TITLE, anchor="e").pack(fill="x", padx=16, pady=(14, 6))

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=16)
        text = tk.Text(frame, wrap="word", relief="flat", bg=self.cget("bg"), font=FONT, padx=6, pady=6)
        sb = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")
        text.pack(side="right", fill="both", expand=True)
        text.tag_configure("rtl", justify="right")
        text.tag_configure("ver", font=FONT_BOLD, justify="right", spacing1=10, spacing3=4)
        for e in entries:
            text.insert("end", f"الإصدار {e['version']}  ·  {e.get('date', '')}\n", ("ver",))
            for note in e.get("notes", []):
                text.insert("end", f"{note} •\n", ("rtl",))
        text.configure(state="disabled")

        ttk.Button(self, text="حسناً", command=self.destroy).pack(pady=12, ipadx=20)
        self.bind("<Return>", lambda e: self.destroy())
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, master)
        self.grab_set()
        self.focus_set()


class UpdateDialog(tk.Toplevel):
    def __init__(self, master: App, upd: updater.Update):
        super().__init__(master)
        self.app, self.upd = master, upd
        self.title("تحديث جديد متاح")
        self.transient(master)
        self.geometry("520x400")

        ttk.Label(self, text=f"الإصدار {upd.version} متاح الآن", font=FONT_TITLE, anchor="e").pack(fill="x", padx=16, pady=(14, 2))
        ttk.Label(self, text=f"الإصدار المثبّت حالياً: {__version__}", anchor="e").pack(fill="x", padx=16)

        text = tk.Text(self, wrap="word", height=10, relief="flat", bg=self.cget("bg"), font=FONT)
        text.tag_configure("rtl", justify="right")
        text.insert("end", upd.notes.strip() or "تحسينات وإصلاحات.", ("rtl",))
        text.configure(state="disabled")
        text.pack(fill="both", expand=True, padx=16, pady=8)

        self.bar = ttk.Progressbar(self, mode="determinate", maximum=1.0)
        self.bar.pack(fill="x", padx=16)
        btns = ttk.Frame(self)
        btns.pack(pady=12)
        self.b_now = ttk.Button(btns, text="تحديث الآن", command=self.install)
        self.b_later = ttk.Button(btns, text="لاحقاً", command=self.destroy)
        self.b_skip = ttk.Button(btns, text="تخطّي هذا الإصدار", command=self.skip)
        for b in (self.b_now, self.b_later, self.b_skip):
            b.pack(side="right", padx=6)
        if os.name != "nt":
            self.b_now.config(text="فتح صفحة التنزيل", command=lambda: webbrowser.open(upd.page or upd.url))
        self.bind("<Escape>", lambda e: self.destroy())
        _center(self, master)
        self.grab_set()

    def skip(self) -> None:
        self.app.cfg.skipped_version = self.upd.version
        settings.save(self.app.cfg)
        self.destroy()

    def install(self) -> None:
        for b in (self.b_now, self.b_later, self.b_skip):
            b.config(state="disabled")
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
                        self.bar["value"] = data
                    elif kind == "ok":
                        updater.run_installer(data)
                        self.app.destroy()
                        return
                    else:
                        messagebox.showerror(APP_NAME, f"فشل تنزيل التحديث:\n{data}", parent=self)
                        for b in (self.b_now, self.b_later, self.b_skip):
                            b.config(state="normal")
                        return
            except queue.Empty:
                pass
            self.after(100, poll)

        threading.Thread(target=work, daemon=True).start()
        poll()


def main(open_path: Optional[str] = None) -> None:
    App(open_path).mainloop()
