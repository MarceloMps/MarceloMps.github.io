// Uso: node render_ep.js <pasta-do-episodio> <saida.mp4|preview> [t1,t2,...]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
(async () => {
  const [dir, out, times] = process.argv.slice(2);
  const b = await chromium.launch({ args: ['--font-render-hinting=none'] });
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  p.on('pageerror', e => console.error('pageerror', e.message));
  await p.goto('file://' + path.resolve(dir, 'ep.html'));
  await p.evaluate(() => window.READY);
  const meta = await p.evaluate(() => window.META);
  if (out === 'preview') {
    for (const t of times.split(',').map(Number)) {
      await p.evaluate(t => seek(t), t);
      await p.screenshot({ path: path.join(dir, `preview_${t}.jpg`), type: 'jpeg', quality: 80 });
    }
    console.log('dur', meta.dur);
  } else {
    fs.writeFileSync(out.replace(/\.mp4$/, '.json'), JSON.stringify(meta, null, 1));
    const n = Math.round(meta.dur * meta.fps);
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(meta.fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < n; i++) {
      await p.evaluate(t => seek(t), i / meta.fps);
      const buf = await p.screenshot({ type: 'jpeg', quality: 94 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log(i, '/', n);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
