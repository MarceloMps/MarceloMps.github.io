// Gera a imagem de cena de cada episódio (sem cabeçalho/legenda) para as capas.
// Uso: node cenas.js   →  capas/cena_ep01.png, capas/cena_ep02.png
const { chromium } = require('playwright');
const path = require('path');
const SHOTS = { ep01: 'T.a6+1.6', ep02: 'WS.a5[14]-0.05', ep03: 'WS.a5[11]-0.1', ep04: 'WS.a4[4]', ep05: 'WS.g1[12]' };
// no ep02 a câmera fica no plano geral para caber prédio, dívida e pessoas
const PRE = { ep02: 'CAMK.splice(0,CAMK.length,[0,1.05,600,1180],[999,1.05,600,1180])',
  ep03: 'CAMK.splice(0,CAMK.length,[0,1.02,600,1150],[999,1.02,600,1150])',
  ep05: 'CAMK.splice(0,CAMK.length,[0,1.1,600,1190],[999,1.1,600,1190])' };
(async () => {
  const b = await chromium.launch();
  for (const [ep, expr] of Object.entries(SHOTS)) {
    const p = await b.newPage({ viewport: { width: 1080, height: 1920 } });
    await p.goto('file://' + path.resolve(__dirname, '..', ep, 'ep.html'));
    await p.evaluate(() => window.READY);
    await p.evaluate(([e, pre]) => {
      if (pre) eval(pre);
      seek(eval(e));
      for (const s of ['#hdr', '#cap', '#frame', '.chip', '.stk']) document.querySelectorAll(s).forEach(x => x.style.display = 'none');
    }, [expr, PRE[ep]]);
    await p.screenshot({ path: path.join(__dirname, `cena_${ep}.png`), clip: { x: 0, y: 640, width: 1080, height: 1000 } });
  }
  await b.close();
})();
