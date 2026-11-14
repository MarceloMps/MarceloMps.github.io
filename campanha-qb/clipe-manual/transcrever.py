"""Transcreve o vídeo bruto com tempo por palavra.  Uso: python3 transcrever.py bruto.mp4 → words.json"""
import json, subprocess, sys
from faster_whisper import WhisperModel
subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-i', sys.argv[1], '-ac', '1', '-ar', '16000', 'work/a16.wav'], check=True)
segs, _ = WhisperModel('small', compute_type='int8').transcribe('work/a16.wav', language='pt', word_timestamps=True)
json.dump([[round(w.start, 2), round(w.end, 2), w.word.strip()] for s in segs for w in s.words], open('words.json', 'w'), ensure_ascii=False)
