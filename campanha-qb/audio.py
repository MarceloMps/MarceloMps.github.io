"""Desenho de som da campanha QB Group.

Trilha original sintetizada (tensão -> clareza/confiança), efeitos sonoros
sincronizados às pistas exportadas por ad.html (window.META.cues) e mixagem
com a narração, com ducking automático da música sob a voz.

Uso: python3 audio.py <meta.json> <dir_narracao_wav> <saida.wav>
"""
import json, sys, wave
import numpy as np

SR = 48000
rs = np.random.RandomState(7)


def T(d):
    return np.arange(int(d * SR)) / SR


def fft_filter(x, lo=None, hi=None, slope=1.5):
    """Filtro passa-faixa suave no domínio da frequência (sinal inteiro)."""
    n = len(x)
    if n == 0:
        return x
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR) + 1e-6
    g = np.ones_like(f)
    if hi:
        g /= np.sqrt(1 + (f / hi) ** (2 * slope))
    if lo:
        g /= np.sqrt(1 + (lo / f) ** (2 * slope))
    return np.fft.irfft(X * g, n)


def conv(x, ir):
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:len(x)]


def reverb_ir(d=1.6, decay=3.2, seed=1):
    r = np.random.RandomState(seed)
    t = T(d)
    ir = r.randn(len(t)) * np.exp(-decay * t)
    ir = fft_filter(ir, lo=200, hi=6000)
    ir[:int(.012 * SR)] = 0
    return ir / np.sqrt(np.sum(ir ** 2))


def env(n, a, d_rel, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-curve * np.maximum(0, t - a) / max(d_rel, 1e-3))
    return e


def nf(note):
    return 440.0 * 2 ** ((note - 69) / 12)


class Bus:
    def __init__(self, dur):
        self.L = np.zeros(int(dur * SR) + SR)
        self.R = np.zeros_like(self.L)

    def add(self, x, t, gain=1.0, pan=0.0):
        i = int(t * SR)
        if i < 0:
            x = x[-i:]
            i = 0
        j = min(len(self.L), i + len(x))
        x = x[:j - i]
        gl, gr = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        self.L[i:j] += x * gain * gl * 1.414
        self.R[i:j] += x * gain * gr * 1.414


# ---------------------------------------------------------------- efeitos
def sfx_impact(big=1.0):
    t = T(2.6)
    f = 32 + 70 * np.exp(-t * 7)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.2)
    nz = fft_filter(rs.randn(len(t)), hi=500) * np.exp(-t * 9) * .9
    click = fft_filter(rs.randn(len(t)), lo=1500) * np.exp(-t * 60) * .25
    x = boom + nz + click
    x = x + .35 * conv(x, reverb_ir(2.2, 2.0)) * big
    return x / np.max(np.abs(x))


def sfx_notif():
    out = np.zeros(int(.5 * SR))
    for k, (fr, st) in enumerate([(1318.5, 0), (1975.5, .11)]):
        t = T(.32)
        x = (np.sin(2 * np.pi * fr * t) + .3 * np.sin(4 * np.pi * fr * t)) * env(len(t), .004, .25, 5)
        i = int(st * SR)
        out[i:i + len(x)] += x[:len(out) - i]
    return out / np.max(np.abs(out))


def sfx_zap():
    t = T(.55)
    f = 2400 * np.exp(-t * 5) + 180
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .01, .45, 4)
    x += fft_filter(rs.randn(len(t)), lo=2000, hi=8000) * env(len(t), .005, .2, 6) * .3
    return x / np.max(np.abs(x))


def sfx_beep(fr=880, n=2, gap=.16, dur=.09):
    out = np.zeros(int((n * gap + .3) * SR))
    for k in range(n):
        t = T(dur)
        sq = np.sign(np.sin(2 * np.pi * fr * t)) * .35 + np.sin(2 * np.pi * fr * t) * .65
        x = fft_filter(sq, hi=4000) * env(len(t), .003, dur, 2)
        i = int(k * gap * SR)
        out[i:i + len(x)] += x
    return out / np.max(np.abs(out))


def sfx_stamp():
    t = T(.6)
    x = np.sin(2 * np.pi * 95 * t) * np.exp(-t * 14) + fft_filter(rs.randn(len(t)), hi=1800) * np.exp(-t * 25) * .8
    return x / np.max(np.abs(x))


def sfx_paper():
    t = T(.55)
    nz = fft_filter(rs.randn(len(t)), lo=1800, hi=7500)
    am = np.abs(fft_filter(rs.randn(len(t)), hi=40)) * 3
    x = nz * am * env(len(t), .03, .45, 3)
    return x / np.max(np.abs(x))


def sfx_whoosh(d=.7, lo=250, hi=5000):
    t = T(d)
    nz = rs.randn(len(t))
    # varredura por blocos
    out = np.zeros_like(nz)
    blk = 2048
    for i in range(0, len(t), blk):
        p = i / len(t)
        c = lo * (hi / lo) ** (np.sin(np.pi * p) ** 1.2)
        seg = nz[max(0, i - blk):i + blk * 2]
        y = fft_filter(seg, lo=c * .6, hi=c * 1.6, slope=2)
        off = i - max(0, i - blk)
        out[i:i + blk] = y[off:off + blk][:len(out[i:i + blk])]
    e = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    x = out * e
    return x / np.max(np.abs(x))


def sfx_scan():
    t = T(.7)
    f = 900 + 1500 * t / .7
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * (.6 + .4 * np.sin(2 * np.pi * 18 * t)) * env(len(t), .05, .6, 2)
    return x / np.max(np.abs(x))


def sfx_pop():
    t = T(.18)
    f = 520 + 600 * t / .18
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(len(t), .003, .12, 5)
    return x / np.max(np.abs(x))


def sfx_tick():
    t = T(.12)
    x = fft_filter(rs.randn(len(t)), lo=2500, hi=9000) * np.exp(-t * 80) + np.sin(2 * np.pi * 2200 * t) * np.exp(-t * 60) * .5
    return x / np.max(np.abs(x))


def bell(fr, d=1.8):
    t = T(d)
    x = sum(a * np.sin(2 * np.pi * fr * m * t) * np.exp(-t * k) for m, a, k in [(1, 1, 2.2), (2.01, .45, 3.5), (3.0, .25, 5), (4.2, .12, 7)])
    x = x * env(len(t), .004, d, .1)
    return x / np.max(np.abs(x))


def sfx_shimmer():
    out = np.zeros(int(1.6 * SR))
    for k, n in enumerate([86, 90, 93, 98, 102]):
        b = bell(nf(n), 1.2) * .5
        i = int(k * .06 * SR)
        out[i:i + len(b)] += b[:len(out) - i]
    out = out + .5 * conv(out, reverb_ir(1.4, 3))
    return out / np.max(np.abs(out))


def sfx_riser(d=1.6):
    t = T(d)
    nz = rs.randn(len(t))
    hp = fft_filter(nz, lo=800, hi=9000)
    x = hp * (t / d) ** 2.2
    f = 180 * 2 ** (2.5 * t / d)
    x += np.sin(2 * np.pi * np.cumsum(f) / SR) * (t / d) ** 2 * .6
    return x / np.max(np.abs(x))


def sfx_click():
    t = T(.1)
    x = np.sin(2 * np.pi * 1600 * t) * np.exp(-t * 90) + fft_filter(rs.randn(len(t)), lo=3000) * np.exp(-t * 120) * .4
    return x / np.max(np.abs(x))


# ---------------------------------------------------------------- música
def saw(fr, t, det=0.0):
    ph = (fr * (1 + det) * t) % 1.0
    return 2 * ph - 1


def build_music(dur, shift, bpm=96):
    beat = 60 / bpm
    L = np.zeros(int(dur * SR) + SR)
    R = np.zeros_like(L)
    n = len(L)
    tt = np.arange(n) / SR

    # --- tensão: drone em Ré menor + pulso de "relógio" crescente
    tens_end = shift if shift else dur
    m = tt < tens_end + 1.2
    fade_t = np.clip((tens_end + 1.2 - tt) / 1.2, 0, 1)
    intens = np.clip(tt / max(tens_end, 1), 0, 1)
    drone = (saw(nf(38), tt) + saw(nf(38), tt, .004) + .6 * saw(nf(45), tt, -.003) + .4 * saw(nf(41), tt, .002))
    drone = fft_filter(drone * m, hi=420) * .22 * fade_t * (.7 + .3 * intens)
    L += drone
    R += np.roll(drone, 240)
    k = 0
    while k * beat < tens_end:
        t0 = k * beat
        tb = T(.45)
        thump = np.sin(2 * np.pi * (48 + 60 * np.exp(-tb * 30)) * tb) * np.exp(-tb * 9) * (.35 + .4 * (t0 / tens_end))
        i = int(t0 * SR)
        if t0 > .3:
            L[i:i + len(tb)] += thump[:n - i]
            R[i:i + len(tb)] += thump[:n - i]
        for h in (0, .5):
            ti = t0 + h * beat
            tk = sfx_tick() * (.035 + .05 * (t0 / tens_end))
            j = int(ti * SR)
            pan = .35 if h else -.35
            L[j:j + len(tk)] += tk[:n - j] * (1 - pan)
            R[j:j + len(tk)] += tk[:n - j] * (1 + pan)
        k += 1
    # nota aguda de suspense
    sus = np.sin(2 * np.pi * nf(81) * tt) * .025 * (.5 + .5 * np.sin(2 * np.pi * .35 * tt)) * m * fade_t
    L += sus
    R += sus

    if shift is None:
        return L, R

    # --- resolução: progressão maior, pads, arpejo, baixo e batida leve
    prog = [[50, 54, 57, 61, 64], [47, 50, 54, 57, 61], [43, 47, 50, 54, 57], [45, 49, 52, 55, 59]]  # Dmaj9 Bm9 Gmaj7 A7
    bar = 4 * beat
    t = shift
    ci = 0
    arp_ir = reverb_ir(1.8, 2.6, 3)
    padL = np.zeros_like(L)
    padR = np.zeros_like(L)
    arp = np.zeros_like(L)
    bass = np.zeros_like(L)
    drums = np.zeros_like(L)
    while t < dur + bar:
        ch = prog[ci % 4]
        d = 2 * bar
        i0 = int(t * SR)
        if i0 >= n:
            break
        seg = T(d + .8)
        e = np.minimum(1, seg / .5) * np.clip((d + .8 - seg) / .8, 0, 1)
        pl = sum(saw(nf(nn + 12), seg, .003 * (q + 1)) for q, nn in enumerate(ch[1:]))
        pr = sum(saw(nf(nn + 12), seg, -.003 * (q + 1)) for q, nn in enumerate(ch[1:]))
        pl = fft_filter(pl, hi=1500, lo=180) * e * .045
        pr = fft_filter(pr, hi=1500, lo=180) * e * .045
        j = min(n, i0 + len(seg))
        padL[i0:j] += pl[:j - i0]
        padR[i0:j] += pr[:j - i0]
        bs = np.sin(2 * np.pi * nf(ch[0] - 12) * seg) * e * .22
        bass[i0:j] += bs[:j - i0]
        # arpejo em colcheias
        notes = [ch[1] + 12, ch[2] + 12, ch[3] + 12, ch[4] + 12, ch[3] + 12, ch[2] + 12, ch[4] + 12, ch[2] + 24]
        for q in range(16):
            ta = t + q * beat / 2
            if ta >= dur:
                break
            tp = T(.6)
            fr = nf(notes[q % 8])
            pk = (np.sin(2 * np.pi * fr * tp) + .25 * np.sin(4 * np.pi * fr * tp)) * env(len(tp), .004, .45, 4)
            ia = int(ta * SR)
            jj = min(n, ia + len(tp))
            arp[ia:jj] += pk[:jj - ia] * (.09 if q % 2 == 0 else .06)
        # batida discreta (a partir do 2º compasso)
        for q in range(8):
            tb = t + q * beat
            if tb < shift + bar or tb >= dur - .2:
                continue
            kk = T(.4)
            kick = np.sin(2 * np.pi * (45 + 90 * np.exp(-kk * 35)) * kk) * np.exp(-kk * 10) * .28
            ib = int(tb * SR)
            jb = min(n, ib + len(kk))
            drums[ib:jb] += kick[:jb - ib]
            if q % 2 == 1:
                sn = fft_filter(rs.randn(len(T(.2))), lo=1500, hi=8000) * np.exp(-T(.2) * 25) * .05
                drums[ib:ib + len(sn)] += sn[:n - ib]
        t += d
        ci += 1
    arp_w = conv(arp, arp_ir)
    fade_in = np.clip((tt - shift) / .4, 0, 1)
    L += (padL + bass + drums + arp + .5 * np.roll(arp_w, 0)) * fade_in
    R += (padR + bass + drums + .8 * arp + .5 * np.roll(arp_w, 1800)) * fade_in
    # final: fade suave
    tail = np.clip((dur - tt) / 1.0, 0, 1)
    return L * tail, R * tail


# ---------------------------------------------------------------- mix
def read_wav(p):
    with wave.open(p) as w:
        assert w.getframerate() == SR, p
        a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        if w.getnchannels() == 2:
            a = a.reshape(-1, 2).mean(1)
    return a


def process_voice(x):
    x = fft_filter(x, lo=85, hi=14000)
    # leve presença
    x = x + .25 * fft_filter(x, lo=2500, hi=6000)
    # compressão simples por envelope RMS
    e = np.sqrt(np.convolve(x ** 2, np.ones(480) / 480, 'same')) + 1e-6
    thr = .08
    g = np.where(e > thr, (thr / e) ** .45, 1.0)
    g = np.convolve(g, np.ones(240) / 240, 'same')
    y = x * g
    return y / np.max(np.abs(y)) * .89


def main(meta_p, vo_dir, out):
    M = json.load(open(meta_p))
    dur = M['dur']
    shift = M.get('music_shift')
    voice = Bus(dur)
    for vid, t0 in M['vo']:
        v = process_voice(read_wav(f"{vo_dir}/{vid}.wav"))
        voice.add(v, t0, 1.0)
    mL, mR = build_music(dur, shift)
    n = len(voice.L)
    mL, mR = mL[:n], mR[:n]
    # ducking da trilha sob a voz
    ve = np.abs(voice.L)
    ve = np.convolve(ve, np.ones(int(.05 * SR)) / (.05 * SR), 'same')
    duck = np.clip(ve / .05, 0, 1)
    att = np.convolve(duck, np.ones(int(.25 * SR)) / (.25 * SR), 'same')
    duck = np.maximum(duck, att)
    mg = 1 - .62 * np.clip(duck, 0, 1)
    music_gain = .55
    fx = Bus(dur)
    lib = {
        'notif': (sfx_notif(), .30, 0), 'impact': (sfx_impact(), .95, 0), 'zap': (sfx_zap(), .22, .2),
        'alert': (sfx_beep(880, 2), .13, .15), 'stamp': (sfx_stamp(), .50, 0), 'paper': (sfx_paper(), .22, -.2),
        'whoosh': (sfx_whoosh(), .30, 0), 'swish': (sfx_whoosh(.45, 400, 6000), .20, .3), 'scan': (sfx_scan(), .07, 0),
        'beep': (sfx_beep(1046, 1, .1, .07), .08, .2), 'pop': (sfx_pop(), .16, -.25), 'tick': (sfx_tick(), .14, 0),
        'riser': (sfx_riser(), .26, 0), 'impact_soft': (sfx_impact(.6), .45, 0), 'shimmer': (sfx_shimmer(), .16, 0),
        'check': (bell(nf(86), .6), .12, .1), 'impact_final': (sfx_impact(1.3), 1.0, 0), 'click': (sfx_click(), .25, 0),
    }
    chimes = [bell(nf(n), 1.4) for n in (74, 78, 81, 86)]
    for k, t, v in M['cues']:
        if k == 'chime':
            fx.add(chimes[int(v) % 4], t, .16, (-.3, .3, -.15, .15)[int(v) % 4])
            continue
        if k not in lib:
            continue
        x, gn, pan = lib[k]
        fx.add(x, t, gn * (v if isinstance(v, (int, float)) else 1), pan)
    # acorde final junto do logotipo
    for k, t, v in M['cues']:
        if k == 'impact_final':
            for q, nn in enumerate([62, 66, 69, 74]):
                b = bell(nf(nn), 2.5)
                fx.add(b, t + q * .015, .10, (-.4, -.1, .1, .4)[q])
    fx_rev_L = conv(fx.L, reverb_ir(1.2, 3.5, 5))
    fx_rev_R = conv(fx.R, reverb_ir(1.2, 3.5, 6))
    L = voice.L + mL * music_gain * mg + fx.L + .18 * fx_rev_L
    R = voice.R + mR * music_gain * mg + fx.R + .18 * fx_rev_R
    st = np.stack([L, R], 1)[:int(dur * SR)]
    # fade final e limitador suave
    st[-int(.3 * SR):] *= np.linspace(1, 0, int(.3 * SR))[:, None]
    st = np.tanh(st * 1.1) / np.tanh(1.1)
    st = st / np.max(np.abs(st)) * .95
    with wave.open(out, 'w') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


if __name__ == '__main__':
    main(*sys.argv[1:4])
