#!/usr/bin/env bash
# Baixa os takes do Drive e converte para o painel: HDR do iPhone (HLG / Dolby
# Vision, BT.2020) → SDR BT.709 com mapeamento de tons, em 1080x1920.
# Sem o tonemap a imagem fica lavada ("fantasma"). Uso: bash preparar_takes.sh ids.txt
# ids.txt: "<nome> <id do arquivo no Drive>" por linha.
set -u
mkdir -p takes
TM="zscale=t=linear:npl=180,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
while read -r n id; do
  [ -z "$n" ] && continue
  [ -s "takes/p_$n.mp4" ] && continue
  curl -sSL -o "takes/raw_$n.mov" "https://drive.usercontent.google.com/download?id=$id&export=download&confirm=t" || { echo "falhou $n"; continue; }
  tr=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of csv=p=0 "takes/raw_$n.mov")
  if [ "$tr" = "arib-std-b67" ] || [ "$tr" = "smpte2084" ]; then vf="$TM,scale=1080:-2"; else vf="scale=1080:-2"; fi
  ffmpeg -nostdin -v error -y -i "takes/raw_$n.mov" -vf "$vf" -r 30 -c:v libx264 -crf 15 -preset fast \
    -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a aac -b:a 192k "takes/p_$n.mp4" && rm "takes/raw_$n.mov"
  echo "ok $n ($tr)"
done < "$1"
