/* Renderiza um cartão de reporte de campo (HTML autocontido) em PNG e PDF.

   O cartão tem tamanho fixo — 1024 × 1280, o mesmo do modelo institucional que o
   gestor mandou —, então a captura é do nó .cartao, não da página.

   Uso:  NODE_PATH=/opt/node22/lib/node_modules /opt/node22/bin/node \
           scripts/imagem_reporte.js dist/REPORTE_5800440256.html
*/

const { chromium } = require('playwright');
const path = require('path');

const ENTRADA = path.resolve(process.argv[2] || 'dist/REPORTE_5800440256.html');
const SAIDA = ENTRADA.replace(/\.html$/, '');

(async () => {
  const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });

  const p = await b.newPage({ viewport: { width: 1100, height: 1360 }, deviceScaleFactor: 2 });
  await p.goto('file://' + ENTRADA);
  await p.waitForTimeout(1200);                       // fontes e fotos embutidas assentarem
  const el = await p.$('.cartao');
  await el.screenshot({ path: `${SAIDA}.png` });

  const p2 = await b.newPage({ viewport: { width: 1100, height: 1360 } });
  await p2.goto('file://' + ENTRADA);
  await p2.waitForTimeout(1200);
  await p2.pdf({
    path: `${SAIDA}.pdf`,
    width: '1024px', height: '1280px', printBackground: true,
    margin: { top: '0', bottom: '0', left: '0', right: '0' },
  });

  await b.close();
  console.log(`OK — ${SAIDA}.png (2048 × 2560) e ${SAIDA}.pdf`);
})();
