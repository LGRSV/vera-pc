"""
Prontuário de Falhas do DCMD — o painel da leitura das 497 cadeias.

`falha_dcmd_mae.py` lê e consolida; este monta a página. O que o gestor pediu, na ordem
em que pediu: a mensalização das falhas dividida em RL e RT, o defeito de origem (tanque
ou controle) e as marcas.

Três decisões de desenho que valem registro:

- **Duas escalas, dois gráficos.** As falhas vão de 0 a 19 por mês; as demandas que
  chegaram ao posto vão a 57. Pôr as duas no mesmo eixo esmaga a série que interessa, e
  dois eixos Y no mesmo gráfico é proibido pela régua de dataviz do projeto. Então são
  dois gráficos empilhados, cada um com sua escala, lendo o mesmo eixo de meses.
- **O eixo é contínuo de jan/2024 a jul/2025**, 19 meses, sem cortar no ano. É o único
  jeito de a queda de agosto/2025 aparecer pelo que é: o fim da base, não melhora do
  parque. A faixa hachurada marca o que a planilha mãe não alcança.
- **A marca sai do cadastro de ajuste**, não de base de SS. O denominador honesto dela é
  o parque DESSES cadastros (1.293 RL e 189 RT), não os 1.307/207 oficiais — senão o
  índice de quem não tem cadastro vira zero por omissão.

Rodar: python3 scripts/painel_falha_dcmd.py  → scratchpad/painel_falha_dcmd.html
"""

import json
import os
from collections import Counter

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "data", "missao", "falha_dcmd_artifact.json")
SAIDA = os.path.join(RAIZ, "scratchpad", "painel_falha_dcmd.html")

CORTE = "2025-07-11"        # última abertura da planilha mãe
EIXO = [(2024, m) for m in range(1, 13)] + [(2025, m) for m in range(1, 13)]
ULTIMO = 19   # jul/2025 é o último mês que a planilha mãe alcança


def contexto():
    """Quantas cadeias chegaram ao posto em cada mês — o denominador do gráfico de baixo."""
    import sys
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    import falha_dcmd_mae as m
    reg, prox, comeco = m.ler()
    cads = m.recorte(reg, prox, comeco)
    c = Counter((reg[x[0]]["abert"].year, reg[x[0]]["abert"].month) for x in cads)
    return [c.get(k, 0) for k in EIXO]


def monta():
    d = json.load(open(DADOS))
    eq = d["equipamentos"]
    payload = {
        "eq": eq,
        "eixo": [list(k) for k in EIXO],
        "chegaram": contexto(),
        "parque": d["parque_marca"],
        "cadeias": d["cadeias_lidas"],
        "com_falha": d["cadeias_com_falha"],
        "corte": CORTE,
        "ultimo": ULTIMO,
    }
    html = MOLDE.replace("/*DADOS*/", json.dumps(payload, ensure_ascii=False))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w") as f:
        f.write(html)
    print(SAIDA, "·", len(html), "bytes ·", len(eq), "equipamentos")
    return SAIDA


MOLDE = r"""
<title>Prontuário de Falhas do DCMD</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Spectral:ital,wght@0,400;0,600;1,400&display=swap">
<style>
:root{
  color-scheme: light;
  --papel:#f2efe6; --papel-2:#e9e5d8; --papel-3:#dfdac9;
  --tinta:#211d15; --tinta-2:#57513f; --tinta-3:#8d8672;
  --filete:#c8c2af; --filete-2:#a49d87;
  --sinal:#bc4b0e; --sinal-papel:#f3e0d2;
  --rl:#2f56b0; --rt:#bc4b0e;
  --p-tanque:#2f56b0; --p-controle:#bc4b0e; --p-completo:#2e7f52;
  --p-celula:#7a4b9c; --p-furto:#8c2f22; --p-rele:#8d8672;
  --ghost:#cfc8b4;
  --cond:"Barlow Condensed","Arial Narrow","Helvetica Neue",sans-serif;
  --leitura:"Spectral",Georgia,"Times New Roman",serif;
  --mono:"IBM Plex Mono",ui-monospace,Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme: dark;
    --papel:#191713; --papel-2:#221f1a; --papel-3:#2c2820;
    --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
    --filete:#403a2e; --filete-2:#5b5443;
    --sinal:#e0703a; --sinal-papel:#33231a;
    --rl:#6b8fe0; --rt:#e0703a;
    --p-tanque:#6b8fe0; --p-controle:#e0703a; --p-completo:#35a58c;
    --p-celula:#a884cc; --p-furto:#d96a55; --p-rele:#7c7563;
    --ghost:#3b3529;
  }
}
:root[data-theme="dark"]{
  color-scheme: dark;
  --papel:#191713; --papel-2:#221f1a; --papel-3:#2c2820;
  --tinta:#e8e3d4; --tinta-2:#b3ac97; --tinta-3:#7c7563;
  --filete:#403a2e; --filete-2:#5b5443;
  --sinal:#e0703a; --sinal-papel:#33231a;
  --rl:#6b8fe0; --rt:#e0703a;
  --p-tanque:#6b8fe0; --p-controle:#e0703a; --p-completo:#35a58c;
  --p-celula:#a884cc; --p-furto:#d96a55; --p-rele:#7c7563;
  --ghost:#3b3529;
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--papel); color:var(--tinta);
  font-family:var(--leitura); font-size:15px; line-height:1.55;
  -webkit-font-smoothing:antialiased;
}
.folha{max-width:1080px; margin:0 auto; padding:0 20px; padding-block:0 64px}

/* ---------------------------------------------------------------- cabeçalho */
.masthead{border-bottom:3px double var(--filete-2); padding-block:34px 14px; margin-bottom:26px}
.carimbo{
  display:inline-block; font-family:var(--mono); font-size:10.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--sinal); border:1px solid var(--sinal);
  background:var(--sinal-papel); padding:3px 9px; border-radius:2px; margin-bottom:14px;
}
h1{
  font-family:var(--cond); font-weight:700; font-size:clamp(34px,6.4vw,54px);
  line-height:.98; margin:0 0 10px; letter-spacing:-.005em; text-wrap:balance;
}
.subtitulo{
  font-family:var(--leitura); font-size:16px; color:var(--tinta-2);
  max-width:62ch; margin:0 0 20px;
}
.subtitulo em{color:var(--tinta); font-style:italic}

.placa{
  display:grid; grid-template-columns:repeat(auto-fit,minmax(138px,1fr));
  gap:0; border-top:1px solid var(--filete); border-left:1px solid var(--filete);
}
.placa div{
  border-right:1px solid var(--filete); border-bottom:1px solid var(--filete);
  padding:11px 13px; background:var(--papel-2);
}
.placa dt{
  font-family:var(--mono); font-size:9.5px; letter-spacing:.11em; text-transform:uppercase;
  color:var(--tinta-3); margin:0 0 3px;
}
.placa dd{
  margin:0; font-family:var(--cond); font-weight:600; font-size:27px; line-height:1;
  font-variant-numeric:tabular-nums;
}
.placa dd small{font-size:13px; font-weight:500; color:var(--tinta-2); margin-left:4px}

/* ---------------------------------------------------------------- seções */
section{margin-top:44px}
h2{
  font-family:var(--cond); font-weight:600; font-size:26px; margin:0 0 4px;
  letter-spacing:.005em; text-wrap:balance;
}
h2 .ordem{
  font-family:var(--mono); font-size:11px; color:var(--sinal); letter-spacing:.1em;
  vertical-align:.5em; margin-right:9px;
}
.lede{color:var(--tinta-2); max-width:66ch; margin:0 0 20px; font-size:14.5px}
.lede strong{color:var(--tinta); font-weight:600}

.aviso{
  border-left:3px solid var(--sinal); background:var(--sinal-papel);
  padding:12px 15px; margin:0 0 22px; font-size:14px; color:var(--tinta);
  max-width:72ch;
}
.aviso b{font-family:var(--cond); font-weight:600; letter-spacing:.01em}

/* ---------------------------------------------------------------- gráfico */
.quadro{border:1px solid var(--filete); background:var(--papel-2); padding:16px 14px 10px}
.quadro + .quadro{border-top:none}
.quadro-cab{
  display:flex; flex-wrap:wrap; gap:10px 18px; align-items:baseline;
  justify-content:space-between; margin-bottom:12px;
}
.quadro-tit{
  font-family:var(--mono); font-size:10px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--tinta-3);
}
svg{display:block; width:100%; height:auto; overflow:visible}
.gx{font-family:var(--mono); font-size:8.5px; fill:var(--tinta-3)}
.gy{font-family:var(--mono); font-size:9px; fill:var(--tinta-3)}
.grade{stroke:var(--filete); stroke-width:.6}
.eixo{stroke:var(--filete-2); stroke-width:1}
.vnum{font-family:var(--mono); font-size:9.5px; font-weight:600; fill:var(--tinta-2)}
.anolab{font-family:var(--cond); font-size:12px; font-weight:600; fill:var(--tinta-2); letter-spacing:.06em}

.chaves{display:flex; gap:0; border:1px solid var(--filete-2); border-radius:2px; overflow:hidden}
.chaves button{
  font-family:var(--mono); font-size:10px; letter-spacing:.08em; text-transform:uppercase;
  border:none; background:var(--papel); color:var(--tinta-2); padding:6px 12px; cursor:pointer;
  border-right:1px solid var(--filete);
}
.chaves button:last-child{border-right:none}
.chaves button[aria-pressed="true"]{background:var(--tinta); color:var(--papel)}
.chaves button:focus-visible{outline:2px solid var(--sinal); outline-offset:-2px}

.legenda{display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:12px; padding-top:11px; border-top:1px solid var(--filete)}
.legenda span{
  display:inline-flex; align-items:center; gap:6px;
  font-family:var(--mono); font-size:10px; letter-spacing:.06em; color:var(--tinta-2);
}
.legenda i{width:11px; height:11px; border-radius:1px; display:inline-block}

/* ---------------------------------------------------------------- tabelas */
.rolo{overflow-x:auto; border:1px solid var(--filete)}
table{border-collapse:collapse; width:100%; font-family:var(--cond); font-size:14.5px}
caption{
  text-align:left; font-family:var(--mono); font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--tinta-3); padding:10px 12px 8px; background:var(--papel-2);
  border-bottom:1px solid var(--filete);
}
th{
  background:var(--tinta); color:var(--papel); font-weight:600; font-size:11px;
  font-family:var(--mono); letter-spacing:.07em; text-transform:uppercase;
  padding:8px 10px; text-align:left; white-space:nowrap; position:sticky; top:0;
}
td{padding:6px 10px; border-bottom:1px solid var(--filete); vertical-align:top}
tbody tr:nth-child(even){background:var(--papel-2)}
.num{text-align:right; font-family:var(--mono); font-size:12.5px; font-variant-numeric:tabular-nums}
.cod{font-family:var(--mono); font-size:12.5px; letter-spacing:-.01em}
.barra{display:block; height:7px; border-radius:1px; min-width:2px}
.barra-cel{width:110px; padding-top:11px}

.pill{
  display:inline-block; font-family:var(--mono); font-size:9.5px; letter-spacing:.07em;
  text-transform:uppercase; padding:2px 7px; border-radius:9px; border:1px solid;
  white-space:nowrap;
}
.pill.tanque{color:var(--p-tanque); border-color:var(--p-tanque)}
.pill.controle{color:var(--p-controle); border-color:var(--p-controle)}
.pill.completo{color:var(--p-completo); border-color:var(--p-completo)}
.pill.celula{color:var(--p-celula); border-color:var(--p-celula)}
.pill.furto{color:var(--p-furto); border-color:var(--p-furto)}
.pill.rele{color:var(--p-rele); border-color:var(--p-rele)}
.tipo{font-family:var(--mono); font-size:11px; font-weight:600; letter-spacing:.06em}
.tipo.RL{color:var(--rl)} .tipo.RT{color:var(--rt)}
.sim{color:var(--p-completo); font-family:var(--mono); font-size:11px}
.nao{color:var(--sinal); font-family:var(--mono); font-size:11px}

/* ---------------------------------------------------------------- filtros */
.filtros{display:flex; flex-wrap:wrap; gap:9px; align-items:center; margin-bottom:14px}
.filtros label{
  font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--tinta-3); margin-right:-4px;
}
select,input[type=search]{
  font-family:var(--cond); font-size:14px; padding:5px 9px; color:var(--tinta);
  background:var(--papel); border:1px solid var(--filete-2); border-radius:2px;
}
select:focus-visible,input:focus-visible{outline:2px solid var(--sinal); outline-offset:1px}
.contador{font-family:var(--mono); font-size:11px; color:var(--tinta-3); margin-left:auto}

/* ---------------------------------------------------------------- método */
.metodo{
  border-top:3px double var(--filete-2); margin-top:52px; padding-top:22px;
  columns:2; column-gap:38px; font-size:14px; color:var(--tinta-2);
}
.metodo h3{
  font-family:var(--mono); font-size:10px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--sinal); margin:0 0 5px; break-after:avoid;
}
.metodo p{margin:0 0 16px; break-inside:avoid; max-width:46ch}
.metodo b{color:var(--tinta); font-weight:600}
.metodo code{font-family:var(--mono); font-size:12px; color:var(--tinta)}
@media (max-width:760px){.metodo{columns:1}}

.rodape{
  margin-top:34px; padding-top:14px; border-top:1px solid var(--filete);
  font-family:var(--mono); font-size:10px; letter-spacing:.06em; color:var(--tinta-3);
  display:flex; flex-wrap:wrap; gap:6px 18px;
}
@media (prefers-reduced-motion:no-preference){
  rect.anim{animation:sobe .5s cubic-bezier(.2,.7,.3,1) backwards}
  @keyframes sobe{from{transform:scaleY(0)}}
}
</style>

<div class="folha">

<header class="masthead">
  <div class="carimbo">ETO-COEP · leitura das SS que passaram pelo DCMD</div>
  <h1>Prontuário de Falhas do DCMD</h1>
  <p class="subtitulo">
    As <em>497 cadeias</em> de religador e regulador que chegaram a um posto do DCMD
    entre 2024 e 2025, lidas parecer a parecer. Cada linha abaixo é um equipamento que
    exigiu <em>peça grande</em> — tanque, controle, célula ou o equipamento inteiro —
    datado pela abertura da primeira SS, antes de a demanda chegar ao posto.
  </p>
  <dl class="placa" id="placa"></dl>
</header>

<section>
  <h2><span class="ordem">01</span>A mensalização</h2>
  <p class="lede">
    Falhas por mês de <strong>abertura da primeira SS</strong>, de janeiro de 2024 a
    julho de 2025. O eixo corre contínuo pelos dois anos de propósito: é assim que se vê
    que a série não cai em agosto de 2025 — ela <strong>acaba</strong>.
  </p>

  <div class="quadro">
    <div class="quadro-cab">
      <span class="quadro-tit">Equipamentos que falharam no mês</span>
      <div class="chaves" role="group" aria-label="Como dividir as barras">
        <button id="bt-tipo" aria-pressed="true">por tipo</button>
        <button id="bt-peca" aria-pressed="false">por peça</button>
      </div>
    </div>
    <svg id="g-falhas" viewBox="0 0 1000 300" role="img"
         aria-label="Falhas por mês, janeiro de 2024 a julho de 2025"></svg>
    <div class="legenda" id="leg-falhas"></div>
  </div>

  <div class="quadro">
    <div class="quadro-cab">
      <span class="quadro-tit">Contexto — demandas que chegaram ao posto no mês</span>
      <span class="quadro-tit">escala própria · 0 a 60</span>
    </div>
    <svg id="g-ctx" viewBox="0 0 1000 130" role="img"
         aria-label="Demandas que chegaram ao posto por mês"></svg>
  </div>
</section>

<section>
  <h2><span class="ordem">02</span>O defeito de origem</h2>
  <p class="lede">
    A peça que o parecer mandou trocar. No religador o defeito se reparte entre
    <strong>tanque</strong> (a parte ativa) e <strong>controle</strong>; quando os dois
    vão juntos, o parecer pede o <strong>equipamento completo</strong>, que é a categoria
    própria. No regulador quase tudo é <strong>célula</strong> — o banco é de três, e a
    falha de uma é falha do banco.
  </p>
  <div class="rolo">
    <table id="t-peca">
      <caption>Defeito por tipo e ano · equipamentos, não ocorrências</caption>
      <thead><tr>
        <th>Peça</th><th>Tipo</th><th class="num">2024</th><th class="num">2025</th>
        <th class="num">Total</th><th class="num">Trocado</th><th>Participação</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<section>
  <h2><span class="ordem">03</span>As marcas</h2>
  <p class="lede">
    A marca não existe em base de SS nenhuma: vem do <strong>cadastro de ajuste da
    proteção</strong> — a coluna RELÉ no religador, PARTE ATIVA no regulador. Por isso o
    denominador aqui é o parque <strong>desse cadastro</strong>, 1.293 RL e 189 RT, e não
    os 1.307 e 207 oficiais. O <strong>índice</strong> é a fatia das falhas dividida pela
    fatia do parque: acima de 1,00 a marca falha mais do que o tamanho dela explica.
  </p>
  <div class="rolo">
    <table id="t-marca">
      <caption>Marca · parque do cadastro de ajuste contra as falhas lidas</caption>
      <thead><tr>
        <th>Marca</th><th>Tipo</th><th class="num">Parque</th><th class="num">Falhas</th>
        <th class="num">% do parque que falhou</th><th class="num">Índice</th><th>Escala do índice</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="aviso" id="aviso-misto"></div>
</section>

<section>
  <h2><span class="ordem">04</span>A lista</h2>
  <p class="lede">
    Um equipamento por linha, por ano. Ativo que saiu de operação duas vezes no mesmo ano
    aparece uma vez — a coluna <strong>cadeias</strong> diz quantas demandas distintas ele
    gerou. Clique numa peça ou numa marca acima para filtrar aqui.
  </p>
  <div class="filtros">
    <label for="f-ano">Ano</label><select id="f-ano"></select>
    <label for="f-tipo">Tipo</label><select id="f-tipo"></select>
    <label for="f-peca">Peça</label><select id="f-peca"></select>
    <label for="f-marca">Marca</label><select id="f-marca"></select>
    <input type="search" id="f-busca" placeholder="ativo, praça ou SS" aria-label="Buscar">
    <span class="contador" id="contador"></span>
  </div>
  <div class="rolo">
    <table id="t-lista">
      <thead><tr>
        <th>Ativo</th><th>Tipo</th><th>Praça</th><th class="num">Mês</th>
        <th>Peça</th><th>Marca</th><th>Trocado</th><th class="num">Cadeias</th>
        <th>Primeira SS</th><th>Caminho no SGM</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<div class="metodo">
  <h3>A fonte</h3>
  <p>
    <b>Religa_Regula_2025.xlsx</b>, aba «Exportar Planilha»: 7.638 SS, 7.634 com parecer.
    É a única base que traz o texto técnico junto da cadeia já montada — o recorte local
    de SS/OS não tem descrição, e a base crua de 36 MB está fora do repositório.
  </p>

  <h3>A cadeia</h3>
  <p>
    A coluna <code>Primeiro</code> marca o começo e a coluna <code>hierarquia</code> dá o
    elo seguinte. O SGM abre SS nova a cada passagem de posto, mas repasse não é falha
    nova: <b>a cadeia inteira é uma falha só</b>. Das 497, <b>124</b> tinham peça grande.
  </p>

  <h3>A data</h3>
  <p>
    A falha é datada pela <b>abertura da primeira SS da cadeia</b>, antes de a demanda
    chegar ao DCMD — foi o pedido do gestor. A SS do DCMD é sempre posterior; datar por
    ela joga a falha meses para a frente.
  </p>

  <h3>O que conta como falha</h3>
  <p>
    Só peça grande, pela régua de 21/08/2026. Religador: controle, tanque/parte ativa ou o
    equipamento completo. Regulador: célula, relé, o banco completo ou furto. Contam como
    controle a placa de alimentação CA, o relé de sincronismo, o armário de controle e o
    retrofit. <b>Não contam</b>: placa de comunicação, placa 3G, rádio e antena — é
    telecom. Fora também trafo auxiliar, chave faca, bateria, aterramento, cabo, conector,
    poste, poda, ajuste de proteção, comissionamento e obra de equipamento novo.
  </p>

  <h3>Como se conta</h3>
  <p>
    <b>Equipamento, não ocorrência.</b> Ativo que falhou duas vezes no mesmo ano conta uma
    vez naquele ano — e conta de novo se falhar em outro ano. São 124 cadeias com peça
    grande em <b>107 equipamentos-ano</b>.
  </p>

  <h3>A leitura</h3>
  <p>
    Cada cadeia foi lida por inteiro, parecer por parecer, por dez leitores em paralelo —
    não por palavra-chave. A triagem por regex de peça foi testada e <b>reprovada</b>:
    deixou escapar 6 das 21 falhas conhecidas de 2025, 29% de fuga.
  </p>

  <h3>As quatro armadilhas</h3>
  <p>
    <b>1.</b> A descrição é cumulativa — o SGM cola parecer novo por cima do antigo, sem
    separador; vale o mais recente. <b>2.</b> Texto de terceiro: laudo de outro ativo
    colado na descrição, conferido pelo código em cada caso. <b>3.</b> «Equipamento ficou
    em operação? NÃO» significa que <b>não</b> ficou. <b>4.</b> Quando a SS e a OS
    discordam, vale a OS.
  </p>

  <h3>O horizonte</h3>
  <p>
    A planilha mãe fecha em <b>11/07/2025</b>. Não há uma única SS depois dessa data, então
    julho de 2025 é mês parcial e agosto em diante não existe na base. A faixa hachurada no
    gráfico marca esse limite: <b>a queda não é melhora do parque, é o fim do dado</b>.
  </p>
</div>

<div class="rodape">
  <span>Fonte: Religa_Regula_2025.xlsx · aba Exportar Planilha</span>
  <span>Marca: GESTÃO DE EQUIPAMENTOS · abas de ajuste da proteção</span>
  <span>Posição: 11/07/2025</span>
</div>

</div>

<script>
const D = /*DADOS*/;
const MES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const MESL = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
              "setembro","outubro","novembro","dezembro"];
const PECAS = ["tanque","controle","completo","celula","rele","furto"];
const PECA_NOME = {tanque:"Tanque / parte ativa", controle:"Controle", completo:"Equipamento completo",
                   celula:"Célula", rele:"Relé", furto:"Furto"};
const cor = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();

const eixo = D.eixo, N = eixo.length;
const eq = D.eq;

/* ------------------------------------------------------------------ placa */
(function(){
  const rl = eq.filter(e=>e.fam==="RL").length, rt = eq.filter(e=>e.fam==="RT").length;
  const troc = eq.filter(e=>e.executada).length;
  const itens = [
    ["Cadeias lidas", D.cadeias, ""],
    ["Com peça grande", D.com_falha, "cadeias"],
    ["Equipamentos-ano", eq.length, ""],
    ["Religadores", rl, ""],
    ["Reguladores", rt, ""],
    ["Troca confirmada", troc, "de "+eq.length],
  ];
  document.getElementById("placa").innerHTML = itens.map(([t,v,s])=>
    `<div><dt>${t}</dt><dd>${v}${s?`<small>${s}</small>`:""}</dd></div>`).join("");
})();

/* ------------------------------------------------------------------ séries */
function serie(chave){
  // chave: "tipo" -> [RL, RT] ; "peca" -> uma faixa por peça presente
  const grupos = chave==="tipo"
    ? [{k:"RL", rot:"Religador", c:"--rl", f:e=>e.fam==="RL"},
       {k:"RT", rot:"Regulador", c:"--rt", f:e=>e.fam==="RT"}]
    : PECAS.filter(p=>eq.some(e=>e.peca===p))
           .map(p=>({k:p, rot:PECA_NOME[p], c:"--p-"+p, f:e=>e.peca===p}));
  return grupos.map(g=>({...g, v: eixo.map(([a,m])=>
    eq.filter(e=>e.ano===a && e.mes===m).filter(g.f).length)}));
}

/* ------------------------------------------------------------------ gráfico */
const W=1000, H=300, ML=34, MR=8, MT=14, MB=44;
const IW = W-ML-MR, IH = H-MT-MB;
const passo = IW/N, larg = Math.min(passo-6, 34);

function desenha(chave){
  const gs = serie(chave);
  const totais = eixo.map((_,i)=>gs.reduce((s,g)=>s+g.v[i],0));
  const topo = 20;
  const y = v => MT + IH - (v/topo)*IH;
  let s = "";

  // grade e eixo Y
  for(let v=0; v<=topo; v+=5){
    s += `<line class="grade" x1="${ML}" y1="${y(v)}" x2="${W-MR}" y2="${y(v)}"/>`;
    s += `<text class="gy" x="${ML-7}" y="${y(v)+3}" text-anchor="end">${v}</text>`;
  }
  s += `<line class="eixo" x1="${ML}" y1="${y(0)}" x2="${W-MR}" y2="${y(0)}"/>`;

  // faixa do que a base não alcança (depois de jul/2025)
  const xFim = ML + D.ultimo*passo;
  s += `<defs><pattern id="hach" width="7" height="7" patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="7" stroke="${cor("--filete")}" stroke-width="2"/>
        </pattern></defs>`;
  s += `<rect x="${xFim}" y="${MT}" width="${ML+N*passo-xFim}" height="${IH}" fill="url(#hach)" opacity=".5"/>`;
  s += `<line class="eixo" x1="${xFim}" y1="${MT}" x2="${xFim}" y2="${MT+IH}" stroke-dasharray="3 3"/>`;

  // barras empilhadas
  eixo.forEach(([a,m],i)=>{
    const x = ML + i*passo + (passo-larg)/2;
    let acc = 0;
    gs.forEach((g,gi)=>{
      const v = g.v[i];
      if(!v) return;
      const alt = (v/topo)*IH;
      const yy = y(acc+v);
      s += `<rect class="anim" x="${x}" y="${yy}" width="${larg}" height="${alt}"
              fill="${cor(g.c)}" style="transform-origin:${x}px ${y(acc)}px; animation-delay:${i*22}ms">
              <title>${MESL[m-1]} de ${a} — ${g.rot}: ${v}</title></rect>`;
      acc += v;
    });
    if(totais[i]) s += `<text class="vnum" x="${x+larg/2}" y="${y(acc)-5}" text-anchor="middle">${totais[i]}</text>`;
    s += `<text class="gx" x="${x+larg/2}" y="${MT+IH+14}" text-anchor="middle">${MES[m-1]}</text>`;
  });

  // réguas de ano
  [[0,12,"2024"],[12,24,"2025"]].forEach(([a,b,rot])=>{
    const x1 = ML + a*passo + 3, x2 = ML + b*passo - 3;
    s += `<line class="eixo" x1="${x1}" y1="${MT+IH+24}" x2="${x2}" y2="${MT+IH+24}"/>`;
    s += `<text class="anolab" x="${(x1+x2)/2}" y="${MT+IH+38}" text-anchor="middle">${rot}</text>`;
  });
  const xm = (xFim + ML + N*passo)/2;
  s += `<text class="anolab" x="${xm}" y="${MT+IH/2-6}" text-anchor="middle"
          fill="${cor("--tinta-3")}">a base acaba</text>`;
  s += `<text class="anolab" x="${xm}" y="${MT+IH/2+10}" text-anchor="middle"
          fill="${cor("--tinta-3")}">em 11/07/2025</text>`;

  document.getElementById("g-falhas").innerHTML = s;
  document.getElementById("leg-falhas").innerHTML = gs.map(g=>{
    const t = g.v.reduce((x,z)=>x+z,0);
    return `<span><i style="background:${cor(g.c)}"></i>${g.rot} · ${t}</span>`;
  }).join("");
}

/* ------------------------------------------------------------------ contexto */
(function(){
  const CH=130, cMT=10, cMB=18, cIH=CH-cMT-cMB, topo=60;
  const y = v => cMT + cIH - (v/topo)*cIH;
  let s = "";
  for(let v=0; v<=topo; v+=20){
    s += `<line class="grade" x1="${ML}" y1="${y(v)}" x2="${W-MR}" y2="${y(v)}"/>`;
    s += `<text class="gy" x="${ML-7}" y="${y(v)+3}" text-anchor="end">${v}</text>`;
  }
  D.chegaram.forEach((v,i)=>{
    if(i >= D.ultimo) return;
    const x = ML + i*passo + (passo-larg)/2;
    const [a,m] = eixo[i];
    s += `<rect x="${x}" y="${y(v)}" width="${larg}" height="${(v/topo)*cIH}" fill="${cor("--ghost")}">
            <title>${MESL[m-1]} de ${a} — ${v} demandas chegaram ao posto</title></rect>`;
    s += `<text class="gx" x="${x+larg/2}" y="${y(v)-4}" text-anchor="middle">${v}</text>`;
  });
  s += `<line class="eixo" x1="${ML}" y1="${y(0)}" x2="${W-MR}" y2="${y(0)}"/>`;
  document.getElementById("g-ctx").innerHTML = s;
})();

/* ------------------------------------------------------------------ peça */
(function(){
  const linhas = [];
  ["RL","RT"].forEach(fam=>{
    PECAS.forEach(p=>{
      const sub = eq.filter(e=>e.fam===fam && e.peca===p);
      if(!sub.length) return;
      linhas.push({peca:p, fam,
        a24: sub.filter(e=>e.ano===2024).length,
        a25: sub.filter(e=>e.ano===2025).length,
        tot: sub.length, troc: sub.filter(e=>e.executada).length});
    });
  });
  const maior = Math.max(...linhas.map(l=>l.tot));
  document.querySelector("#t-peca tbody").innerHTML = linhas.map(l=>`
    <tr>
      <td><span class="pill ${l.peca}">${PECA_NOME[l.peca]}</span></td>
      <td><span class="tipo ${l.fam}">${l.fam}</span></td>
      <td class="num">${l.a24}</td><td class="num">${l.a25}</td>
      <td class="num"><b>${l.tot}</b></td><td class="num">${l.troc}</td>
      <td class="barra-cel"><span class="barra" style="width:${100*l.tot/maior}%;
          background:${cor("--p-"+l.peca)}"></span></td>
    </tr>`).join("");
})();

/* ------------------------------------------------------------------ marca */
(function(){
  const linhas = [];
  ["RL","RT"].forEach(fam=>{
    const pq = D.parque[fam] || {};
    const tf = eq.filter(e=>e.fam===fam).length;
    const tp = Object.values(pq).reduce((a,b)=>a+b,0);
    Object.entries(pq).sort((a,b)=>b[1]-a[1]).forEach(([mk,n])=>{
      const f = eq.filter(e=>e.fam===fam && e.marca===mk).length;
      linhas.push({mk, fam, n, f, pct: n? 100*f/n : 0, idx: (tf&&n)? (f/tf)/(n/tp) : 0});
    });
    const semCad = eq.filter(e=>e.fam===fam && e.marca==="SEM CADASTRO").length;
    if(semCad) linhas.push({mk:"SEM CADASTRO", fam, n:null, f:semCad, pct:null, idx:null});
  });
  document.querySelector("#t-marca tbody").innerHTML = linhas.map(l=>`
    <tr>
      <td class="cod">${l.mk}</td>
      <td><span class="tipo ${l.fam}">${l.fam}</span></td>
      <td class="num">${l.n===null?"—":l.n}</td>
      <td class="num"><b>${l.f}</b></td>
      <td class="num">${l.pct===null?"—":l.pct.toFixed(1)+"%"}</td>
      <td class="num">${l.idx===null?"—":l.idx.toFixed(2)}</td>
      <td class="barra-cel">${l.idx===null?"":`<span class="barra"
          style="width:${Math.min(100, l.idx*19)}%;
          background:${l.idx>=1.5?cor("--sinal"):cor(l.fam==="RL"?"--rl":"--rt")}"></span>`}</td>
    </tr>`).join("");

  const misto = eq.filter(e=>e.marca==="MISTO");
  document.getElementById("aviso-misto").innerHTML = `
    <b>Cuidado com o MISTO.</b> São ${misto.length} bancos de regulador cujas três células
    são de fabricantes diferentes — ${misto.map(e=>e.marca_bruta).filter((v,i,a)=>a.indexOf(v)===i)
    .join(", ")}. O índice alto deles não diz que misturar marca estraga o banco: diz que o
    banco ficou misto <em>porque</em> já trocaram uma célula. É efeito, não causa.`;
})();

/* ------------------------------------------------------------------ lista */
const F = {ano:"", tipo:"", peca:"", marca:"", busca:""};
function opcoes(id, vals, rot){
  const s = document.getElementById(id);
  s.innerHTML = `<option value="">todos</option>` +
    vals.map(v=>`<option value="${v}">${rot?rot(v):v}</option>`).join("");
}
opcoes("f-ano", [2024,2025]);
opcoes("f-tipo", ["RL","RT"], v=> v==="RL"?"RL · religador":"RT · regulador");
opcoes("f-peca", PECAS.filter(p=>eq.some(e=>e.peca===p)), v=>PECA_NOME[v]);
opcoes("f-marca", [...new Set(eq.map(e=>e.marca))].sort());

function pinta(){
  const lin = eq.filter(e=>
    (!F.ano   || e.ano===+F.ano) &&
    (!F.tipo  || e.fam===F.tipo) &&
    (!F.peca  || e.peca===F.peca) &&
    (!F.marca || e.marca===F.marca) &&
    (!F.busca || (e.ativo+" "+e.loc+" "+e.primeira_ss).toLowerCase().includes(F.busca))
  ).sort((a,b)=> a.abert < b.abert ? -1 : a.abert > b.abert ? 1 : 0);

  document.querySelector("#t-lista tbody").innerHTML = lin.map(e=>`
    <tr>
      <td class="cod">${e.ativo}</td>
      <td><span class="tipo ${e.fam}">${e.fam}</span></td>
      <td>${e.loc}</td>
      <td class="num">${MES[e.mes-1]}/${String(e.ano).slice(2)}</td>
      <td><span class="pill ${e.peca}">${PECA_NOME[e.peca]}</span></td>
      <td class="cod">${e.marca_bruta || e.marca}</td>
      <td>${e.executada?'<span class="sim">sim</span>':'<span class="nao">não</span>'}</td>
      <td class="num">${e.cadeias}</td>
      <td class="cod">${e.primeira_ss}</td>
      <td style="font-size:12.5px; color:var(--tinta-2)">${e.postos}</td>
    </tr>`).join("");

  document.getElementById("contador").textContent =
    `${lin.length} de ${eq.length} equipamentos` +
    (lin.length ? ` · ${lin.filter(e=>e.fam==="RL").length} RL · ${lin.filter(e=>e.fam==="RT").length} RT` : "");
}
[["f-ano","ano"],["f-tipo","tipo"],["f-peca","peca"],["f-marca","marca"]].forEach(([id,k])=>{
  document.getElementById(id).addEventListener("change", ev=>{ F[k]=ev.target.value; pinta(); });
});
document.getElementById("f-busca").addEventListener("input", ev=>{
  F.busca = ev.target.value.trim().toLowerCase(); pinta();
});

/* clicar na tabela de peça ou de marca filtra a lista */
document.querySelector("#t-peca tbody").addEventListener("click", ev=>{
  const tr = ev.target.closest("tr"); if(!tr) return;
  const p = tr.querySelector(".pill").className.split(" ")[1];
  F.peca = p; F.tipo = tr.querySelector(".tipo").textContent;
  document.getElementById("f-peca").value = p;
  document.getElementById("f-tipo").value = F.tipo;
  pinta(); document.getElementById("t-lista").scrollIntoView({behavior:"smooth", block:"start"});
});
document.querySelector("#t-marca tbody").addEventListener("click", ev=>{
  const tr = ev.target.closest("tr"); if(!tr) return;
  F.marca = tr.querySelector(".cod").textContent;
  F.tipo = tr.querySelector(".tipo").textContent;
  document.getElementById("f-marca").value = F.marca;
  document.getElementById("f-tipo").value = F.tipo;
  pinta(); document.getElementById("t-lista").scrollIntoView({behavior:"smooth", block:"start"});
});
document.querySelector("#t-peca tbody").style.cursor = "pointer";
document.querySelector("#t-marca tbody").style.cursor = "pointer";

/* ------------------------------------------------------------------ chaves */
let modo = "tipo";
function chave(m){
  modo = m;
  document.getElementById("bt-tipo").setAttribute("aria-pressed", m==="tipo");
  document.getElementById("bt-peca").setAttribute("aria-pressed", m==="peca");
  desenha(m);
}
document.getElementById("bt-tipo").addEventListener("click", ()=>chave("tipo"));
document.getElementById("bt-peca").addEventListener("click", ()=>chave("peca"));

desenha("tipo");
pinta();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>{
  desenha(modo); pinta();
});
</script>

"""


if __name__ == "__main__":
    monta()
