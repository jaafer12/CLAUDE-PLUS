"""Record the app's English with Kokoro, a free open-source natural voice (Apache 2.0).

    python3 tools/gen_voice_kokoro.py

Same clips and index as tools/gen_voice.py (web/audio/*, web/audio/voice.json), but no
API key and no quota: the model runs locally on the CPU. Used by the "Record voices"
GitHub Actions workflow. Needs: kokoro, soundfile, numpy, espeak-ng, ffmpeg.
"""
import io
import json
import os
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

sys.path.insert(0, os.path.dirname(__file__))
from gen_voice import OUT, jobs_from_app, save, to_mp3  # noqa: E402

VOICE = "af_heart"
MODEL = "kokoro-82m"
SPEED = {"word": 0.85, "sentence": 0.9, "story": 0.9}


def main():
    for d in ("w", "x", "s", "v"):
        os.makedirs(f"{OUT}/{d}", exist_ok=True)
    ipath = f"{OUT}/voice.json"
    index = json.load(open(ipath, encoding="utf-8")) if os.path.exists(ipath) else {}
    jobs = jobs_from_app()
    wanted = {t for t, _, _ in jobs}
    for t in [t for t in index if t not in wanted]:
        try:
            os.remove(f"{OUT}/{index[t]['clip']}.mp3")
        except FileNotFoundError:
            pass
        del index[t]
    todo = [j for j in jobs if not (index.get(j[0], {}).get("clip") == j[1] and index[j[0]].get("voice") == VOICE
                                    and os.path.exists(f"{OUT}/{j[1]}.mp3"))]
    print(f"{len(jobs)} clips in the app, {len(todo)} to record", flush=True)

    pipe = KPipeline(lang_code="a")
    for n, (text, clip, kind) in enumerate(todo, 1):
        pieces = []
        for result in pipe(text, voice=VOICE, speed=SPEED[kind]):
            audio = result.audio if hasattr(result, "audio") else result[2]
            if audio is not None:
                pieces.append(audio.numpy() if hasattr(audio, "numpy") else np.asarray(audio))
        if not pieces:
            print(f"  FAILED {clip}: no audio", flush=True)
            continue
        buf = io.BytesIO()
        sf.write(buf, np.concatenate(pieces), 24000, format="WAV")
        dur = to_mp3("audio/wav", buf.getvalue(), f"{OUT}/{clip}.mp3")
        index[text] = {"clip": clip, "voice": VOICE, "model": MODEL, "dur": dur}
        if n % 25 == 0 or n == len(todo):
            save(index)
        print(f"{n:4}/{len(todo)} {dur:6.2f}s  {clip:24} {text}", flush=True)
    save(index)
    print(f"done: {len(index)} clips ready")


if __name__ == "__main__":
    main()
