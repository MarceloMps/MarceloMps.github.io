"""Junta os takes na ordem do roteiro em bruto.mp4 e as palavras em words.json.
Uso: python3 juntar.py words_all.json takes/p_1385.mp4 takes/p_1386.mp4 ...
(words_all.json: {"1385": [[ini, fim, palavra], ...], ...}, transcrição de cada take)"""
import json, os, subprocess, sys
allw = json.load(open(sys.argv[1])); files = sys.argv[2:]
dur = lambda f: float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]))
words, off = [], 0.0
for f in files:
    n = os.path.basename(f)[2:-4]
    words += [[round(a + off, 3), round(b + off, 3), w] for a, b, w in allw[n]]
    off += dur(f)
open('lista.txt', 'w').write(''.join(f"file '{f}'\n" for f in files))
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'lista.txt', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast', '-r', '30',
                '-c:a', 'aac', '-b:a', '192k', 'bruto.mp4'], check=True)
json.dump(words, open('words.json', 'w'), ensure_ascii=False)
print(' '.join(f'{i}:{w[2]}' for i, w in enumerate(words)))
