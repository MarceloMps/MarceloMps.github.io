// Uso: node render.js <feed|story|short> <saida.mp4|preview> [t1,t2,...]
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path'), fs = require('fs');
(async () => {
  const [v, out, times] = process.argv.slice(2);
  const H = v === 'feed' ? 1350 : 1920;
  const b = await chromium.launch({ args: ['--disable-gpu-vsync', '--font-render-hinting=none'] });
  const p = await b.newPage({ viewport: { width: 1080, height: H }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.resolve(__dirname, 'ad.html') + '?v=' + v);
  await p.evaluate(() => window.READY);
  const meta = await p.evaluate(() => window.META);
  if (out === 'preview') {
    for (const t of times.split(',').map(Number)) {
      await p.evaluate(t => seek(t), t);
      await p.screenshot({ path: `preview_${v}_${t}.jpg`, type: 'jpeg', quality: 80 });
    }
  } else {
    fs.writeFileSync(out.replace(/\.mp4$/, '.json'), JSON.stringify(meta, null, 1));
    const fps = meta.fps, n = Math.round(meta.dur * fps);
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = 0; i < n; i++) {
      await p.evaluate(t => seek(t), i / fps);
      const buf = await p.screenshot({ type: 'jpeg', quality: 94 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if (i % 150 === 0) console.log(v, i, '/', n);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await b.close();
})();
