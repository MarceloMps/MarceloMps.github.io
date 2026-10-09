"""Divide cada tomada de narração (takes/<take>.wav) nas falas de narracao.txt.

Alinha a transcrição (faster-whisper, com tempo por palavra) ao texto esperado,
corta entre as falas preservando as pausas naturais e grava:
  vo/<id>.wav          uma fala por arquivo (48 kHz, mono)
  vo_durations.js      window.VODUR (duração) e window.VOWORDS (início/fim de
                       cada palavra, relativo ao início da fala)
"""
import difflib, json, os, re, wave
import numpy as np
from faster_whisper import WhisperModel

SR = 48000
norm = lambda w: re.sub(r"[^\w]", "", w.lower())
texts = dict(l.rstrip("\n").split("|", 1) for l in open("narracao.txt", encoding="utf-8") if "|" in l)
takes = [(t, ids.split()) for t, ids in (l.rstrip("\n").split("|", 1) for l in open("takes.txt") if "|" in l)]


def read(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1, p
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)


def write(p, a):
    with wave.open(p, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.astype(np.int16).tobytes())


model = WhisperModel("small", compute_type="int8")
os.makedirs("vo", exist_ok=True)
VODUR, VOWORDS = {}, {}
for take, ids in takes:
    path = f"takes/{take}.wav"
    if not os.path.exists(path):
        continue
    audio = read(path)
    dur = len(audio) / SR
    segs, _ = model.transcribe(path, language="pt", word_timestamps=True)
    got = [(norm(w.word), w.start, w.end) for s in segs for w in s.words if norm(w.word)]
    exp, owner = [], []
    for i in ids:
        toks = [norm(x) for x in texts[i].split() if norm(x)]
        exp += toks; owner += [i] * len(toks)
    times = [None] * len(exp)
    sm = difflib.SequenceMatcher(a=exp, b=[g[0] for g in got], autojunk=False)
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            times[a + k] = [got[b + k][1], got[b + k][2]]
    # interpola palavras não reconhecidas
    known = [k for k, t in enumerate(times) if t]
    for k in range(len(times)):
        if times[k] is None:
            lo = max([j for j in known if j < k], default=None)
            hi = min([j for j in known if j > k], default=None)
            a0 = times[lo][1] if lo is not None else 0.0
            b0 = times[hi][0] if hi is not None else dur
            span = (hi if hi is not None else len(times)) - (lo if lo is not None else -1)
            f = (k - (lo if lo is not None else -1)) / span
            s = a0 + (b0 - a0) * f
            times[k] = [s, min(b0, s + .25)]
    print(take, f"{len(known)}/{len(exp)} palavras alinhadas")
    cuts = [max(0.0, times[0][0] - .12)]
    for n in range(1, len(ids)):
        last = max(k for k, o in enumerate(owner) if o == ids[n - 1])
        first = min(k for k, o in enumerate(owner) if o == ids[n])
        e, s = times[last][1], times[first][0]
        cuts.append((e + s) / 2 if s > e else s - .02)
    cuts.append(min(dur, times[-1][1] + .3))
    for n, i in enumerate(ids):
        a, b = cuts[n], cuts[n + 1]
        write(f"vo/{i}.wav", audio[int(a * SR):int(b * SR)])
        VODUR[i] = round(b - a, 3)
        VOWORDS[i] = [[round(t[0] - a, 3), round(t[1] - a, 3)] for t, o in zip(times, owner) if o == i]
open("vo_durations.js", "w").write("window.VODUR=" + json.dumps(VODUR) + ";\nwindow.VOWORDS=" + json.dumps(VOWORDS) + ";\n")
print(json.dumps(VODUR))
