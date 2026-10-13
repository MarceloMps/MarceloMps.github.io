#!/usr/bin/env bash
# Gera um episódio da série: narração gratuita (edge-tts, pt-BR-ThalitaMultilingualNeural),
# alinhamento por palavra, quadros, trilha/efeitos e mux.  Uso: bash build_ep.sh ep01
set -euo pipefail
cd "$(dirname "$0")/$1"
mkdir -p takes assets out
VOICE=${VOICE:-pt-BR-ThalitaMultilingualNeural}; RATE=${RATE:-+6%}
while IFS='|' read -r id txt; do
  [ -z "$id" ] && continue
  [ -s "takes/$id.wav" ] && continue
  edge-tts --voice "$VOICE" --rate="$RATE" --text "$txt" --write-media "takes/$id.mp3"
  ffmpeg -nostdin -v error -y -i "takes/$id.mp3" -ar 48000 -ac 1 -c:a pcm_s16le "takes/$id.wav" && rm "takes/$id.mp3"
done < narracao.txt
python3 ../../vo_split.py
node ../render_ep.js . out/video.mp4
python3 ../../audio.py out/video.json vo out/audio.wav
ffmpeg -nostdin -v error -y -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest "out/QB_serie_$1_9x16.mp4"
python3 - "$1" <<'PY'
import json, sys
M = json.load(open("out/video.json"))
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
with open(f"out/QB_serie_{sys.argv[1]}.srt", "w") as f:
    for i, (a, b, txt) in enumerate(M["caps"], 1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
PY
echo "ok: out/QB_serie_$1_9x16.mp4"
