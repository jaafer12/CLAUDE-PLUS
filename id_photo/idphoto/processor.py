"""معالجة الصورة الشخصية إلى صورة رسمية (جواز سفر / مستمسكات عراقية).

المبدأ: الوجه لا يُجمَّل ولا يُنعَّم ولا تُغيَّر ملامحه. كل ما يجري هو:
  1. تعديل ميلان الرأس (تدوير الصورة كلها، لا تشويه للوجه).
  2. فصل الشخص عن الخلفية واستبدالها بأبيض نقي ‎#FFFFFF‎.
  3. إزالة الصبغة الصفراء/الدافئة بتصحيح توازن الأبيض على الصورة كلها.
  4. إضاءة متساوية: رفع الظلال الواسعة على البشرة فقط (ترددات منخفضة)،
     فتبقى المسام والشامات والتفاصيل كما هي.
  5. القصّ والتوسيط بمقاس الصورة الرسمية ثم شحذ خفيف للطباعة.
"""

from __future__ import annotations

import hashlib
import math
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import cv2
import numpy as np
from PIL import Image, ImageOps

from . import paths

_RELEASES = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"


@dataclass(frozen=True)
class SegModel:
    file: str
    url: str
    md5: str
    size: int  # حجم إدخال النموذج (مربّع)
    mb: int
    sigmoid: bool


# سريع ومرفق مع البرنامج
FAST_MODEL = SegModel("u2net_human_seg.onnx", _RELEASES + "u2net_human_seg.onnx",
                      "c09ddc2e0104f800e3e1bb4652583d1f", 320, 176, False)
# أدق بكثير في حواف الشماغ والحجاب والكتفين ويحذف المقاعد والأشياء خلف الشخص،
# يُنزَّل مرة واحدة عند أول استعمال. يحتاج نحو 7 غيغابايت ذاكرة أثناء المعالجة.
HIGH_MODEL = SegModel("birefnet-general-lite.onnx", _RELEASES + "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx",
                      "4fab47adc4ff364be1713e97b7e66334", 1024, 214, True)
HIGH_QUALITY_MIN_RAM_GB = 12


def total_ram_gb() -> float:
    """ذاكرة الجهاز الكلية بالغيغابايت (0 إن تعذّر معرفتها)."""
    try:
        if os.name == "nt":
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

            st = MEMORYSTATUSEX()
            st.dwLength = ctypes.sizeof(st)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
            return st.ullTotalPhys / 2**30
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (OSError, ValueError, AttributeError):
        return 0.0
SEG_MODEL_NAME, SEG_MODEL_URL, SEG_MODEL_MD5 = FAST_MODEL.file, FAST_MODEL.url, FAST_MODEL.md5
FACE_MODEL_NAME = "face_detection_yunet_2023mar.onnx"

WHITE = 255


class PhotoError(Exception):
    """خطأ يُعرض للمستخدم كما هو."""


@dataclass(frozen=True)
class Preset:
    label: str
    width_mm: float
    height_mm: float
    head_ratio: float  # ارتفاع الرأس (أعلاه المقدَّر من الوجه إلى الذقن) ÷ ارتفاع الصورة
    top_ratio: float  # الفراغ فوق الرأس ÷ ارتفاع الصورة


PRESETS: dict[str, Preset] = {
    "iraq_passport": Preset("جواز سفر عراقي 3.5×4.5 سم", 35, 45, 0.60, 0.10),
    "iraq_4x6": Preset("مستمسكات رسمية 4×6 سم", 40, 60, 0.50, 0.11),
    "iraq_3x4": Preset("صورة 3×4 سم", 30, 40, 0.58, 0.11),
}


@dataclass
class Options:
    preset: str = "iraq_passport"
    dpi: int = 600
    straighten: bool = True
    remove_yellow: bool = True
    even_lighting: bool = True
    sharpen: bool = True
    high_quality: bool = False  # نموذج BiRefNet (أبطأ وأدق، يحتاج ذاكرة كبيرة)


@dataclass
class Result:
    image: Image.Image  # الصورة النهائية RGB
    dpi: int
    preset: Preset
    warnings: list[str]


ProgressFn = Callable[[str], None]


# ---------------------------------------------------------------- النماذج

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_ready(model: SegModel) -> bool:
    return (paths.models_dir() / model.file).exists() or (paths.data_dir() / "models" / model.file).exists()


def _model_path(model: SegModel, progress: ProgressFn) -> Path:
    bundled = paths.models_dir() / model.file
    if bundled.exists():
        return bundled
    cached = paths.data_dir() / "models" / model.file
    if cached.exists():
        return cached
    cached.parent.mkdir(parents=True, exist_ok=True)
    tmp = cached.with_suffix(".part")
    last = [-1]

    def hook(blocks, block_size, total):
        if total > 0:
            pct = min(100, blocks * block_size * 100 // total)
            if pct != last[0]:
                last[0] = pct
                progress(f"تنزيل نموذج القصّ عالي الدقة لمرة واحدة فقط ({model.mb} ميغابايت): {pct}%")

    urllib.request.urlretrieve(model.url, tmp, hook)
    progress("التحقق من النموذج…")
    if _md5(tmp) != model.md5:
        tmp.unlink(missing_ok=True)
        raise PhotoError("نموذج إزالة الخلفية الذي نُزّل تالف. أعد المحاولة.")
    tmp.replace(cached)
    return cached


class _Models:
    seg: dict = {}
    face = None

    @classmethod
    def load(cls, progress: ProgressFn, model: SegModel = FAST_MODEL) -> None:
        if model.file not in cls.seg:
            import onnxruntime as ort

            path = _model_path(model, progress)
            progress("تحميل نموذج إزالة الخلفية…")
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            # بلا ذاكرة احتياطية دائمة: تُعاد الذاكرة للنظام بعد كل صورة
            opts.enable_cpu_mem_arena = False
            opts.enable_mem_pattern = False
            if model is HIGH_MODEL:  # أقل ذروة ذاكرة وأسرع لهذا النموذج على المعالج
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
            cls.seg[model.file] = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
        if cls.face is None:
            cls.face = cv2.FaceDetectorYN.create(
                str(paths.models_dir() / FACE_MODEL_NAME), "", (320, 320), 0.7, 0.3, 5000
            )


# ---------------------------------------------------------------- كشف الوجه

@dataclass
class Face:
    box: np.ndarray  # x, y, w, h
    right_eye: np.ndarray  # عين الشخص اليمنى (يسار الصورة)
    left_eye: np.ndarray
    nose: np.ndarray
    mouth_r: np.ndarray
    mouth_l: np.ndarray

    @property
    def eye_center(self) -> np.ndarray:
        return (self.right_eye + self.left_eye) / 2

    @property
    def roll_deg(self) -> float:
        d = self.left_eye - self.right_eye
        return math.degrees(math.atan2(d[1], d[0]))


def _detect_face(rgb: np.ndarray) -> Face:
    h, w = rgb.shape[:2]
    # YuNet أسرع وأدق على صور بحجم معقول
    scale = min(1.0, 1280 / max(h, w))
    small = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else rgb
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    _Models.face.setInputSize((bgr.shape[1], bgr.shape[0]))
    _, faces = _Models.face.detect(bgr)
    if faces is None or len(faces) == 0:
        raise PhotoError("لم يُعثر على وجه في الصورة. استخدم صورة أمامية واضحة للوجه.")
    f = max(faces, key=lambda r: r[2] * r[3]) / scale
    pts = f[4:14].reshape(5, 2)
    return Face(f[0:4].copy(), pts[0], pts[1], pts[2], pts[3], pts[4])


def _estimate_roll(rgb: np.ndarray, face: Face, limit: float = 25) -> float:
    """ميلان الرأس بالدرجات، من تناظر الوجه.

    نقاط العينين وحدها غير موثوقة (النظارات، الحواجب الكثيفة، العيون شبه المغمضة)،
    أما الوجه وغطاء الرأس فمتناظران حول محور عمودي. ندوّر قصاصة الوجه بزوايا متعددة
    ونختار الزاوية التي يتطابق عندها نصفا الوجه أكثر ما يمكن.
    """
    x, y, w, h = face.box
    c = (face.eye_center + face.nose) / 2
    r = int(max(w, h) * 0.75)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gray = cv2.copyMakeBorder(gray, 2 * r, 2 * r, 2 * r, 2 * r, cv2.BORDER_REPLICATE)
    cx, cy = float(c[0] + 2 * r), float(c[1] + 2 * r)
    size = 128

    def score(ang: float) -> float:
        m = cv2.getRotationMatrix2D((cx, cy), ang, size / (2 * r))
        m[0, 2] += size / 2 - cx
        m[1, 2] += size / 2 - cy
        im = cv2.GaussianBlur(cv2.warpAffine(gray, m, (size, size)), (0, 0), 1.5)
        mag = np.hypot(cv2.Sobel(im, cv2.CV_32F, 1, 0), cv2.Sobel(im, cv2.CV_32F, 0, 1))
        best = -1.0
        for dx in range(-6, 7, 2):  # محور التناظر قد لا يمرّ بالضبط بمنتصف القصاصة
            a = mag[16:112, 24 + dx:104 + dx]
            a = a - a.mean()
            b = a[:, ::-1]
            best = max(best, float((a * b).sum() / ((a * a).sum() + 1e-6)))
        return best

    angles = np.arange(-limit, limit + 0.5, 1.0)
    scores = np.array([score(a) for a in angles])
    i = int(np.argmax(scores))
    if 0 < i < len(angles) - 1:  # دقة أقل من درجة بملاءمة قطع مكافئ
        s0, s1, s2 = scores[i - 1:i + 2]
        den = s0 - 2 * s1 + s2
        if den < 0:
            return float(angles[i] + 0.5 * (s0 - s2) / den)
    return float(angles[i])


# ---------------------------------------------------------------- فصل الخلفية

def _box_filter(x: np.ndarray, r: int) -> np.ndarray:
    return cv2.boxFilter(x, -1, (2 * r + 1, 2 * r + 1), borderType=cv2.BORDER_REFLECT)


def _guided_filter(guide: np.ndarray, src: np.ndarray, r: int, eps: float) -> np.ndarray:
    """مرشّح موجَّه (He et al.) يجعل حافة القناع تتبع حواف الصورة الحقيقية (الشعر، الحجاب)."""
    mean_i = _box_filter(guide, r)
    mean_p = _box_filter(src, r)
    cov_ip = _box_filter(guide * src, r) - mean_i * mean_p
    var_i = _box_filter(guide * guide, r) - mean_i * mean_i
    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    return _box_filter(a, r) * guide + _box_filter(b, r)


def _segment(rgb: np.ndarray, model: SegModel = FAST_MODEL) -> np.ndarray:
    """قناع الشخص بقيم 0..1 بحجم الصورة."""
    h, w = rgb.shape[:2]
    n = model.size
    interp = cv2.INTER_AREA if max(h, w) > n else cv2.INTER_CUBIC
    im = cv2.resize(rgb, (n, n), interpolation=interp).astype(np.float32)
    im /= max(float(im.max()), 1e-6)
    im = (im - (0.485, 0.456, 0.406)) / (0.229, 0.224, 0.225)
    inp = im.transpose(2, 0, 1)[None].astype(np.float32)
    seg = _Models.seg[model.file]
    pred = seg.run(None, {seg.get_inputs()[0].name: inp})[0][0, 0].astype(np.float32)
    if model.sigmoid:
        pred = 1 / (1 + np.exp(-pred))
    pred = (pred - pred.min()) / max(float(pred.max() - pred.min()), 1e-6)
    mask = cv2.resize(pred, (w, h), interpolation=cv2.INTER_CUBIC)

    # حافة دقيقة تتبع الصورة الأصلية
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    r = max(2, int(round(max(h, w) / n)))
    mask = _guided_filter(gray, mask, r, 1e-3)
    return np.clip(mask, 0, 1)


def _keep_person(mask: np.ndarray, face: Face) -> np.ndarray:
    """يحذف أي بقع منفصلة عن الشخص (أشياء في الخلفية) ويملأ الثقوب داخله."""
    binary = (mask > 0.5).astype(np.uint8)
    n, labels = cv2.connectedComponents(binary)
    if n > 2:
        cx, cy = face.eye_center.astype(int)
        cy = int(np.clip(cy, 0, mask.shape[0] - 1))
        cx = int(np.clip(cx, 0, mask.shape[1] - 1))
        keep = labels[cy, cx]
        if keep == 0:
            keep = 1 + int(np.argmax(np.bincount(labels.ravel())[1:]))
        person = labels == keep
        # تلاشٍ ناعم عند حواف البقع المحذوفة بدلاً من قطع حاد
        far = cv2.dilate(person.astype(np.uint8), np.ones((15, 15), np.uint8)).astype(bool)
        mask = np.where(far, mask, 0)
        mask = np.where(person | (labels == 0), mask, 0)
    # ملء الثقوب: كل ما لا يتصل بحافة الصورة من الخلفية يُعدّ جزءاً من الشخص
    bg = (mask < 0.5).astype(np.uint8)
    n, labels = cv2.connectedComponents(bg)
    border = set(np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])))
    holes = ~np.isin(labels, list(border)) & (bg > 0)
    mask = np.where(holes, 1.0, mask)
    return mask.astype(np.float32)


def _decontaminate(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """يزيل لون الخلفية القديمة العالق في حواف الشعر والحجاب."""
    inner = (alpha > 0.95).astype(np.float32)
    sigma = max(2.0, max(alpha.shape) / 400)
    num = cv2.GaussianBlur(rgb * inner[..., None], (0, 0), sigma)
    den = cv2.GaussianBlur(inner, (0, 0), sigma)[..., None]
    est = num / np.maximum(den, 1e-4)
    edge = ((alpha > 0.02) & (alpha <= 0.95) & (den[..., 0] > 1e-3))[..., None]
    return np.where(edge, est, rgb)


# ---------------------------------------------------------------- الألوان والإضاءة

def _srgb_to_lin(x: np.ndarray) -> np.ndarray:
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def _lab(rgb01: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(rgb01.astype(np.float32), cv2.COLOR_RGB2LAB)


def _skin_mask(rgb01: np.ndarray, face: Face, alpha: np.ndarray) -> np.ndarray:
    """بشرة الوجه والرقبة: بكسلات قريبة لوناً من وسط الوجه (بلا عيون أو حواجب أو حجاب)."""
    h, w = alpha.shape
    x, y, bw, bh = face.box
    lab = _lab(rgb01)
    # عيّنة من الخدّين والأنف
    cx, cy = face.nose
    sample = np.zeros((h, w), np.uint8)
    cv2.ellipse(sample, (int(cx), int(cy)), (max(1, int(bw * 0.28)), max(1, int(bh * 0.18))), 0, 0, 360, 1, -1)
    pts = lab[sample.astype(bool)]
    if len(pts) < 50:
        return np.zeros((h, w), np.float32)
    med = np.median(pts, axis=0)
    dist_ab = np.hypot(lab[..., 1] - med[1], lab[..., 2] - med[2])
    dist_l = np.abs(lab[..., 0] - med[0])
    region = np.zeros((h, w), np.uint8)
    cv2.rectangle(region, (int(x - bw * 0.3), int(y - bh * 0.2)), (int(x + bw * 1.3), int(y + bh * 1.6)), 1, -1)
    skin = (dist_ab < 9) & (dist_l < 28) & region.astype(bool) & (alpha > 0.9)
    skin = cv2.morphologyEx(skin.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    return cv2.GaussianBlur(skin.astype(np.float32), (0, 0), max(1.0, bw / 60))


def _apply_gains(lin: np.ndarray, gains: np.ndarray) -> np.ndarray:
    # الحفاظ على السطوع: تُطبَّع المضاعفات بحسب معاملات الإضاءة
    gains = gains / float(np.dot(gains, (0.2126, 0.7152, 0.0722)))
    return lin * gains


def _remove_color_cast(rgb01: np.ndarray, face: Face, alpha: np.ndarray, warn: list[str]) -> np.ndarray:
    lin = _srgb_to_lin(rgb01)
    lab = _lab(rgb01)
    h, w = alpha.shape

    # (1) الأسطح الرمادية/البيضاء في الصورة (جدار، قميص، حجاب أبيض) تكشف لون الإضاءة
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    neutral = (chroma < 18) & (lab[..., 0] > 25) & (lab[..., 0] < 97)
    x, y, bw, bh = face.box.astype(int)
    neutral[max(0, y - bh // 2): y + bh * 2, max(0, x - bw // 3): x + bw + bw // 3] = False
    if neutral.sum() > 0.02 * h * w:
        mean = lin[neutral].mean(axis=0)
        g = mean.mean() / np.maximum(mean, 1e-4)
        gains = np.clip(1 + 0.7 * (g - 1), 0.8, 1.3)
        lin = _apply_gains(lin, gains)

    # (2) حارس البشرة: إن بقيت البشرة مائلة إلى الأصفر نرفع الأزرق تدريجياً
    target = 61.0  # زاوية لون البشرة الطبيعية في فضاء Lab تقع تقريباً بين 45° و62°
    skin = _skin_mask(_lin_to_srgb(lin), face, alpha) > 0.5
    if skin.sum() >= 100:
        pix = lin[skin][None]  # نحسب على بكسلات البشرة فقط لسرعة البحث

        def hue(gains):
            lab = _lab(_lin_to_srgb(_apply_gains(pix, gains)))[0]
            return math.degrees(math.atan2(np.median(lab[:, 2]), np.median(lab[:, 1])))

        def gains_for(t):
            return np.array([t ** 0.35, 1.0, t])

        if hue(np.ones(3)) > target:
            lo, hi = 1.0, 1.6
            for _ in range(16):
                t = (lo + hi) / 2
                lo, hi = (t, hi) if hue(gains_for(t)) > target else (lo, t)
            lin = _apply_gains(lin, gains_for(hi))
            if hi >= 1.59:
                warn.append("الصبغة الصفراء في الصورة قوية جداً؛ صُحّح أغلبها. يُفضّل التصوير بإضاءة بيضاء.")
    return _lin_to_srgb(lin).astype(np.float32)


def _even_lighting(rgb01: np.ndarray, face: Face, alpha: np.ndarray) -> np.ndarray:
    """إضاءة ناعمة متساوية: تصحيح التعريض ورفع الظلال الواسعة على البشرة فقط.

    لا تُلمس التفاصيل الدقيقة (المسام، الشامات، الخطوط): التصحيح يُحسب من نسخة
    شديدة التمويه للإضاءة، فيغيّر الإضاءة ولا يغيّر الملمس.
    """
    lab = _lab(rgb01)
    L = lab[..., 0]
    skin = _skin_mask(rgb01, face, alpha)
    sel = skin > 0.5
    if sel.sum() < 100:
        return rgb01

    # (1) التعريض: وسيط سطوع البشرة إلى نطاق طبيعي، بمنحنى غاما على الشخص كله
    med = float(np.median(L[sel]))
    target = float(np.clip(med, 58, 76))
    if abs(target - med) > 1:
        gamma = math.log(target / 100) / math.log(max(med, 1) / 100)
        gamma = float(np.clip(gamma, 0.7, 1.3))
        L = 100 * np.power(np.clip(L / 100, 0, 1), gamma)

    # (2) الظلال: إضاءة البشرة الواسعة (تمويه مُطبَّع لا يخلط البشرة بالحجاب أو الشعر)
    bw = float(face.box[2])
    sigma = max(3.0, bw * 0.18)
    num = cv2.GaussianBlur(L * skin, (0, 0), sigma)
    den = cv2.GaussianBlur(skin, (0, 0), sigma)
    illum = num / np.maximum(den, 1e-3)
    level = float(np.percentile(illum[sel], 75))
    lift = np.clip(0.55 * (level - illum), 0, 14)  # نرفع الظلال فقط، لا نُعتّم شيئاً
    L = L + lift * skin

    lab[..., 0] = np.clip(L, 0, 100)
    out = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return np.clip(out, 0, 1)


def _sharpen(rgb: np.ndarray, dpi: int) -> np.ndarray:
    """شحذ خفيف لقناة السطوع فقط بعد تحجيم الصورة للطباعة."""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    L = lab[..., 0]
    sigma = 1.0 * dpi / 600
    blur = cv2.GaussianBlur(L, (0, 0), sigma)
    detail = L - blur
    detail[np.abs(detail) < 2] = 0  # لا نضخّم الضجيج
    lab[..., 0] = np.clip(L + 0.5 * detail, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)


# ---------------------------------------------------------------- الهندسة

def _rotate(img: np.ndarray, angle: float, center, border_mode) -> np.ndarray:
    m = cv2.getRotationMatrix2D((float(center[0]), float(center[1])), angle, 1.0)
    return cv2.warpAffine(img, m, (img.shape[1], img.shape[0]), flags=cv2.INTER_CUBIC, borderMode=border_mode)


def _head_top(alpha: np.ndarray, face: Face) -> float:
    x, y, bw, bh = face.box
    x0 = int(max(0, x - 0.15 * bw))
    x1 = int(min(alpha.shape[1], x + 1.15 * bw))
    rows = np.where(alpha[: int(y + bh * 0.3), x0:x1].max(axis=1) > 0.5)[0]
    if len(rows) == 0:
        return float(y - 0.35 * bh)
    return float(rows[0])


def _crop_box(alpha: np.ndarray, face: Face, preset: Preset, warn: list[str]):
    """إطار القصّ مبني على الوجه نفسه لا على غطاء الرأس.

    أعلى الرأس يُقدَّر من موضع العينين والذقن، فيبقى حجم الوجه ثابتاً سواء كان الشخص
    حاسر الرأس أو يلبس حجاباً أو شماغاً وعقالاً. ثم يُوسَّع الإطار إن لزم حتى يظهر
    غطاء الرأس كاملاً مع فراغ أبيض فوقه.
    """
    eye_y = float(face.eye_center[1])
    chin = float(face.box[1] + face.box[3])
    crown = eye_y - 0.8 * (chin - eye_y)  # العينان أعلى قليلاً من منتصف الرأس
    out_h = (chin - crown) / preset.head_ratio
    y0 = crown - preset.top_ratio * out_h
    chin_frac = (chin - y0) / out_h

    top = _head_top(alpha, face)  # أعلى الشعر أو غطاء الرأس فعلياً
    margin = 0.04
    if top - y0 < margin * out_h:
        out_h = (chin - top) / (chin_frac - margin)
        y0 = chin - chin_frac * out_h
    out_w = out_h * preset.width_mm / preset.height_mm
    # التوسيط على منتصف الوجه (بين العينين والأنف)
    cx = (face.eye_center[0] + face.nose[0]) / 2
    x0 = cx - out_w / 2
    if top <= 1:
        warn.append("أعلى الرأس مقطوع في الصورة الأصلية؛ صوّر الصورة مع فراغ فوق الرأس.")
    return x0, y0, out_w, out_h


def _crop(img: np.ndarray, x0, y0, w, h, fill) -> np.ndarray:
    """قصّ قد يتجاوز حدود الصورة: فوقها وجانبيها بلون fill، وأسفلها تمتد الملابس."""
    H, W = img.shape[:2]
    x0, y0 = int(round(x0)), int(round(y0))
    w, h = int(round(w)), int(round(h))
    pad_l, pad_t = max(0, -x0), max(0, -y0)
    pad_r, pad_b = max(0, x0 + w - W), max(0, y0 + h - H)
    if pad_b:
        img = cv2.copyMakeBorder(img, 0, pad_b, 0, 0, cv2.BORDER_REPLICATE)
    if pad_l or pad_t or pad_r:
        img = cv2.copyMakeBorder(img, pad_t, 0, pad_l, pad_r, cv2.BORDER_CONSTANT, value=fill)
        x0 += pad_l
        y0 += pad_t
    return img[y0:y0 + h, x0:x0 + w]


# ---------------------------------------------------------------- الواجهة العامة

def load_image(path: str | Path) -> Image.Image:
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img)
    except Exception as e:  # noqa: BLE001
        raise PhotoError(f"تعذّر فتح الصورة: {e}") from e
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img)
    return img.convert("RGB")


def process(img: Image.Image, opts: Options, progress: ProgressFn = lambda s: None) -> Result:
    preset = PRESETS[opts.preset]
    warn: list[str] = []
    model = FAST_MODEL
    if opts.high_quality:
        try:
            _Models.load(progress, HIGH_MODEL)
            model = HIGH_MODEL
        except Exception:  # noqa: BLE001 — بلا إنترنت مثلاً: نكمل بالنموذج السريع
            warn.append("تعذّر تنزيل نموذج القصّ عالي الدقة؛ استُعمل النموذج السريع. تحقّق من الإنترنت وأعد المحاولة.")
    _Models.load(progress, model)

    rgb = np.asarray(img.convert("RGB"))
    # الصور الضخمة تُصغَّر إلى حدّ يكفي لـ 600 نقطة/إنج ويُسرّع المعالجة
    limit = 3200
    if max(rgb.shape[:2]) > limit:
        s = limit / max(rgb.shape[:2])
        rgb = cv2.resize(rgb, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)

    progress("البحث عن الوجه…")
    face = _detect_face(rgb)

    valid = np.ones(rgb.shape[:2], np.float32)  # بكسلات حقيقية (لا حشو من التدوير)
    if opts.straighten:
        angle = _estimate_roll(rgb, face)
        if 0.4 < abs(angle) < 24.5:
            progress("تعديل ميلان الرأس…")
            rgb = _rotate(rgb, angle, face.eye_center, cv2.BORDER_REPLICATE)
            valid = _rotate(valid, angle, face.eye_center, cv2.BORDER_CONSTANT)
            face = _detect_face(rgb)

    progress("إزالة الخلفية…")
    # ما فوق الذقن ويقع في حشو التدوير يصبح خلفية؛ ما تحته (الملابس) يبقى ممتداً
    below = np.arange(rgb.shape[0])[:, None] > face.box[1] + face.box[3]
    outside = (valid < 0.99) & ~below
    if model is HIGH_MODEL:
        progress("إزالة الخلفية بدقة عالية (نحو 20 ثانية)…")
    alpha = _keep_person(np.where(outside, 0, _segment(rgb, model)), face)

    # تمريرة ثانية على منطقة الرأس والكتفين فقط لحواف أدق
    x0, y0, cw, ch = _crop_box(alpha, face, preset, [])
    m = 0.12
    rx0, ry0 = int(max(0, x0 - m * cw)), int(max(0, y0 - m * ch))
    rx1, ry1 = int(min(rgb.shape[1], x0 + cw * (1 + m))), int(min(rgb.shape[0], y0 + ch * (1 + m)))
    if model is FAST_MODEL and (rx1 - rx0) * (ry1 - ry0) < 0.7 * rgb.shape[0] * rgb.shape[1]:
        sub = _segment(rgb[ry0:ry1, rx0:rx1], model)
        first = alpha[ry0:ry1, rx0:rx1]
        # التمريرة الثانية تحسّن الحواف فقط: لا تحذف ما كانت الأولى واثقة منه
        # (مثل أعلى الشماغ الأبيض)، ولا تضيف شيئاً بعيداً عنها
        core = cv2.erode((first > 0.9).astype(np.uint8), np.ones((5, 5), np.uint8)).astype(np.float32)
        near = cv2.dilate(first, np.ones((9, 9), np.uint8))
        refined = alpha.copy()
        refined[ry0:ry1, rx0:rx1] = np.minimum(np.maximum(sub, core), near)
        alpha = _keep_person(np.where(outside, 0, refined), face)

    rgb01 = rgb.astype(np.float32) / 255
    if opts.remove_yellow:
        progress("إزالة الصبغة الصفراء…")
        rgb01 = _remove_color_cast(rgb01, face, alpha, warn)
    if opts.even_lighting:
        progress("توحيد الإضاءة…")
        rgb01 = _even_lighting(rgb01, face, alpha)

    progress("تركيب الخلفية البيضاء…")
    fg = _decontaminate(rgb01, alpha)
    a = alpha[..., None]
    comp = fg * a + (1 - a)
    comp = (np.clip(comp, 0, 1) * 255 + 0.5).astype(np.uint8)
    comp[alpha < 0.02] = WHITE

    progress("القصّ بمقاس الصورة الرسمية…")
    x0, y0, cw, ch = _crop_box(alpha, face, preset, warn)
    crop = _crop(comp, x0, y0, cw, ch, (WHITE, WHITE, WHITE))
    out_w = int(round(preset.width_mm / 25.4 * opts.dpi))
    out_h = int(round(preset.height_mm / 25.4 * opts.dpi))
    interp = cv2.INTER_AREA if crop.shape[0] > out_h else cv2.INTER_LANCZOS4
    if crop.shape[0] < out_h * 0.6:
        warn.append("دقة الصورة الأصلية منخفضة؛ النتيجة قد لا تكون حادّة عند الطباعة.")
    out = cv2.resize(crop, (out_w, out_h), interpolation=interp)

    if opts.sharpen:
        progress("شحذ التفاصيل…")
        out = _sharpen(out, opts.dpi)

    # ضمان أن الخلفية بيضاء نقية ‎#FFFFFF‎ تماماً
    crop_alpha = _crop(alpha, x0, y0, cw, ch, 0)
    crop_alpha = cv2.resize(crop_alpha, (out_w, out_h), interpolation=cv2.INTER_AREA)
    out[crop_alpha < 0.02] = WHITE

    progress("تمّت المعالجة.")
    return Result(Image.fromarray(out), opts.dpi, preset, warn)


def save(result: Result, path: str | Path) -> None:
    path = Path(path)
    fmt = "PNG" if path.suffix.lower() == ".png" else "JPEG"
    kw = {"dpi": (result.dpi, result.dpi)}
    if fmt == "JPEG":
        kw.update(quality=95, subsampling=0)
    result.image.save(path, fmt, **kw)


def print_sheet(result: Result, sheet_mm=(152.4, 101.6), gap_mm: float = 3.0) -> Image.Image:
    """ورقة طباعة 10×15 سم (4×6 إنج) فيها أكبر عدد من النسخ مع خطوط قصّ خفيفة."""
    dpi = result.dpi
    px = lambda mm: int(round(mm / 25.4 * dpi))  # noqa: E731
    sw, sh = px(sheet_mm[0]), px(sheet_mm[1])
    pw, ph = result.image.size
    gap = px(gap_mm)
    cols = max(1, (sw + gap) // (pw + gap))
    rows = max(1, (sh + gap) // (ph + gap))
    sheet = Image.new("RGB", (sw, sh), (255, 255, 255))
    gw = cols * pw + (cols - 1) * gap
    gh = rows * ph + (rows - 1) * gap
    ox, oy = (sw - gw) // 2, (sh - gh) // 2
    arr = np.asarray(sheet).copy()
    for r in range(rows):
        for c in range(cols):
            x, y = ox + c * (pw + gap), oy + r * (ph + gap)
            arr[y:y + ph, x:x + pw] = np.asarray(result.image)
            cv2.rectangle(arr, (x - 1, y - 1), (x + pw, y + ph), (200, 200, 200), 1)
    return Image.fromarray(arr)
