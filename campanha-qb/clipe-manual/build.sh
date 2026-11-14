#!/usr/bin/env bash
# Clipe da Dra. Quetilin sobre o Manual: transcrição, corte das pausas, painel com
# moldura da série, camada de cartões/legendas, trilha e mux.  Uso: bash build.sh
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p work out
[ -s words.json ] || python3 transcrever.py bruto.mp4
python3 cortar.py bruto.mp4 words.json
ffmpeg -nostdin -v error -y -f lavfi -i color=white:s=1080x1920:r=30 -i work/painel.mp4 \
  -filter_complex "[0][1]overlay=22:518:shortest=1[v]" -map "[v]" -c:v libx264 -crf 14 -preset fast -pix_fmt yuv420p work/base.mp4
node render_clip.js out/video.mp4
python3 ../audio.py out/video.json work out/audio.wav
ffmpeg -nostdin -v error -y -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest out/QB_clipe_manual_9x16.mp4
python3 - <<'PY'
import json
M = json.load(open("out/video.json"))
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
with open("out/QB_clipe_manual.srt", "w") as f:
    for i, (a, b, txt) in enumerate(M["caps"], 1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
PY
echo "ok: out/QB_clipe_manual_9x16.mp4"
