// Capa do especial (1080x1920). Antes: ffmpeg -ss 1 -i <painel.mp4> -frames:v 1 work/capa_frame.jpg
// Uso: node capa.js  →  out/capa_especial_incorporacao.jpg (fica fora do git: tem a imagem dela)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  await p.goto('file://' + path.resolve(__dirname, 'capa.html'));
  await p.evaluate(() => window.READY);
  await p.screenshot({ path: path.join(__dirname, 'out/capa_especial_incorporacao.jpg'), type: 'jpeg', quality: 92 });
  await b.close();
})();
