#!/usr/bin/env bash
# Monta uma variante do criativo com a narração já distribuída (montar_voz.py).
# Uso (na pasta serie/): [MUSIC_A=tenso.wav MUSIC_B=alto.wav] bash dr01/build.sh dr01a
set -euo pipefail
cd "$(dirname "$0")/../$1"
mkdir -p out
node ../render_ep.js . out/video.mp4
python3 ../../audio.py out/video.json vo out/audio.wav
ffmpeg -nostdin -v error -y -i out/video.mp4 -i out/audio.wav -map 0:v -map 1:a -c:v copy \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest "out/QB_$1_9x16.mp4"
echo "ok: out/QB_$1_9x16.mp4"
