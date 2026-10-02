"""Record the app's English with a natural Google Gemini voice (Gemini 3.8 Flash TTS).

    GEMINI_API_KEY=... python3 tools/gen_voice.py [--limit N] [--workers 4] [--no-verify]

Reads web/app.html and records:
  w/<word>        each lesson word or phrase
  x/<word>        each lesson example sentence
  s/<part>-<n>    each story sentence
  v/<word>        each story "new word" that is not already a lesson word
Clips are MP3 files under web/audio, indexed in web/audio/voice.json (text -> clip).
Existing clips for the same text and voice are kept, so re-running only fills gaps.
Every new clip is transcribed by a Gemini text model and compared with its text;
clips that do not match are deleted so the next run records them again.
The key is read from the environment only. Never commit it.
"""
import base64
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request

TTS_MODEL = "gemini-3.8-flash-tts"
CHECK_MODEL = "gemini-flash-latest"
VOICE = "Sulafat"
BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
NOTES = {
    "word": "Style: a warm, patient English teacher saying one word or short phrase to an adult learner. "
            "Clear standard American accent. Natural, unhurried.",
    "sentence": "Style: a warm, patient English teacher reading to an adult learner. "
                "Clear standard American accent. Calm, slightly slow, natural pace.",
    "story": "Style: a warm storyteller reading a short mystery story to an adult English learner. "
             "Clear standard American accent. Calm, slightly slow pace, natural expression, "
             "a little suspense where it fits.",
}
OUT = "web/audio"
lock = threading.Lock()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]+", " ", s.lower().replace("’", "'"))).strip()


def jobs_from_app():
    html = open("web/app.html", encoding="utf-8").read()
    words = html[html.index("const RAW"):html.index("const CATS")]
    row = re.compile(r"^([^|\n`]+)\|([^|\n]+)\|([^|\n]+)\|([^|\n]+)\|([^|\n]+)\|([^|\n]+)\|([^|\n]+)$", re.M)
    jobs, lesson = [], set()
    for m in row.finditer(words):
        en, ex = m.group(1).strip(), m.group(6).strip()
        lesson.add(en.lower())
        jobs.append((en, f"w/{slug(en)}", "word"))
        jobs.append((ex, f"x/{slug(en)}", "sentence"))
    stories = html[html.index("const STORY_RAW"):html.index("const STORIES")]
    for sm in re.finditer(r"\['([a-z]+)', '[a-z]+', '[^']*', '[^']*', '[^']*', \[(.*?)\n\]\]", stories, re.S):
        sid = sm.group(1)
        for pi, body in enumerate(re.findall(r"`(.*?)`", sm.group(2), re.S), 1):
            n = 0
            for line in body.strip().split("\n"):
                line = line.strip()
                if not line or line.startswith("?"):
                    continue
                en = line.lstrip("= ").split("|")[0].strip()
                if line.startswith("="):
                    if en.lower() not in lesson:
                        jobs.append((en, f"v/{slug(en)}", "word"))
                else:
                    n += 1
                    jobs.append((en, f"s/{sid}-{pi}-{n}", "story"))
    seen, out = set(), []
    for j in jobs:
        if j[0] not in seen:
            seen.add(j[0])
            out.append(j)
    return out


def post(model, body, key, tries=8):
    for attempt in range(tries):
        req = urllib.request.Request(BASE + model + ":generateContent", data=json.dumps(body).encode(),
                                     method="POST", headers={"Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")
            if e.code in (429, 500, 503):
                if "PerDay" in msg:
                    raise RuntimeError("daily quota reached (enable billing or wait until tomorrow)")
                m = re.search(r'"retryDelay":\s*"(\d+)s"', msg)
                wait = int(m.group(1)) + 2 if m else 10 * (attempt + 1)
                time.sleep(wait)
                continue
            raise RuntimeError(f"{e.code}: {msg[:300]}")
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5)
    raise RuntimeError("gave up after retries")


def tts(text, kind, key):
    prompt = f"### DIRECTOR'S NOTES\n{NOTES[kind]}\n\n### TRANSCRIPT\n{text}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
    for _ in range(3):
        d = post(TTS_MODEL, body, key)
        try:
            part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
            return part["mimeType"], base64.b64decode(part["data"])
        except (KeyError, IndexError):
            time.sleep(3)
    raise RuntimeError("no audio in response")


def to_mp3(mime, data, dest):
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "in.raw")
        open(src, "wb").write(data)
        if "wav" in mime.lower():
            inp = ["-i", src]
        else:
            rate = re.search(r"rate=(\d+)", mime)
            inp = ["-f", "s16le", "-ar", rate.group(1) if rate else "24000", "-ac", "1", "-i", src]
        trim = ("silenceremove=start_periods=1:start_silence=0.03:start_threshold=-48dB,areverse,"
                "silenceremove=start_periods=1:start_silence=0.03:start_threshold=-48dB,areverse,"
                "adelay=60,apad=pad_dur=0.12,loudnorm=I=-16:TP=-1.5:LRA=11")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inp, "-af", trim,
                        "-ac", "1", "-ar", "24000", "-b:a", "48k", dest], check=True)
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dest],
                         capture_output=True, text=True, check=True)
    return round(float(out.stdout.strip()), 2)


def save(index):
    tmp = f"{OUT}/voice.json.tmp"
    json.dump(dict(sorted(index.items(), key=lambda kv: kv[1]["clip"])), open(tmp, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    os.replace(tmp, f"{OUT}/voice.json")


def verify(index, key):
    todo = [t for t, v in index.items() if not v.get("ok")]
    bad = []
    for i in range(0, len(todo), 15):
        batch = todo[i:i + 15]
        parts = [{"text": "Transcribe exactly what is spoken in each audio clip, word for word, with no "
                          "corrections. Reply with a JSON list of strings, one per clip, in order."}]
        for t in batch:
            data = open(f"{OUT}/{index[t]['clip']}.mp3", "rb").read()
            parts.append({"inlineData": {"mimeType": "audio/mpeg", "data": base64.b64encode(data).decode()}})
        d = post(CHECK_MODEL, {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json"}}, key)
        heard = json.loads(d["candidates"][0]["content"]["parts"][0]["text"])
        if len(heard) != len(batch):
            print(f"  check skipped a batch ({len(heard)} answers for {len(batch)} clips)")
            continue
        for t, h in zip(batch, heard):
            a, b = norm(t), norm(h)
            if a == b or a.replace("'", "") == b.replace("'", ""):
                index[t]["ok"] = True
            else:
                bad.append((t, h))
        save(index)
    for t, h in bad:
        print(f"  MISMATCH  {index[t]['clip']}: wanted «{t}» heard «{h}»")
        try:
            os.remove(f"{OUT}/{index[t]['clip']}.mp3")
        except FileNotFoundError:
            pass
        del index[t]
    save(index)
    return len(todo) - len(bad), len(bad)


def main():
    key = os.environ.get("GEMINI_API_KEY") or sys.exit("Set GEMINI_API_KEY")
    arg = lambda name, default: type(default)(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default
    limit, workers = arg("--limit", 0), arg("--workers", 4)
    for d in ("w", "x", "s", "v"):
        os.makedirs(f"{OUT}/{d}", exist_ok=True)
    ipath = f"{OUT}/voice.json"
    index = json.load(open(ipath, encoding="utf-8")) if os.path.exists(ipath) else {}

    jobs = jobs_from_app()
    wanted = {t for t, _, _ in jobs}
    for t in [t for t in index if t not in wanted]:  # text removed from the app
        try:
            os.remove(f"{OUT}/{index[t]['clip']}.mp3")
        except FileNotFoundError:
            pass
        del index[t]
    todo = [j for j in jobs if not (index.get(j[0], {}).get("clip") == j[1] and index[j[0]].get("voice") == VOICE
                                    and os.path.exists(f"{OUT}/{j[1]}.mp3"))]
    if limit:
        todo = todo[:limit]
    print(f"{len(jobs)} clips in the app, {len(todo)} to record", flush=True)

    stop = threading.Event()

    def work(job):
        text, clip, kind = job
        if stop.is_set():
            return
        try:
            mime, data = tts(text, kind, key)
            dur = to_mp3(mime, data, f"{OUT}/{clip}.mp3")
        except RuntimeError as e:
            if "daily quota" in str(e):
                stop.set()
            print(f"  FAILED {clip}: {e}", flush=True)
            return
        with lock:
            index[text] = {"clip": clip, "voice": VOICE, "model": TTS_MODEL, "dur": dur}
            save(index)
        print(f"{dur:6.2f}s  {clip:24} {text}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, todo))

    if "--no-verify" not in sys.argv:
        ok, bad = verify(index, key)
        print(f"\nchecked: {ok} match, {bad} removed for re-recording")
    missing = len([j for j in jobs if j[0] not in index])
    print(f"done: {len(index)} clips ready, {missing} still missing")


if __name__ == "__main__":
    main()
