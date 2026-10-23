#!/usr/bin/env bash
# Especial incorporação: corte das pausas, painel com moldura da série,
# camada de cartões/legendas/cenas (renderizada em partes, para caber no
# limite de tempo do sandbox), trilha e mux.
# Antes: bash preparar_takes.sh ids.txt; python3 transcrever_takes.py takes/p_*.mp4;
#        python3 juntar.py words_all.json takes/p_1070.mp4 … takes/p_1078.mp4
# Uso: bash build.sh  (partes já renderizadas em parts/ são reaproveitadas)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work out parts

[ -s work/painel.mp4 ] || python3 cortar.py bruto.mp4 words.json
[ -s work/base.mp4 ] || ffmpeg -nostdin -v error -y -f lavfi -i color=white:s=1080x1920:r=30 -i work/painel.mp4 \
  -filter_complex "[0][1]overlay=22:518:shortest=1[v]" -map "[v]" -c:v libx264 -crf 14 -preset fast -pix_fmt yuv420p work/base.mp4
for r in "0 57" "57 114" "114 999"; do set -- $r; [ -s parts/p_$1.mp4 ] || node render_clip.js parts/p_$1.mp4 $1 $2; done
printf "file '%s'\n" p_0.mp4 p_57.mp4 p_114.mp4 > parts/lista.txt
ffmpeg -nostdin -v error -y -f concat -safe 0 -i parts/lista.txt -c copy out/video.mp4
cp parts/p_0.json out/video.json
python3 ../audio.py out/video.json work out/audio.wav
ffmpeg -nostdin -v error -y -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest out/QB_especial_incorporacao_9x16.mp4
python3 - <<'PY'
import json
M = json.load(open("out/video.json"))
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
with open("out/QB_especial_incorporacao.srt", "w") as f:
    for i, (a, b, txt) in enumerate(M["caps"], 1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
PY
echo "ok: out/QB_especial_incorporacao_9x16.mp4"
