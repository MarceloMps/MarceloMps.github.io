"""Transcreve cada take com tempo por palavra → words_all.json ({"1070": [[ini, fim, palavra], ...]}).
Uso: python3 transcrever_takes.py takes/p_1070.mp4 takes/p_1072.mp4 ...  (pula takes já transcritos)"""
import json, os, subprocess, sys
from faster_whisper import WhisperModel
out = json.load(open('words_all.json')) if os.path.exists('words_all.json') else {}
model = WhisperModel('small', compute_type='int8')
os.makedirs('work', exist_ok=True)
for f in sys.argv[1:]:
    n = os.path.basename(f)[2:-4]
    if n in out: continue
    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', f, '-ac', '1', '-ar', '16000', 'work/a16.wav'], check=True)
    segs, _ = model.transcribe('work/a16.wav', language='pt', word_timestamps=True)
    out[n] = [[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segs for w in s.words]
    json.dump(out, open('words_all.json', 'w'), ensure_ascii=False)
    print(n, ' '.join(w[2] for w in out[n]), flush=True)
