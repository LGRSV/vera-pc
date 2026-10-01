/* Gera a imagem da «carteira em movimento» para apresentação, a partir da
   própria página da dinâmica — assim o slide nunca diverge do site.

   Saída: dist/carteira-em-movimento.png  (4× de densidade, ~5360 px de largura)
          dist/carteira-em-movimento.pdf  (vetorial, sem perda em qualquer tamanho)

   Fundo branco puro no lugar do papel do tema: em projeção o creme suja, e a
   legenda de interação («passe o mouse») não faz sentido impressa.

   Uso:  NODE_PATH=/opt/node22/lib/node_modules node scripts/imagem_carteira.js
*/

const { chromium } = require('playwright');
const path = require('path');

const RAIZ = path.dirname(__dirname);
const PAGINA = 'file://' + path.join(RAIZ, 'dist', 'dinamica-posto.html');
const SAIDA = path.join(RAIZ, 'dist', 'carteira-em-movimento');

/* Roda dentro da página: recorta o bloco, branqueia o fundo e devolve o nó. */
function isolar() {
  const h4 = [...document.querySelectorAll('h4.sub-grafico')]
    .find((x) => x.textContent.includes('carteira em movimento'));
  if (!h4) throw new Error('bloco «A carteira em movimento» não encontrado');

  const cx = document.createElement('div');
  cx.id = 'captura';
  cx.style.cssText = 'padding:44px 50px 40px;background:#fff;max-width:1340px';

  // do subtítulo até a nota de conciliação, que fecha o raciocínio
  const nos = [h4];
  let n = h4.nextElementSibling;
  while (n && !n.matches('h4, section')) {
    nos.push(n);
    const fim = n.matches('.nota') && n.textContent.includes('conta fecha na carteira');
    n = n.nextElementSibling;
    if (fim) break;
  }
  nos.forEach((x) => cx.appendChild(x.cloneNode(true)));
  document.body.insertBefore(cx, document.body.firstChild);
  [...document.body.children].forEach((x) => { if (x !== cx) x.style.display = 'none'; });

  const st = document.createElement('style');
  st.textContent = ':root{--papel:#ffffff;--papel-2:#fbfbfa;--papel-3:#f1f0ec;'
    + '--filete:#d6d3ca;--filete-2:#a8a49a;--tinta:#141310;--tinta-2:#4a463c;'
    + '--tinta-3:#84806f;--sinal-papel:#fdf0e6}'
    + 'body,#captura{background:#fff}'
    + '#captura .grafico-saldo .risco{stroke:#e2e0d9}';
  document.head.appendChild(st);

  cx.querySelector('h4').style.cssText = 'margin:0 0 12px;border:0;padding:0;'
    + 'font:700 30px var(--cond);letter-spacing:.08em;text-transform:uppercase;color:#141310';
  cx.querySelectorAll('figcaption').forEach((f) => {
    f.textContent = f.textContent.replace(/\s*Passe o mouse[^.]*\.\s*/, '').trim();
    if (!f.textContent) f.remove();
  });
  const tela = cx.querySelector('.tela-grafico');
  if (tela) tela.style.overflow = 'visible';
  const svg = cx.querySelector('svg');
  if (svg) { svg.style.minWidth = '0'; svg.removeAttribute('preserveAspectRatio'); }
  return cx;
}

(async () => {
  const b = await chromium.launch();

  const p = await b.newPage({ viewport: { width: 1400, height: 1400 }, deviceScaleFactor: 4 });
  await p.goto(PAGINA);
  await p.waitForTimeout(1400);                    // fontes embutidas assentarem
  const el = await p.evaluateHandle(isolar);
  await p.waitForTimeout(500);
  await el.asElement().screenshot({ path: `${SAIDA}.png` });

  // o PDF precisa de página em densidade 1: o tamanho vem do bloco em px de CSS
  const p2 = await b.newPage({ viewport: { width: 1400, height: 1400 } });
  await p2.goto(PAGINA);
  await p2.waitForTimeout(1400);
  await p2.evaluateHandle(isolar);
  await p2.waitForTimeout(400);
  const d = await p2.evaluate(() => {
    const c = document.getElementById('captura');
    return { w: c.scrollWidth, h: c.scrollHeight };
  });
  await p2.pdf({
    path: `${SAIDA}.pdf`,
    width: `${d.w}px`,
    height: `${d.h + 2}px`,
    printBackground: true,
    margin: { top: '0', bottom: '0', left: '0', right: '0' },
  });

  await b.close();
  console.log(`OK — ${SAIDA}.png (${d.w * 4} × ${(d.h + 1) * 4} px) e ${SAIDA}.pdf`);
})();
