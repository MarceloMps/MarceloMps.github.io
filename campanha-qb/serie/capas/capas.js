// Uso: node capas.js  →  capa_ep01.jpg, capa_ep02.jpg (1080x1920)
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
  for (const ep of ['ep01', 'ep02']) {
    await p.goto('file://' + path.resolve(__dirname, 'capa.html') + '?ep=' + ep);
    await p.evaluate(() => window.READY);
    await p.screenshot({ path: path.join(__dirname, `capa_${ep}.jpg`), type: 'jpeg', quality: 92 });
  }
  await b.close();
})();
