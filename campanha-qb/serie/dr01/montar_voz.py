"""Distribui a narração única (dr01/voz, uma tomada com os 3 ganchos + corpo) pelas variantes.

Antes: em dr01/voz, takes/all.wav (48 kHz mono) e `python3 ../../../vo_split.py`.
Aqui cada fala é aparada rente às palavras (ritmo mais seco) e cada variante
recebe vo/g1.wav (o seu gancho), o corpo e o vo_durations.js correspondente.
Uso (na pasta serie/): python3 dr01/montar_voz.py
"""
import json, os, re, wave
import numpy as np
SR, PRE, POST = 48000, .05, .14
js = open('dr01/voz/vo_durations.js').read()
words = json.loads(re.search(r'VOWORDS=(\{.*\});', js).group(1))
def cut(i):
    with wave.open(f'dr01/voz/vo/{i}.wav') as w:
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    t0, t1 = max(0, words[i][0][0] - PRE), min(len(a) / SR, words[i][-1][1] + POST)
    a = a[int(t0 * SR):int(t1 * SR)].astype(np.float64)
    f = int(.01 * SR); a[:f] *= np.linspace(0, 1, f); a[-f:] *= np.linspace(1, 0, f)
    return a.astype(np.int16), round(t1 - t0, 3), [[round(x - t0, 3), round(y - t0, 3)] for x, y in words[i]]
for v in 'abc':
    d = f'dr01{v}'; os.makedirs(f'{d}/vo', exist_ok=True); dur, wd = {}, {}
    for src, dst in [(f'g{v}', 'g1')] + [(k, k) for k in ('p1', 'p2', 's1', 's2', 'o1', 'c1')]:
        a, dur[dst], wd[dst] = cut(src)
        with wave.open(f'{d}/vo/{dst}.wav', 'w') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(a.tobytes())
    open(f'{d}/vo_durations.js', 'w').write('window.VODUR=' + json.dumps(dur) + ';\nwindow.VOWORDS=' + json.dumps(wd) + ';\n')
    print(d, dur, round(sum(dur.values()), 2))
