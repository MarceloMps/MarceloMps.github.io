#!/usr/bin/env bash
# Gera os vídeos finais: narração (vo/<id>.wav; se faltar, edge-tts pt-BR-AntonioNeural), quadros (Playwright),
# trilha/efeitos/mixagem (audio.py) e mux com loudness para redes sociais (-14 LUFS).
# Requisitos: node + playwright, python3 + numpy, ffmpeg, edge-tts (pip), acesso à internet.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p assets vo out
LOGO=https://qbgroupsolutions.lovable.app/__l5e/assets-v1/a78a23e4-75fd-41ff-a553-944fcda668b3/logo_w.png
[ -s assets/logo_w.png ] || curl -sfL -o assets/logo_w.png "$LOGO"

while IFS='|' read -r id txt; do
  [ -z "$id" ] && continue
  if [ ! -s "vo/$id.wav" ]; then
    edge-tts --voice pt-BR-AntonioNeural --rate=+15% --text "$txt" --write-media "vo/$id.mp3"
    ffmpeg -v error -y -i "vo/$id.mp3" -af "silenceremove=start_periods=1:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_threshold=-50dB,areverse" -ar 48000 -ac 1 "vo/$id.wav"
  fi
done < narracao.txt

# duração real de cada fala -> linha do tempo de ad.html
python3 - <<'PY'
import glob, json, os, wave
d = {}
for f in sorted(glob.glob("vo/*.wav")):
    with wave.open(f) as w: d[os.path.basename(f)[:-4]] = round(w.getnframes() / w.getframerate(), 3)
open("vo_durations.js", "w").write("window.VODUR=" + json.dumps(d) + ";\n")
print("vo_durations.js:", d)
PY

VERSIONS=${VERSIONS:-"feed story short"}
for v in $VERSIONS; do node render.js "$v" "out/$v.mp4" > "out/$v.log" 2>&1 & done
wait

declare -A NAME=([feed]="QB_feed_4x5_1080x1350" [story]="QB_stories_reels_9x16_1080x1920" [short]="QB_stories_reels_curto_9x16_1080x1920")
for v in $VERSIONS; do
  python3 - "$v" <<'PY'
import json, sys, wave
v = sys.argv[1]; M = json.load(open(f"out/{v}.json"))
for k, d in M["voDur"].items():
    with wave.open(f"vo/{k}.wav") as w: real = w.getnframes() / w.getframerate()
    if abs(real - d) > .15: print(f"AVISO {k}: duração real {real:.2f}s ≠ {d}s em ad.html")
def ts(t): h, r = divmod(t, 3600); m, s = divmod(r, 60); return f"{int(h):02}:{int(m):02}:{int(s):02},{int(round((s % 1) * 1000)):03}"
with open(f"out/{v}.srt", "w") as f:
    for i, (a, b, txt) in enumerate(M["caps"], 1): f.write(f"{i}\n{ts(a)} --> {ts(b)}\n{txt}\n\n")
PY
  python3 audio.py "out/$v.json" vo "out/$v.wav"
  ffmpeg -v error -y -i "out/$v.mp4" -i "out/$v.wav" -map 0:v -map 1:a -c:v copy \
    -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 -c:a aac -b:a 192k -movflags +faststart -shortest "out/${NAME[$v]}.mp4"
  cp "out/$v.srt" "out/${NAME[$v]}.srt"
  echo "ok: out/${NAME[$v]}.mp4"
done
