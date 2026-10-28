"""Corta as pausas do vídeo bruto e gera o painel 1036x1380 com zoom alternado.

Uso: python3 cortar.py bruto.mp4 words.json [índices a remover, separados por vírgula]
Saída: work/painel.mp4 (vídeo + áudio, cortes nas pausas), work/voz.wav (48 kHz mono)
       e words_cut.js (window.WORDS = [[início, fim, palavra], ...] na nova linha do tempo).
"""
import json, os, subprocess, sys

src, wj = sys.argv[1], sys.argv[2]
W = json.load(open(wj))
DROP = set(int(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else set()
GAP, PRE, POST = .30, .08, .12
words = [w for i, w in enumerate(W) if i not in DROP]
idx = [i for i in range(len(W)) if i not in DROP]
# intervalos de fala: junta palavras com pausa curta; corta pausas longas e trechos removidos
segs = []
for k, (a, b, _) in enumerate(words):
    a, b = max(0, a - PRE), b + POST
    if segs and a - segs[-1][1] < GAP - PRE - POST + .05 and idx[k] - 1 not in DROP:
        segs[-1][1] = max(segs[-1][1], b)
    else:
        segs.append([a, b])
for s in segs:
    s[0], s[1] = round(s[0], 3), round(s[1], 3)
# fecha sobreposições
for i in range(1, len(segs)):
    if segs[i][0] < segs[i - 1][1]:
        segs[i][0] = segs[i - 1][1]
# nova linha do tempo das palavras
out, t = [], 0.0
for a, b in segs:
    for (wa, wb, tx), i in zip(words, idx):
        if a <= wa < b:
            out.append([round(wa - a + t, 3), round(min(wb, b) - a + t, 3), tx, i])
    t += b - a
dur = round(t, 3)
os.makedirs('work', exist_ok=True)
open('words_cut.js', 'w').write('window.WORDS=' + json.dumps(out, ensure_ascii=False) + ';\nwindow.CLIPDUR=' + str(dur) + ';\n')
# filtro: cada trecho com zoom alternado (1.00 / 1.08) para disfarçar o corte
vf, af = [], []
for k, (a, b) in enumerate(segs):
    if k % 2 == 0:
        sc = 'scale=1036:-2,crop=1036:1380:0:40,unsharp=5:5:0.4'
    else:
        sc = 'scale=1119:-2,crop=1036:1380:41:84,unsharp=5:5:0.4'
    vf.append(f'[0:v]trim=start={a}:end={b},setpts=PTS-STARTPTS,{sc},setsar=1[v{k}]')
    af.append(f'[0:a]atrim=start={a}:end={b},asetpts=PTS-STARTPTS,afade=t=in:d=0.015,afade=t=out:st={max(0, b - a - .02):.3f}:d=0.02[a{k}]')
n = len(segs)
fc = ';'.join(vf + af) + ';' + ''.join(f'[v{k}][a{k}]' for k in range(n)) + f'concat=n={n}:v=1:a=1[v][a]'
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', src, '-filter_complex', fc, '-map', '[v]', '-map', '[a]',
                '-r', '30', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', 'work/painel.mp4'], check=True)
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', 'work/painel.mp4', '-vn', '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', 'work/voz.wav'], check=True)
print('trechos', n, 'duração', dur, 'de', W[-1][1])
