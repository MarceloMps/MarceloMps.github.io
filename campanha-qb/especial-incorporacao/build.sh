#!/usr/bin/env bash
# Especial incorporação: corte das pausas, painel com moldura da série,
# camada de cartões/legendas/cenas (renderizada em partes, para caber no
# limite de tempo do sandbox), trilha e mux.
# Antes: bash preparar_takes.sh ids.txt; python3 transcrever_takes.py takes/p_*.mp4;
#        python3 juntar.py words_all.json takes/p_1070.mp4 … takes/p_1078.mp4
# Uso: bash build.sh          versão completa (~2min50)
#      bash build.sh curta    versão de ~90 s, montada em ../especial-incorporacao-curta
# Partes já renderizadas em parts/ são reaproveitadas.
set -euo pipefail
cd "$(dirname "$0")"
NOME=QB_especial_incorporacao
if [ "${1:-}" = curta ]; then
  # trechos removidos (índices das palavras): detalhes do gancho, a fala ao corretor,
  # repetições nos riscos, o bloco das infrações, a explicação dos 3 pontos,
  # "não é só papel" e partes do fechamento
  DROP=$(python3 -c "r=[(13,26),(42,44),(50,82),(143,149),(152,157),(183,185),(189,262),(267,279),(328,356),(368,370),(381,393)];print(','.join(str(i) for a,b in r for i in range(a,b+1)))")
  D=../especial-incorporacao-curta; mkdir -p $D
  cp clip.html render_clip.js cortar.py $D/; cp -r assets $D/ 2>/dev/null || true
  ln -sf ../especial-incorporacao/bruto.mp4 $D/bruto.mp4; cp words.json $D/
  cd $D; NOME=QB_especial_incorporacao_curta
  [ -s work/painel.mp4 ] || python3 cortar.py bruto.mp4 words.json "$DROP"
fi
mkdir -p work out parts

[ -s work/painel.mp4 ] || python3 cortar.py bruto.mp4 words.json
[ -s work/base.mp4 ] || ffmpeg -nostdin -v error -y -f lavfi -i color=white:s=1080x1920:r=30 -i work/painel.mp4 \
  -filter_complex "[0][1]overlay=22:518:shortest=1[v]" -map "[v]" -c:v libx264 -crf 14 -preset fast -pix_fmt yuv420p work/base.mp4
DURC=$(python3 -c "import re;print(int(float(re.search(r'CLIPDUR=([0-9.]+)',open('words_cut.js').read()).group(1))+1))")
: > parts/lista.txt
for s in 0 57 114 171 228; do
  [ $s -lt $DURC ] || break
  [ -s parts/p_$s.mp4 ] || node render_clip.js parts/p_$s.mp4 $s $((s + 57))
  echo "file 'p_$s.mp4'" >> parts/lista.txt
done
ffmpeg -nostdin -v error -y -f concat -safe 0 -i parts/lista.txt -c copy out/video.mp4
cp parts/p_0.json out/video.json
python3 ../audio.py out/video.json work out/audio.wav
ffmpeg -nostdin -v error -y -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest out/${NOME}_9x16.mp4
python3 - "$NOME" <<'PY'
import json, sys
M = json.load(open("out/video.json"))
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
with open(f"out/{sys.argv[1]}.srt", "w") as f:
    for i, (a, b, txt) in enumerate(M["caps"], 1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
PY
echo "ok: out/${NOME}_9x16.mp4"
