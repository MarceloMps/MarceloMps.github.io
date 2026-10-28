// Renderiza a camada de sobreposição (fundo transparente) e compõe sobre work/base.mp4.
// Uso: node render_clip.js <saida.mp4|preview> [t1,t2,...]  |  node render_clip.js <parte.mp4> <ini> <fim>  (renderiza só um trecho)
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
(async () => {
  const [out, times, tEnd] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--font-render-hinting=none'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('pageerror', e.message));
  await p.goto('file://' + path.resolve(__dirname, 'clip.html'));
  await p.evaluate(() => window.READY);
  const meta = await p.evaluate(() => window.META);
  if (out === 'preview') {
    for (const t of times.split(',').map(Number)) {
      await p.evaluate(t => seek(t), t);
      await p.screenshot({ path: path.join(__dirname, `preview_${t}.png`), omitBackground: true });
    }
    console.log('dur', meta.dur);
  } else {
    fs.writeFileSync(out.replace(/\.mp4$/, '.json'), JSON.stringify(meta, null, 1));
    const n = Math.round(meta.dur * meta.fps), f0 = tEnd ? Math.round(+times * meta.fps) : 0, f1 = tEnd ? Math.min(n, Math.round(+tEnd * meta.fps)) : n;
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-ss', String(f0 / meta.fps), '-i', path.join(__dirname, 'work/base.mp4'),
      '-f', 'image2pipe', '-framerate', String(meta.fps), '-c:v', 'png', '-i', '-',
      '-filter_complex', '[0:v]tpad=stop_mode=clone:stop_duration=3[b];[b][1:v]overlay=0:0:shortest=1[v]', '-map', '[v]',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = f0; i < f1; i++) {
      await p.evaluate(t => seek(t), i / meta.fps);
      const buf = await p.screenshot({ type: 'png', omitBackground: true });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log(i, '/', n);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
