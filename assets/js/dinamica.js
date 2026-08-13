/* Dinâmica do posto — onde cada equipamento está hoje.
   Uma página só: a escada de etapas, o corte por criticidade e a lista inteira. */

const D = DINAMICA;
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? '').replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const rs = (v) => `R$ ${Number(v || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const TOM = {
  'Concluído': 'bom', 'Cancelada em operação': 'bom', 'Em ajustes': 'bom',
  'Aguardando comissionamento': 'bom', 'Entregue ao COCM': 'atento', 'Em logística': 'atento',
  'Em compra': 'critico', 'Travado': 'critico',
};

const EXPLICA = {
  'Concluído': 'serviço fechado no parecer',
  'Cancelada em operação': 'a SS caiu porque o equipamento já estava operando',
  'Em ajustes': 'trocado, a Proteção ainda vai ajustar',
  'Aguardando comissionamento': 'trocado, o DMSL ainda vai comissionar',
  'Entregue ao COCM': 'material na mão da equipe, falta subir no poste',
  'Em logística': 'comprado, a caminho',
  'Em compra': 'na fila do posto',
  'Com o DMSL': 'laudo pedido, esperando o DMSL responder',
  'Primeiro ataque do DMSL': 'entrou agora, o DMSL vai ao campo diagnosticar',
  'Em análise': 'o posto está lendo o caso',
  'Travado': 'parado por coisa que não é material',
  'Desmobilizado': 'não era caso do posto',
  'Sem parecer': 'ainda não foi olhado',
};

const num = ({ rotulo, valor, nota, tom = '' }) => `<div class="numero ${tom}">
  <span>${esc(rotulo)}</span><b>${esc(valor)}</b>${nota ? `<i>${esc(nota)}</i>` : ''}</div>`;

let filtro = null;

const MES_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const rotuloMes = (m) => `${MES_PT[+m.split('-')[1] - 1]}/${m.split('-')[0]}`;
const dataBr = (iso) => { const [a, m, d] = String(iso).split('-'); return d ? `${d}/${m}/${a}` : iso; };

/* Barras agrupadas — três séries por mês. As cores saem de --serie-1/2/3, que
   passaram pelo validador de paleta nos dois temas. Cada barra leva o valor
   escrito em cima, então a identidade nunca depende só da cor. */
function barrasTresColunas(curva) {
  const SERIES = [
    { chave: 'ativos', nome: 'Ativos', cor: 'var(--serie-1)',
      dica: 'da carteira herdada, pela abertura da SS' },
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-2)',
      dica: 'ativos novos no COEP, pela abertura da SS' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)',
      dica: 'pelo mês da tratativa ou do repasse' },
  ];
  const teto = Math.max(...curva.flatMap((m) => SERIES.map((s) => m[s.chave])), 1);
  const L = 44, R = 12, T = 22, B = 44;
  const larguraGrupo = 96, alturaPlot = 210;
  const W = L + R + larguraGrupo * curva.length;
  const H = T + alturaPlot + B;
  const larguraBarra = 24, vao = 2;
  const bloco = SERIES.length * larguraBarra + (SERIES.length - 1) * vao;
  const passo = teto <= 10 ? 2 : teto <= 30 ? 10 : 20;
  const riscos = [];
  for (let v = 0; v <= teto; v += passo) riscos.push(v);
  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;

  return `<figure class="grafico-barras">
    <div class="legenda-series">
      ${SERIES.map((s) => `<span class="serie"><i style="background:${s.cor}"></i>
        <b>${esc(s.nome)}</b> <em>${esc(s.dica)}</em></span>`).join('')}
    </div>
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Barras agrupadas por mês de 2026: ${curva.map((m) => `${m.rotulo}, ${SERIES.map((s) => `${s.nome} ${m[s.chave]}`).join(', ')}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${curva.map((m, i) => {
        const x0 = L + i * larguraGrupo + (larguraGrupo - bloco) / 2;
        return `<g class="grupo-mes">
          ${SERIES.map((s, j) => {
            const v = m[s.chave];
            const x = x0 + j * (larguraBarra + vao);
            const alt = Math.max((v / teto) * alturaPlot, v ? 2 : 0);
            return `<g class="barra-mes">
              <title>${esc(m.rotulo)} · ${esc(s.nome)}: ${v}</title>
              <rect x="${x}" y="${(T + alturaPlot - alt).toFixed(1)}" width="${larguraBarra}"
                    height="${alt.toFixed(1)}" rx="4" ry="4" fill="${s.cor}"/>
              ${v ? `<rect x="${x}" y="${(T + alturaPlot - Math.min(alt, 5)).toFixed(1)}"
                    width="${larguraBarra}" height="${Math.min(alt, 5).toFixed(1)}" fill="${s.cor}"/>` : ''}
              ${v ? `<text x="${x + larguraBarra / 2}" y="${(T + alturaPlot - alt - 5).toFixed(1)}"
                    class="rot-valor" text-anchor="middle">${v}</text>` : ''}
            </g>`;
          }).join('')}
          <text x="${(x0 + bloco / 2).toFixed(1)}" y="${T + alturaPlot + 18}"
                class="rot-mes" text-anchor="middle">${esc(m.rotulo)}</text>
        </g>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>Cada barra traz o próprio número, então dá para ler a figura sem
    depender da cor. Os mesmos valores estão na tabela abaixo.</figcaption>
  </figure>`;
}

/* O saldo da carteira herdada, mês a mês. Série única — sem caixa de legenda;
   a coluna cinza da frente é o acervo com que o posto abriu o ano. */
function colunaSaldo(mm) {
  const cols = [
    { rotulo: 'Acervo', final: mm.abertura, tipo: 'acervo',
      conta: `Acervo: ${mm.abertura} SS de 2023–2025 pendentes na abertura de 2026` },
    ...mm.saldo.map((s) => ({ rotulo: s.rotulo, final: s.final, tipo: '',
      conta: `${s.rotulo}: começou com ${s.inicial}, abriram ${s.entram}, tratados ${s.saem}, sobrou ${s.final}` })),
  ];
  const picoV = Math.max(...mm.saldo.map((s) => s.final));
  const teto = Math.ceil(Math.max(picoV, mm.abertura, 1) / 20) * 20;
  const L = 44, R = 12, T = 22, B = 44;
  const largura = 88, alturaPlot = 190;
  const W = L + R + largura * cols.length;
  const H = T + alturaPlot + B;
  const barra = 34;
  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;
  const riscos = [];
  for (let v = 0; v <= teto; v += 20) riscos.push(v);

  return `<figure class="grafico-barras grafico-saldo">
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Saldo da carteira herdada no fim de cada mês: ${cols.map((c) => `${c.rotulo}, ${c.final}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${cols.map((c, i) => {
        const x = L + i * largura + (largura - barra) / 2;
        const alt = Math.max((c.final / teto) * alturaPlot, c.final ? 2 : 0);
        return `<g class="barra-mes ${c.tipo}${!c.tipo && c.final === picoV ? ' pico' : ''}">
          <title>${esc(c.conta)}</title>
          <rect x="${x}" y="${(T + alturaPlot - alt).toFixed(1)}" width="${barra}"
                height="${alt.toFixed(1)}" rx="4" ry="4"/>
          <rect x="${x}" y="${(T + alturaPlot - Math.min(alt, 5)).toFixed(1)}"
                width="${barra}" height="${Math.min(alt, 5).toFixed(1)}"/>
          <text x="${x + barra / 2}" y="${(T + alturaPlot - alt - 6).toFixed(1)}"
                class="rot-valor" text-anchor="middle">${c.final}</text>
          <text x="${x + barra / 2}" y="${T + alturaPlot + 18}" class="rot-mes"
                text-anchor="middle">${esc(c.rotulo)}</text>
        </g>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>A coluna cinza é o acervo herdado; as azuis, o saldo no fim de cada mês;
    a laranja marca o topo da fila. Passe o mouse para ver a conta do mês inteiro.</figcaption>
  </figure>`;
}

/* O livro-caixa: saldo do mês anterior + SS abertas no mês − tratadas = sobra. */
function livroCaixa(mm) {
  const sal = mm.saldo;
  const totE = sal.reduce((n, s) => n + s.entram, 0);
  const totS = sal.reduce((n, s) => n + s.saem, 0);
  const fim = sal[sal.length - 1];
  return `${colunaSaldo(mm)}
  <div class="tabela-rol" style="margin-top:18px"><table class="matriz"><thead><tr>
    <th>Mês</th><th class="num">Começou com</th><th class="num">Entraram</th>
    <th class="num">Saíram</th><th class="num">Sobrou no fim</th>
    <th class="num">Variação</th></tr></thead><tbody>
    <tr><td>Acervo de 2023–2025 <i>(saldo de abertura)</i></td><td class="num">—</td>
      <td class="num">—</td><td class="num">—</td><td class="num"><b>${mm.abertura}</b></td>
      <td class="num">—</td></tr>
    ${sal.map((s) => {
      const d = s.final - s.inicial;
      return `<tr><td>${esc(s.rotulo)}</td><td class="num">${s.inicial}</td>
        <td class="num">${s.entram || '—'}</td><td class="num">${s.saem || '—'}</td>
        <td class="num"><b>${s.final}</b></td>
        <td class="num ${d > 0 ? 'sobe' : d < 0 ? 'desce' : ''}">${d > 0 ? '+' : ''}${d || '—'}</td></tr>`;
    }).join('')}
  </tbody><tfoot><tr><td>Total do ano</td><td class="num">—</td>
    <td class="num"><b>${totE}</b></td><td class="num"><b>${totS}</b></td>
    <td class="num"><b>${fim.final}</b></td>
    <td class="num">${fim.final - mm.abertura > 0 ? '+' : ''}${fim.final - mm.abertura}</td></tr></tfoot></table></div>
  <div class="nota" style="margin-top:14px"><strong>A conta fecha na carteira</strong>
  ${mm.abertura} do acervo + ${totE} abertas em 2026 = ${mm.abertura + totE} ativos da foto;
  ${totS} tratados; sobram ${fim.final} — exatamente os que a carteira mostra ainda no fluxo.
  Os ${mm.fora_do_livro} ativos que passaram pelo COEP em 2026 por fora da foto não entram neste
  livro: sem SS na foto de entrada, não há data de tratativa rastreada para dar baixa. Eles
  seguem na coluna de entrantes e na lista própria.</div>`;
}

/* A mesma coisa somando: onde cada série chegou até o fim de cada mês. Linha em
   vez de barra porque o que importa aqui é a distância entre as curvas — o
   tamanho da fila contra o que já saiu — e barra empilhada esconde isso. */
function linhaAcumulada(curva) {
  const SERIES = [
    { chave: 'ativos', nome: 'Ativos', cor: 'var(--serie-1)' },
    { chave: 'entrantes', nome: 'Entrantes', cor: 'var(--serie-2)' },
    { chave: 'resolvidos', nome: 'Resolvidos', cor: 'var(--serie-3)' },
  ];
  let soma = { ativos: 0, entrantes: 0, resolvidos: 0 };
  const ac = curva.map((m) => {
    soma = { ativos: soma.ativos + m.ativos, entrantes: soma.entrantes + m.entrantes,
             resolvidos: soma.resolvidos + m.resolvidos };
    return { ...soma, mes: m.mes, rotulo: m.rotulo };
  });
  const bruto = Math.max(...ac.flatMap((m) => SERIES.map((s) => m[s.chave])), 1);
  const passo = bruto <= 50 ? 10 : 20;
  const teto = Math.ceil(bruto / passo) * passo;
  const L = 44, R = 58, T = 20, B = 44;
  const largura = 108, alturaPlot = 210;
  const W = L + R + largura * (ac.length - 1);
  const H = T + alturaPlot + B;
  const x = (i) => L + i * largura;
  const y = (v) => T + alturaPlot - (v / teto) * alturaPlot;
  const riscos = [];
  for (let v = 0; v <= teto; v += passo) riscos.push(v);

  return `<figure class="grafico-barras grafico-linha">
    <div class="legenda-series">
      ${SERIES.map((s) => `<span class="serie"><i style="background:${s.cor}"></i>
        <b>${esc(s.nome)}</b> <em>somando mês a mês</em></span>`).join('')}
    </div>
    <div class="tela-grafico">
    <svg viewBox="0 0 ${W} ${H}" role="img" preserveAspectRatio="xMinYMid meet"
         aria-label="Acumulado de 2026 até cada mês: ${ac.map((m) => `${m.rotulo}, ${SERIES.map((s) => `${s.nome} ${m[s.chave]}`).join(', ')}`).join('; ')}">
      ${riscos.map((v) => `<g>
        <line x1="${L}" x2="${W - R}" y1="${y(v).toFixed(1)}" y2="${y(v).toFixed(1)}" class="risco"/>
        <text x="${L - 8}" y="${(y(v) + 4).toFixed(1)}" class="rot-eixo" text-anchor="end">${v}</text>
      </g>`).join('')}
      <line x1="${L}" x2="${W - R}" y1="${T + alturaPlot}" y2="${T + alturaPlot}" class="base-eixo"/>
      ${ac.map((m, i) => `<text x="${x(i)}" y="${T + alturaPlot + 18}" class="rot-mes"
        text-anchor="middle">${esc(m.rotulo)}</text>`).join('')}
      ${SERIES.map((s) => `<polyline class="traco" stroke="${s.cor}"
        points="${ac.map((m, i) => `${x(i)},${y(m[s.chave]).toFixed(1)}`).join(' ')}"/>`).join('')}
      ${SERIES.map((s) => ac.map((m, i) => `<g class="ponto-linha">
        <title>${esc(m.rotulo)} · ${esc(s.nome)}, acumulado: ${m[s.chave]}</title>
        <circle cx="${x(i)}" cy="${y(m[s.chave]).toFixed(1)}" r="4.5" fill="${s.cor}"/>
        <circle cx="${x(i)}" cy="${y(m[s.chave]).toFixed(1)}" r="11" fill="transparent"/>
      </g>`).join('')).join('')}
      ${SERIES.map((s) => {
        const ultimo = ac[ac.length - 1];
        return `<text x="${x(ac.length - 1) + 12}" y="${(y(ultimo[s.chave]) + 4).toFixed(1)}"
          class="rot-fim" text-anchor="start">${ultimo[s.chave]}</text>`;
      }).join('')}
    </svg>
    </div>
    <figcaption>O número no fim de cada linha é onde ela chegou em agosto. Passe o
    mouse num ponto para ver o acumulado daquele mês.</figcaption>
  </figure>`;
}

/* O mês a mês do posto: a mesma sequência da planilha entregue ao gestor. */
function mesAMes() {
  const mm = D.mes_a_mes;
  if (!mm || !mm.curva?.length) return '';
  const c = mm.curva;
  const tot = (k) => c.reduce((n, x) => n + x[k], 0);
  const jan = c.find((x) => x.mes === '2026-01')?.ativos || 0;
  const janProprio = jan - mm.legado.qtd;
  const s26 = mm.serie_coep || [];
  const tot26 = (k) => s26.reduce((n, x) => n + x[k], 0);
  const t = mm.tratativas || [];
  const meses = [...new Set(t.map((x) => x.mes_resolucao))].sort();
  const conta = (lista, f) => lista.filter(f).length;
  const pct = (v, base) => `${(100 * v / (base || 1)).toFixed(1).replace('.', ',')}%`;

  return `<section class="bloco"><h3>Entrada e saída do posto em 2026</h3>
    <p class="destaque-texto">Recorte: ${esc(mm.recorte || '')}. Três leituras no mesmo eixo.
    <b>Ativos</b> é a carteira que o posto herdou — ${mm.total} do recorte, pela data de
    abertura da SS, com janeiro carregando o acervo.
    <b>Entrantes</b> é ativo novo no COEP, pela abertura da SS na base de SS/OS. <b>Resolvidos</b> é
    pelo mês em que a tratativa aconteceu — término da SS ou repasse. As três medem coisas
    diferentes e não se somam entre si: estoque parado, fluxo de chegada e fluxo de saída.</p>
    ${barrasTresColunas(c)}
    <h4 class="sub-grafico">O mesmo, somando</h4>
    <p class="destaque-texto">Onde cada série chegou até o fim de cada mês. Aqui o que conta é a
    distância entre as curvas: enquanto a laranja sobe e a verde fica no chão, a fila está
    crescendo; quando a verde encosta na laranja, o posto passou a dar conta do que entra.</p>
    ${linhaAcumulada(c)}
    ${mm.saldo?.length ? `<h4 class="sub-grafico">A carteira em movimento</h4>
    <p class="destaque-texto">O livro-caixa da carteira herdada: começa com o acervo de
    ${mm.abertura} SS de anos anteriores, cada mês soma o que abriu no próprio mês e desconta o
    que foi tratado. Janeiro: ${mm.abertura} + ${mm.saldo[0].entram} − ${mm.saldo[0].saem} =
    ${mm.saldo[0].final}, e fevereiro já começa com ${mm.saldo[0].final}.</p>
    ${livroCaixa(mm)}` : ''}
    <div class="tabela-rol" style="margin-top:18px"><table class="matriz"><thead><tr><th>Mês</th>
    <th class="num">Ativos</th><th class="num">Entrantes</th><th class="num">Resolvidos</th></tr></thead><tbody>
    ${c.map((x) => `<tr><td>${esc(x.rotulo)}${x.mes === '2026-01' ? ' <i>(com o acervo)</i>' : ''}</td>
      <td class="num">${x.ativos || '—'}</td><td class="num">${x.entrantes || '—'}</td>
      <td class="num">${x.resolvidos || '—'}</td></tr>`).join('')}
    </tbody><tfoot><tr><td>Total de 2026</td><td class="num"><b>${tot('ativos')}</b></td>
    <td class="num"><b>${tot('entrantes')}</b></td><td class="num"><b>${tot('resolvidos')}</b></td>
    </tr></tfoot></table></div>
    ${mm.fora_do_recorte?.qtd ? `<div class="nota branda" style="margin-top:12px"><strong>O que ficou fora do recorte</strong>
    Concluído conta de qualquer tipo; pendente, só se for indisponibilidade. Da foto de entrada
    fica fora ${mm.fora_do_recorte.qtd === 1 ? 'um ativo' : `${mm.fora_do_recorte.qtd} ativos`} de outro
    tipo ainda pendente: ${mm.fora_do_recorte.por_tipo.map(([t, q]) => `${q} ${esc(t.toLowerCase())}`).join(' · ')}.
    Segue na carteira de entrada.</div>` : ''}
  </section>

  <section class="bloco"><h3>O que janeiro carrega</h3>
    <p class="destaque-texto">Janeiro é metade da carteira e é quase tudo acervo: dos ${jan} ativos,
    só ${janProprio} têm SS aberta no próprio mês. Sem a regra, esses ${mm.legado.qtd} ficariam
    espalhados por 2023, 2024 e 2025 e a curva de 2026 perderia o tamanho do que foi herdado.</p>
    <div class="tabela-rol"><table class="matriz"><thead><tr><th>Origem</th>
    <th class="num">Ativos</th><th class="num">% de janeiro</th></tr></thead><tbody>
    <tr><td>SS aberta em jan/2026</td><td class="num">${janProprio}</td>
      <td class="num">${pct(janProprio, jan)}</td></tr>
    ${[...mm.legado.por_ano].reverse().map((a) => `<tr><td>Acervo — SS aberta em ${a.ano}</td>
      <td class="num">${a.qtd}</td><td class="num">${pct(a.qtd, jan)}</td></tr>`).join('')}
    </tbody><tfoot><tr><td>Total de janeiro</td><td class="num"><b>${jan}</b></td>
    <td class="num"><b>100,0%</b></td></tr></tfoot></table></div>
    ${mm.legado.mais_antiga ? `<div class="nota branda" style="margin-top:12px">
    <strong>A mais velha da carteira</strong>${esc(mm.legado.mais_antiga.numero_ss)}, ativo
    ${esc(mm.legado.mais_antiga.ativo)} em ${esc(mm.legado.mais_antiga.localidade)}, aberta em
    ${esc(dataBr(mm.legado.mais_antiga.abertura))}.</div>` : ''}
  </section>

  ${s26.length ? `<section class="bloco"><h3>Os entrantes por dentro</h3>
    <p class="destaque-texto">Duas leituras dos ${tot26('novos')} entrantes de 2026. À esquerda,
    quanto de cada mês já estava na carteira herdada e quanto é demanda que chegou por fora dela.
    À direita, quanto é SS realmente nova e quanto é SS de ano anterior que o SGM re-carimbou com
    data nova ao reabrir ou repassar.</p>
    <div class="tabela-rol"><table class="matriz"><thead><tr><th>Mês</th>
    <th class="num">Entrantes</th><th class="num">Já estavam nos ${mm.total}</th>
    <th class="num">Fora dos ${mm.total}</th><th class="num">SS do próprio ano</th>
    <th class="num">SS de ano anterior re-carimbada</th></tr></thead><tbody>
    ${s26.map((x) => `<tr><td>${esc(x.rotulo)}</td><td class="num"><b>${x.novos}</b></td>
      <td class="num">${x.na_foto || '—'}</td><td class="num">${x.fora_da_foto || '—'}</td>
      <td class="num">${x.ss_do_ano || '—'}</td><td class="num">${x.ss_recarimbada || '—'}</td></tr>`).join('')}
    </tbody><tfoot><tr><td>Total de 2026</td><td class="num"><b>${tot26('novos')}</b></td>
    <td class="num"><b>${tot26('na_foto')}</b></td><td class="num"><b>${tot26('fora_da_foto')}</b></td>
    <td class="num"><b>${tot26('ss_do_ano')}</b></td><td class="num"><b>${tot26('ss_recarimbada')}</b></td>
    </tr></tfoot></table></div>
    <div class="nota" style="margin-top:12px"><strong>Duas armadilhas na coluna de entrantes</strong>
    Dos ${tot26('novos')} entrantes, ${tot26('na_foto')} já estavam na carteira herdada — são o mesmo
    problema visto por outra base, não demanda nova. E ${tot26('ss_recarimbada')} têm número de SS de
    ano anterior com abertura em 2026, porque o SGM re-carimba a data quando a SS é reaberta ou
    repassada. Abril é o extremo: de 11 entrantes, 9 são SS re-carimbada.</div>
  </section>` : ''}

  ${meses.length ? `<section class="bloco"><h3>Quando cada um foi tratado de verdade</h3>
    <p class="destaque-texto">Mês da tratativa, não da abertura. A data é o término da SS de entrada;
    quando a SS foi repassada em vez de encerrada, vale a data do repasse. Faltando as duas, entram
    obra encerrada no AIC, reporte de campo, decisão do gestor e, por último, a SS mais recente
    atendida no ativo.</p>
    <div class="tabela-rol"><table class="matriz"><thead><tr><th>Mês da tratativa</th>
    <th class="num">Resolvidos</th><th class="num">Acumulado</th>
    <th class="num">Por cancelamento da SS</th><th class="num">Por repasse</th>
    <th class="num">Outras vias</th><th class="num">Com parecer COEP</th></tr></thead><tbody>
    ${(() => { let ac = 0; return meses.map((k) => {
      const g = t.filter((x) => x.mes_resolucao === k);
      ac += g.length;
      const canc = conta(g, (x) => x.via === 'cancelamento da SS de entrada');
      const rep = conta(g, (x) => x.via === 'repasse para a etapa seguinte');
      return `<tr><td>${rotuloMes(k)}</td><td class="num"><b>${g.length}</b></td>
        <td class="num">${ac}</td><td class="num">${canc || '—'}</td><td class="num">${rep || '—'}</td>
        <td class="num">${(g.length - canc - rep) || '—'}</td>
        <td class="num">${conta(g, (x) => x.parecer_coep) || '—'}</td></tr>`;
    }).join(''); })()}
    </tbody><tfoot><tr><td>Total</td><td class="num"><b>${t.length}</b></td><td class="num">—</td>
    <td class="num"><b>${conta(t, (x) => x.via === 'cancelamento da SS de entrada')}</b></td>
    <td class="num"><b>${conta(t, (x) => x.via === 'repasse para a etapa seguinte')}</b></td>
    <td class="num"><b>${conta(t, (x) => !['cancelamento da SS de entrada', 'repasse para a etapa seguinte'].includes(x.via))}</b></td>
    <td class="num"><b>${conta(t, (x) => x.parecer_coep)}</b></td></tr></tfoot></table></div>
    <div class="nota" style="margin-top:12px"><strong>O desenho da atuação</strong>
    ${conta(t, (x) => x.mes_resolucao >= '2026-04')} dos ${t.length} foram tratados de abril em diante.
    Maio e junho são limpeza de fila — a maioria saiu por cancelamento de SS. Julho vira o jogo: a
    maior parte sai por repasse, e é o mês em que quase todos os que tinham parecer COEP foram
    embora. Repasse quer dizer que a demanda saiu do posto, não que o serviço acabou em campo.</div>
  </section>` : ''}`;
}

/* As fotos que a equipe mandou, todas num lugar só. É a prova mais forte que
   existe: a equipe assinando que subiu no poste e trocou. */
function galeriaReportes() {
  const R = D.reportes;
  if (!R || !R.lista?.length) return '';
  const img = R.imagens || {};
  const comFoto = R.lista.filter((r) => r.imagem && img[r.imagem]);
  const anunciados = R.lista.filter((r) => !(r.imagem && img[r.imagem]) && r.anexo);
  const semAnexo = R.lista.filter((r) => !(r.imagem && img[r.imagem]) && !r.anexo);

  const cartao = (r) => {
    const foto = r.imagem && img[r.imagem];
    return `<figure class="reporte-galeria">
      ${foto ? `<a href="${foto}" target="_blank" rel="noopener">
        <img src="${foto}" loading="lazy"
          alt="Reporte de campo do ativo ${esc(r.ativo)} em ${esc(dataBr(r.data))}"></a>`
        : r.anexo
          ? `<div class="sem-foto"><b>${r.anexo.fotos} foto${r.anexo.fotos > 1 ? 's' : ''}</b>
            <span>${esc(r.anexo.estado)}</span></div>`
          : `<div class="sem-foto"><b>Sem foto</b><span>reporte só em texto</span></div>`}
      <figcaption>
        <div class="topo-galeria"><span class="cod">${esc(r.ativo)}</span>
          <span class="reporte-data">${esc(dataBr(r.data))}</span></div>
        <b>${esc(r.titulo)}</b>
        <span class="onde">${esc(r.local || r.subtitulo || '')}${r.equipe ? ` · ${esc(r.equipe)}` : ''}</span>
        ${r.etapa ? `<span class="feito">na carteira: ${esc(r.etapa)}</span>` : ''}
        ${r.servico_executado ? `<span class="feito">${esc(r.servico_executado)}</span>` : ''}
        ${r.equipamento_instalado ? `<span class="feito mono">${esc(r.equipamento_instalado)}</span>` : ''}
        ${!foto && r.anexo?.descricao ? `<span class="feito">${esc(r.anexo.descricao)}</span>` : ''}
      </figcaption>
    </figure>`;
  };

  return `<section class="bloco"><h3>As fotos de campo (${R.fotos})</h3>
    <p class="destaque-texto">Todas as fotos que a equipe mandou, num lugar só: ${R.fotos} em
    ${R.total} reportes, cobrindo ${R.ativos.length} equipamentos. Clique para abrir em tamanho
    cheio. O reporte é a equipe assinando que subiu no poste e trocou — nenhuma inferência sobre o
    texto da SS ganha disso, e é por isso que ele conta como resolução mesmo quando o SGM ainda não
    registrou nada.</p>
    <div class="galeria">${comFoto.map(cartao).join('')}</div>
    ${anunciados.length ? `<p class="destaque-texto" style="margin-top:24px">Anexo anunciado, arquivo
    ainda não veio — o que dá para ler nas fotos já está descrito aqui.</p>
    <div class="galeria">${anunciados.map(cartao).join('')}</div>` : ''}
    ${semAnexo.length ? `<p class="destaque-texto" style="margin-top:24px">Reportes só em texto.</p>
    <div class="galeria">${semAnexo.map(cartao).join('')}</div>` : ''}
  </section>`;
}

function escada() {
  const maior = Math.max(...D.por_etapa.map((e) => e.qtd));
  return `<div class="escada">${D.por_etapa.map((e) => `
    <button class="degrau ${TOM[e.etapa] || ''}" data-etapa="${esc(e.etapa)}">
      <span class="nome">${esc(e.etapa)}</span>
      <span class="barra"><i style="width:${(100 * e.qtd / maior).toFixed(1)}%"></i></span>
      <span class="lado"><b>${e.qtd}</b>${e.valor ? esc(rs(e.valor))
        : e.valor_evitado ? `<i class="evitado">${esc(rs(e.valor_evitado))} evitados</i>` : '—'}</span>
    </button>`).join('')}</div>
    <p class="destaque-texto" style="margin-top:10px">Clique numa etapa para filtrar a lista.
    O valor é o previsto na planilha de gestão — ${D.com_valor} dos ${D.total} têm valor lá.</p>`;
}

function matriz() {
  const crits = D.por_criticidade.map((c) => c.criticidade);
  const etapas = D.por_etapa.map((e) => e.etapa);
  const busca = (e, c) => D.matriz.find((x) => x.etapa === e && x.criticidade === c);
  return `<div class="tabela-rol"><table class="matriz matriz-etapa"><thead><tr><th>Etapa</th>
    ${crits.map((c) => `<th class="num">${esc(c)}</th>`).join('')}<th class="num">Total</th></tr></thead><tbody>
    ${etapas.map((e) => {
      const linha = D.por_etapa.find((x) => x.etapa === e);
      return `<tr><td><b>${esc(e)}</b></td>
        ${crits.map((c) => { const x = busca(e, c);
          return `<td class="num ${x ? '' : 'zero'}">${x ? x.qtd : '·'}</td>`; }).join('')}
        <td class="num"><b>${linha.qtd}</b></td></tr>`;
    }).join('')}
    <tr><td><b>Total</b></td>
      ${crits.map((c) => `<td class="num"><b>${D.por_criticidade.find((x) => x.criticidade === c).qtd}</b></td>`).join('')}
      <td class="num"><b>${D.total}</b></td></tr>
    </tbody></table></div>`;
}

function rol() {
  const lista = filtro ? D.lista.filter((x) => x.etapa === filtro) : D.lista;
  return `<div class="filtros">
      <button class="pastilha ${filtro ? '' : 'limpar'}" data-etapa="" aria-pressed="${!filtro}">Todos · ${D.total}</button>
      ${D.por_etapa.map((e) => `<button class="pastilha" data-etapa="${esc(e.etapa)}"
        aria-pressed="${filtro === e.etapa}">${esc(e.etapa)} <b>${e.qtd}</b></button>`).join('')}
    </div>
    <div class="tabela-rol"><table class="matriz rol"><thead><tr><th>Ativo</th><th>Localidade</th>
    <th>Tipo</th><th>Criticidade</th><th>Etapa</th><th>Parecer COEP</th><th>Check</th>
    <th class="num">Valor previsto<i class="linha-nota">em vermelho, o que teria sido gasto</i></th></tr></thead><tbody>
    ${lista.map((x) => `<tr>
      <td><b class="mono">${esc(x.ativo)}</b></td>
      <td>${esc(x.localidade || '—')}${x.polo ? `<span class="nota-campo">${esc(x.polo)}</span>` : ''}</td>
      <td>${esc(x.tipo)}</td>
      <td>${esc(x.criticidade)}</td>
      <td>${esc(x.etapa)}</td>
      <td>${esc(x.parecer || '—')}
        ${x.reporte_campo ? `<span class="reporte-selo">reporte de campo entregue${x.reporte_campo.fotos ? ` · ${x.reporte_campo.fotos} foto${x.reporte_campo.fotos > 1 ? 's' : ''}` : ''}</span>` : ''}
        ${x.o_que_trocar ? `<span class="nota-campo">troca: ${esc(x.o_que_trocar)}</span>` : ''}
        ${x.nota_campo ? `<span class="nota-campo">${esc(x.nota_campo)}</span>` : ''}
        ${x.observacao && x.observacao !== x.nota_campo ? `<span class="nota-campo">${esc(x.observacao)}</span>` : ''}</td>
      <td>${esc(x.check || '—')}</td>
      <td class="num">${x.valor ? esc(rs(x.valor))
        : x.valor_evitado ? `<i class="evitado">${esc(rs(x.valor_evitado))}</i>` : '—'}</td></tr>`).join('')}
    </tbody></table></div>`;
}

function desenhar() {
  const feito = D.feito;
  $('#pagina').innerHTML = `<div class="folha">
    <header>
      <h1>Dinâmica do posto</h1>
      <p class="sub">Onde cada um dos ${D.total} religadores e reguladores da carteira do ETO-COEP está
      hoje, pelo parecer mais recente${D.sem_parecer === 0 ? ' — e agora todos têm parecer' : ''}.
      As quatro primeiras etapas já tiveram serviço: <b>${feito.qtd} equipamentos</b>,
      ${rs(feito.valor)} de valor previsto.</p>
      <div class="carimbo">
        <span>${esc(D.fonte)}</span>
        <span>posição de ${esc(D.gerado_em.split('-').reverse().join('/'))}</span>
      </div>
    </header>

    <div class="numeros">
      ${num({ rotulo: 'Na carteira', valor: D.total, nota: D.por_tipo.map((t) => `${t.qtd} ${t.tipo}`).join(' · ') })}
      ${num({ rotulo: 'Com serviço feito', valor: feito.qtd, nota: `${Math.round(100 * feito.qtd / D.total)}% da carteira`, tom: 'bom' })}
      ${num({ rotulo: 'Na fila de compra', valor: D.por_etapa.find((e) => e.etapa === 'Em compra')?.qtd ?? 0, nota: 'esperando material', tom: 'critico' })}
      ${num({ rotulo: 'Valor previsto', valor: rs(D.valor_total), nota: `${D.com_valor} ativos orçados — os cancelados não entram` })}
      ${D.economia ? num({ rotulo: 'O que teria sido gasto', valor: rs(D.economia.total), nota: `${D.economia.total_ativos} cancelados em operação`, tom: 'evitado' }) : ''}
    </div>

    <section class="bloco"><h3>A escada</h3>${escada()}</section>

    ${mesAMes()}

    ${D.economia ? `<section class="bloco"><h3>O que teria sido gasto nos cancelados em operação</h3>
      <p class="destaque-texto">${esc(D.economia.criterio)}</p>
      <div class="numeros">
        ${num({ rotulo: 'O que teria sido gasto', valor: rs(D.economia.total), nota: `${D.economia.total_ativos} equipamentos, material + mão de obra`, tom: 'evitado' })}
        ${num({ rotulo: 'Material de catálogo', valor: rs(D.economia.material), nota: `mão de obra de campo: ${rs(D.economia.mao_de_obra)}` })}
        ${num({ rotulo: 'Com peça identificada', valor: D.economia.com_material, nota: `${D.economia.sem_material} não precisavam de peça · ${D.economia.indeterminados} sem laudo que decida` })}
        ${D.economia.orcado ? num({ rotulo: 'Ainda dentro do orçamento', valor: rs(D.economia.orcado.liberavel), nota: `${D.economia.orcado.com_custo} cancelados com custo lançado — dinheiro a liberar`, tom: 'evitado' }) : ''}
      </div>
      ${(D.economia.decisoes || []).length ? `<div class="decisoes">
      ${D.economia.decisoes.map((x) => `<div class="nota branda"><strong>${esc(x.titulo)}</strong>${esc(x.texto)}</div>`).join('')}
      </div>` : ''}
      <div class="tabela-rol"><table class="matriz economia"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>Criticidade</th><th>Tensão</th><th>Peça que teria sido comprada</th>
      <th class="num">Material</th><th class="num">Mão de obra</th><th class="num">Total</th>
      <th>Fonte do valor</th></tr></thead><tbody>
      ${D.economia.lista.map((x) => `<tr class="cabeca">
        <td><b class="mono">${esc(x.ativo)}</b></td><td>${esc(x.localidade || '—')}</td>
        <td>${esc(x.criticidade || '—')}</td>
        <td>${esc(x.classe_tensao || '—')}${x.kva ? `<br>${x.kva} kVA` : ''}</td>
        <td>${x.linhas.length ? x.linhas.map((l) => `${esc(l.descricao)}${l.qtd > 1 ? ` × ${l.qtd}` : ''} <span class="mono">${esc(l.codigo)}</span>`).join('<br>')
          : `<i>${x.veredito === 'sem_material' ? 'não precisava de peça' : 'o laudo não permite dizer'}</i>`}</td>
        <td class="num">${x.material ? esc(rs(x.material)) : '—'}</td>
        <td class="num">${x.mao_de_obra ? esc(rs(x.mao_de_obra)) : '—'}</td>
        <td class="num">${x.valor ? `<i class="evitado"><b>${esc(rs(x.valor))}</b></i>` : '—'}</td>
        <td>${esc(x.fonte)}${x.no_orcamento ? `<br><i>aba «${esc(x.no_orcamento)}»</i>` : ''}</td></tr>
        ${x.nota ? `<tr class="rodape-linha"><td colspan="9">${esc(x.nota)}</td></tr>` : ''}`).join('')}
      </tbody><tfoot><tr><td colspan="5">Total</td>
      <td class="num"><b>${esc(rs(D.economia.material))}</b></td>
      <td class="num"><b>${esc(rs(D.economia.mao_de_obra))}</b></td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.total))}</b></i></td>
      <td></td></tr></tfoot></table></div>

      ${D.economia.orcado ? `<div class="nota" style="margin-top:16px"><strong>Você tinha razão: parte dos cancelados ainda está orçada</strong>
      ${D.economia.orcado.citados} dos ${D.economia.total_ativos} aparecem no ORCAMENTO_EQ_ESPECIAIS revisado.
      ${D.economia.orcado.com_custo} deles estão nas abas que somam no orçamento, com
      ${esc(rs(D.economia.orcado.liberavel))} de custo lançado para equipamento que já está rodando.
      Esse é o valor que dá para liberar da fila de compra sem mexer em mais nada. Os outros
      ${D.economia.orcado.citados - D.economia.orcado.com_custo} estão em «Repassados» e «Em Análise», que já ficam fora da conta.</div>
      <div class="tabela-rol" style="margin-top:10px"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>SS</th><th>Aba do orçamento</th><th class="num">Valor lançado</th></tr></thead><tbody>
      ${D.economia.orcado.ativos.map((l) => `<tr><td><b class="mono">${esc(l.ativo)}</b></td>
        <td>${esc(l.localidade)}</td><td class="mono">${esc(l.ss)}</td><td>${esc(l.aba)}</td>
        <td class="num">${l.soma ? `<i class="evitado">${esc(rs(l.valor))}</i>` : '<i>fora do total</i>'}</td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="4">A liberar da fila de compra</td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.orcado.liberavel))}</b></i></td></tr></tfoot></table></div>` : ''}

      ${D.economia.teto ? `<div class="nota" style="margin-top:16px"><strong>O teto, se os ${D.economia.teto.ativos} indeterminados se confirmarem</strong>
      Estes não têm laudo que nomeie a peça e ficam em R$ 0 no número oficial, por instrução de errar para baixo.
      Se os três laudos vierem como o texto sugere, entram mais ${esc(rs(D.economia.teto.extra))} e o total vai a
      ${esc(rs(D.economia.teto.valor))}.</div>
      <div class="tabela-rol" style="margin-top:10px"><table class="matriz"><thead><tr><th>Ativo</th><th>Localidade</th>
      <th>Peça provável</th><th>O que falta para decidir</th><th class="num">Valor em aberto</th></tr></thead><tbody>
      ${D.economia.teto.linhas.map((l) => `<tr><td><b class="mono">${esc(l.ativo)}</b></td>
        <td>${esc(l.localidade)}</td><td>${esc(l.peca)}</td>
        <td>${esc(l.porque)}</td><td class="num"><i class="evitado">${esc(rs(l.valor))}</i></td></tr>`).join('')}
      </tbody><tfoot><tr><td colspan="4">Total em aberto</td>
      <td class="num"><i class="evitado"><b>${esc(rs(D.economia.teto.extra))}</b></i></td></tr></tfoot></table></div>` : ''}
    </section>` : ''}

    <section class="bloco"><h3>Etapa × criticidade</h3>
      <p class="destaque-texto">Onde está o risco: quantos de cada criticidade em cada etapa.</p>
      ${matriz()}</section>

    ${galeriaReportes()}

    ${D.notas_campo.length ? `<section class="bloco"><h3>O que o campo anotou (${D.notas_campo.length})</h3>
      <div class="itens">${D.notas_campo.map((x) => `<div class="item-linha">
        <span><b class="mono">${esc(x.ativo)}</b> · ${esc(x.localidade)}
        <i class="linha-nota">${esc(x.nota_campo)}</i></span>
        <b>${esc(x.etapa)}</b></div>`).join('')}</div></section>` : ''}

    ${(D.ajustes || []).length ? `<section class="bloco"><h3>Ajustes que você mandou fazer</h3>
      <div class="itens">${D.ajustes.map((a) => `<div class="item-linha">
        <span><b class="mono">${esc(a.ativo)}</b> · ${esc(a.localidade)} — ${esc(a.o_que_trocar)}
        <i class="linha-nota">${esc(a.motivo)}</i></span><b>${esc(rs(a.valor))}</b></div>`).join('')}</div>
      </section>` : ''}

    <section class="bloco"><h3>A carteira inteira</h3>${rol()}</section>
  </div>`;

  document.querySelectorAll('[data-etapa]').forEach((b) => b.addEventListener('click', () => {
    const e = b.dataset.etapa;
    filtro = (!e || filtro === e) ? null : e;
    desenhar();
    if (filtro) document.querySelector('.rol')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }));
}

desenhar();
