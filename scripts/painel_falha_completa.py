"""
Prontuário de Falhas de RL e RT — o painel da leitura integral da planilha mãe.

Substitui o painel anterior, que só enxergava o DCMD (21% do universo). Aqui entram as
2.384 cadeias de 2024-2025: as 497 que passaram por um posto do DCMD e as 1.137 de
indisponibilidade ou anomalia que nunca passaram. As 750 restantes ficam de fora por
definição — a pendência delas é ajuste, obra, comissionamento ou cadastro.

`falha_completa.py` junta e rotula; este desenha.

Quatro decisões de desenho:

- **A cor do item vem da classe.** São 22 rótulos — inventar 22 matizes distintas seria
  ilegível e reprovaria em daltonismo. Cada classe tem uma família de matiz e o item ganha
  um tom dentro dela, então «para-raio» e «cabo» se distinguem sem brigar com «tanque».
- **O eixo vai até dezembro de 2025** com os cinco últimos meses hachurados e vazios. Os
  meses vazios SÃO o recado: a planilha mãe fecha em 11/07/2025.
- **O seletor «Mostrar» separa o que é falha do que não é.** Peça grande e apoio são falha
  do equipamento; poste e poda são fato de terceiro; obra, comissionamento, ajuste e
  melhoria não são manutenção. Misturar tudo numa barra só é o erro que faz a taxa do
  ativo virar taxa do alimentador.
- **A marca conta ATIVO-ANO, não fato.** Um religador que perdeu tanque e para-raio no
  mesmo ano é um equipamento que falhou, não dois — senão o índice da marca infla.

Rodar: python3 scripts/painel_falha_completa.py  → scratchpad/painel_falha_completa.html
"""

import json
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

# A base já revisada manda quando existe: a revisão é a segunda opinião item a item,
# e é ela que tira a duplicata — duas cadeias contando o mesmo conserto.
DADOS = os.path.join(RAIZ, "data", "missao", "falha_revisada.json")
if not os.path.exists(DADOS):
    DADOS = os.path.join(RAIZ, "data", "missao", "falha_total.json")
SAIDA = os.path.join(RAIZ, "scratchpad", "painel_falha_completa.html")

EIXO = [(a, m) for a in (2024, 2025, 2026) for m in range(1, 13)]
ULTIMO = 32   # ago/2026 é o último mês que a base alcança (aberturas até 19/08)


def monta(saida=SAIDA):
    d = json.load(open(DADOS))
    # a página só usa a CONTAGEM das cadeias lidas; mandar as 1.634 linhas cruas
    # junto triplicava o peso do arquivo sem acrescentar nada na tela
    n_lidas = d["linhas_n"]
    payload = {
        "equipamentos": d["equipamentos"],
        "n_lidas": n_lidas,
        "categorias": d["categorias"],
        "parque_marca": d["parque_marca"],
        "universo": d["universo"], "no_dcmd": d["no_dcmd"],
        "fora_dcmd": d["fora_dcmd"], "fora_sem_falha": d["fora_sem_falha"],
        "derrubados_n": len(d.get("derrubados") or []),
        "duplicatas_n": len(d.get("duplicatas") or []),
        "revisao_ativos": d.get("revisao_ativos", 0),
        "mudados_n": len(d.get("mudados_na_revisao") or []),
        "eixo": [list(k) for k in EIXO], "ultimo": ULTIMO, "corte": d["corte"],
    }
    html = MOLDE.replace("D.linhas.length", "D.n_lidas").replace("/*DADOS*/", json.dumps(payload, ensure_ascii=False))
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w") as f:
        f.write(html)
    print(saida, "·", len(html) // 1024, "KB ·", len(d["equipamentos"]), "fatos")
    return saida


MOLDE = r"""
<title>Prontuário de Falhas de RL e RT</title>
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
  --c-grande:#a33327; --c-apoio:#2f56b0; --c-meio:#75681a; --c-fora:#6d675a; --c-nada:#a49d87;
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
    --c-grande:#d96a55; --c-apoio:#6b8fe0; --c-meio:#a99a3f; --c-fora:#8d8672; --c-nada:#5b5443;
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
  --c-grande:#d96a55; --c-apoio:#6b8fe0; --c-meio:#a99a3f; --c-fora:#8d8672; --c-nada:#5b5443;
  --ghost:#3b3529;
}

*{box-sizing:border-box}
body{margin:0; background:var(--papel); color:var(--tinta);
  font-family:var(--leitura); font-size:15px; line-height:1.55; -webkit-font-smoothing:antialiased}
.folha{max-width:1120px; margin:0 auto; padding:0 20px; padding-block:0 64px}

.masthead{border-bottom:3px double var(--filete-2); padding-block:34px 14px; margin-bottom:26px}
.carimbo{display:inline-block; font-family:var(--mono); font-size:10.5px; letter-spacing:.14em;
  text-transform:uppercase; color:var(--sinal); border:1px solid var(--sinal);
  background:var(--sinal-papel); padding:3px 9px; border-radius:2px; margin-bottom:14px}
h1{font-family:var(--cond); font-weight:700; font-size:clamp(32px,6vw,52px); line-height:.98;
  margin:0 0 10px; letter-spacing:-.005em; text-wrap:balance}
.subtitulo{font-size:16px; color:var(--tinta-2); max-width:64ch; margin:0 0 20px}
.subtitulo em{color:var(--tinta); font-style:italic}

.placa{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:0;
  border-top:1px solid var(--filete); border-left:1px solid var(--filete)}
.placa div{border-right:1px solid var(--filete); border-bottom:1px solid var(--filete);
  padding:11px 13px; background:var(--papel-2)}
.placa dt{font-family:var(--mono); font-size:9.5px; letter-spacing:.11em; text-transform:uppercase;
  color:var(--tinta-3); margin:0 0 3px}
.placa dd{margin:0; font-family:var(--cond); font-weight:600; font-size:27px; line-height:1;
  font-variant-numeric:tabular-nums}
.placa dd small{font-size:13px; font-weight:500; color:var(--tinta-2); margin-left:4px}

section{margin-top:44px}
h2{font-family:var(--cond); font-weight:600; font-size:26px; margin:0 0 4px; text-wrap:balance}
h2 .ordem{font-family:var(--mono); font-size:11px; color:var(--sinal); letter-spacing:.1em;
  vertical-align:.5em; margin-right:9px}
.lede{color:var(--tinta-2); max-width:68ch; margin:0 0 20px; font-size:14.5px}
.lede strong{color:var(--tinta); font-weight:600}

.aviso{border-left:3px solid var(--sinal); background:var(--sinal-papel); padding:12px 15px;
  margin:18px 0 0; font-size:14px; color:var(--tinta); max-width:76ch}
.aviso b{font-family:var(--cond); font-weight:600}

.quadro{border:1px solid var(--filete); background:var(--papel-2); padding:16px 14px 10px}
.quadro + .quadro{border-top:none}
.quadro-cab{display:flex; flex-wrap:wrap; gap:10px 18px; align-items:baseline;
  justify-content:space-between; margin-bottom:12px}
.quadro-tit{font-family:var(--mono); font-size:10px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--tinta-3)}
svg{display:block; width:100%; height:auto; overflow:visible}
.gx{font-family:var(--mono); font-size:8.5px; fill:var(--tinta-3)}
.gy{font-family:var(--mono); font-size:9px; fill:var(--tinta-3)}
.grade{stroke:var(--filete); stroke-width:.6}
.eixo{stroke:var(--filete-2); stroke-width:1}
.vnum{font-family:var(--mono); font-size:9.5px; font-weight:600; fill:var(--tinta-2)}
.anolab{font-family:var(--cond); font-size:12px; font-weight:600; fill:var(--tinta-2); letter-spacing:.06em}

.chaves{display:flex; gap:0; border:1px solid var(--filete-2); border-radius:2px; overflow:hidden}
.chaves button{font-family:var(--mono); font-size:10px; letter-spacing:.07em; text-transform:uppercase;
  border:none; background:var(--papel); color:var(--tinta-2); padding:6px 11px; cursor:pointer;
  border-right:1px solid var(--filete)}
.chaves button:last-child{border-right:none}
.chaves button[aria-pressed="true"]{background:var(--tinta); color:var(--papel)}
.chaves button:focus-visible{outline:2px solid var(--sinal); outline-offset:-2px}

.legenda{display:flex; flex-wrap:wrap; gap:6px 16px; margin-top:12px; padding-top:11px;
  border-top:1px solid var(--filete)}
.legenda span{display:inline-flex; align-items:center; gap:6px; font-family:var(--mono);
  font-size:10px; letter-spacing:.05em; color:var(--tinta-2)}
.legenda i{width:11px; height:11px; border-radius:1px; display:inline-block}

.rolo{overflow-x:auto; border:1px solid var(--filete)}
table{border-collapse:collapse; width:100%; font-family:var(--cond); font-size:14.5px}
caption{text-align:left; font-family:var(--mono); font-size:10px; letter-spacing:.12em;
  text-transform:uppercase; color:var(--tinta-3); padding:10px 12px 8px; background:var(--papel-2);
  border-bottom:1px solid var(--filete)}
th{background:var(--tinta); color:var(--papel); font-weight:600; font-size:11px;
  font-family:var(--mono); letter-spacing:.07em; text-transform:uppercase; padding:8px 10px;
  text-align:left; white-space:nowrap; position:sticky; top:0}
td{padding:6px 10px; border-bottom:1px solid var(--filete); vertical-align:top}
tbody tr:nth-child(even){background:var(--papel-2)}
tr.classe-cab td{background:var(--papel-3); font-family:var(--mono); font-size:10px;
  letter-spacing:.12em; text-transform:uppercase; color:var(--tinta-2); padding:7px 10px}
.num{text-align:right; font-family:var(--mono); font-size:12.5px; font-variant-numeric:tabular-nums}
.cod{font-family:var(--mono); font-size:12.5px; letter-spacing:-.01em}
.barra{display:block; height:7px; border-radius:1px; min-width:2px}
.barra-cel{width:120px; padding-top:11px}

.pill{display:inline-block; font-family:var(--mono); font-size:9.5px; letter-spacing:.06em;
  text-transform:uppercase; padding:2px 7px; border-radius:9px; border:1px solid; white-space:nowrap}
.pill.grande{color:var(--c-grande); border-color:var(--c-grande)}
.pill.apoio{color:var(--c-apoio); border-color:var(--c-apoio)}
.pill.meio{color:var(--c-meio); border-color:var(--c-meio)}
.pill.fora{color:var(--c-fora); border-color:var(--c-fora)}
.pill.nada{color:var(--c-nada); border-color:var(--c-nada)}
.tipo{font-family:var(--mono); font-size:11px; font-weight:600; letter-spacing:.06em}
.tipo.RL{color:var(--rl)} .tipo.RT{color:var(--rt)}
.sim{color:var(--c-meio); font-family:var(--mono); font-size:11px}
.nao{color:var(--sinal); font-family:var(--mono); font-size:11px}
.marca-dcmd{font-family:var(--mono); font-size:10px; color:var(--tinta-3)}

.filtros{display:flex; flex-wrap:wrap; gap:9px; align-items:center; margin-bottom:14px}
.filtros label{font-family:var(--mono); font-size:9.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--tinta-3); margin-right:-4px}
select,input[type=search]{font-family:var(--cond); font-size:14px; padding:5px 9px; color:var(--tinta);
  background:var(--papel); border:1px solid var(--filete-2); border-radius:2px}
select:focus-visible,input:focus-visible{outline:2px solid var(--sinal); outline-offset:1px}
.contador{font-family:var(--mono); font-size:11px; color:var(--tinta-3); margin-left:auto}

.metodo{border-top:3px double var(--filete-2); margin-top:52px; padding-top:22px;
  columns:2; column-gap:38px; font-size:14px; color:var(--tinta-2)}
.metodo h3{font-family:var(--mono); font-size:10px; letter-spacing:.12em; text-transform:uppercase;
  color:var(--sinal); margin:0 0 5px; break-after:avoid}
.metodo p{margin:0 0 16px; break-inside:avoid; max-width:46ch}
.metodo b{color:var(--tinta); font-weight:600}
.metodo code{font-family:var(--mono); font-size:12px; color:var(--tinta)}
@media (max-width:760px){.metodo{columns:1}}

.rodape{margin-top:34px; padding-top:14px; border-top:1px solid var(--filete);
  font-family:var(--mono); font-size:10px; letter-spacing:.06em; color:var(--tinta-3);
  display:flex; flex-wrap:wrap; gap:6px 18px}
@media (prefers-reduced-motion:no-preference){
  rect.anim{animation:sobe .5s cubic-bezier(.2,.7,.3,1) backwards}
  @keyframes sobe{from{transform:scaleY(0)}}
}
</style>

<div class="folha">

<header class="masthead">
  <div class="carimbo">ETO-COEP · leitura integral da base de SS</div>
  <h1>Prontuário de Falhas de RL e RT</h1>
  <p class="subtitulo">
    Todas as demandas de religador e regulador de <em>2024, 2025 e 2026</em> — o alcance do
    parecer na base —, lidas parecer a
    parecer e rotuladas pelo <em>item que deu problema</em> — do tanque ao para-raio, da
    chave faca ao furto. Cada demanda é datada pela abertura da primeira SS, e a cadeia
    inteira conta como um fato só.
  </p>
  <dl class="placa" id="placa"></dl>
  <div class="aviso" id="aviso-escopo"></div>
</header>

<section>
  <h2><span class="ordem">01</span>A mensalização</h2>
  <p class="lede">
    Fatos por mês de <strong>abertura da primeira SS</strong>, de janeiro de 2024 a agosto
    de 2026. O eixo corre contínuo pelos três anos: é assim que se vê onde a série
    <strong>acaba</strong>, em vez de parecer que a fila cedeu. Os botões trocam o que divide
    as barras.
  </p>

  <div class="quadro">
    <div class="quadro-cab">
      <span class="quadro-tit" id="tit-falhas"></span>
      <div class="chaves" role="group" aria-label="Como dividir as barras">
        <button id="bt-tipo" aria-pressed="true">por tipo</button>
        <button id="bt-classe" aria-pressed="false">por classe</button>
        <button id="bt-cat" aria-pressed="false">por item</button>
        <button id="bt-posto" aria-pressed="false">por posto</button>
      </div>
    </div>
    <div class="filtros" style="margin:-4px 0 12px">
      <label for="f-classe-g">Mostrar</label>
      <select id="f-classe-g">
        <option value="falha">falha do equipamento (peça grande + apoio)</option>
        <option value="grande">só peça grande</option>
        <option value="equip+meio">falha + fato de terceiro (poste, poda)</option>
        <option value="tudo">tudo, inclusive obra e comissionamento</option>
      </select>
    </div>
    <svg id="g-falhas" viewBox="0 0 1000 330" role="img"
         aria-label="Demandas por mês, janeiro de 2024 a agosto de 2026"></svg>
    <div class="legenda" id="leg-falhas"></div>
  </div>
</section>

<section>
  <h2><span class="ordem">02</span>O defeito de origem</h2>
  <p class="lede">
    O item que o parecer nomeou, agrupado por classe. <strong>Peça grande</strong> é o
    equipamento em si — a régua que entra na sua taxa de falha. <strong>Apoio</strong> são os
    componentes que ficam junto dele. <strong>Fato de terceiro</strong> é quando a SS pendurou
    no código do religador porque ele é o marco do trecho, mas o fato era do poste ou da
    vegetação. <strong>Não é manutenção</strong> junta obra, comissionamento, ajuste e melhoria.
  </p>
  <div class="rolo">
    <table id="t-cat">
      <caption>Item por classe, tipo e ano · equipamentos, não ocorrências</caption>
      <thead><tr>
        <th>Item</th><th>Tipo</th><th class="num">2024</th><th class="num">2025</th>
        <th class="num">Total</th><th class="num">No DCMD</th><th class="num">Fora</th>
        <th class="num">Feito</th><th>Participação</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
  <div class="aviso" id="aviso-objeto"></div>
</section>

<section>
  <h2><span class="ordem">03</span>As marcas</h2>
  <p class="lede">
    A marca não existe em base de SS nenhuma: vem do <strong>cadastro de ajuste da
    proteção</strong> — a coluna RELÉ no religador, PARTE ATIVA no regulador. Por isso o
    denominador é o parque <strong>desse cadastro</strong>, e não o parque oficial. O
    <strong>índice</strong> é a fatia das falhas dividida pela fatia do parque: acima de 1,00
    a marca falha mais do que o tamanho dela explica.
  </p>
  <div class="filtros" style="margin-bottom:12px">
    <label for="f-classe-m">Contando</label>
    <select id="f-classe-m">
      <option value="grande">só peça grande</option>
      <option value="falha">falha do equipamento (peça grande + apoio)</option>
    </select>
  </div>
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
    Uma linha por <strong>ativo, ano e item</strong>. O mesmo religador pode ter perdido o
    tanque numa demanda e o para-raio noutra — são dois fatos, e aparecem em duas linhas. A
    coluna <strong>cadeias</strong> diz quantas demandas distintas geraram aquele fato.
    Clique numa linha das tabelas acima para filtrar aqui.
  </p>
  <div class="filtros">
    <label for="f-ano">Ano</label><select id="f-ano"></select>
    <label for="f-tipo">Tipo</label><select id="f-tipo"></select>
    <label for="f-cat">Item</label><select id="f-cat"></select>
    <label for="f-marca">Marca</label><select id="f-marca"></select>
    <label for="f-dcmd">Posto</label><select id="f-dcmd">
      <option value="">todos</option>
      <option value="1">passou pelo DCMD</option>
      <option value="0">não passou</option>
    </select>
    <input type="search" id="f-busca" placeholder="ativo, praça ou SS" aria-label="Buscar">
    <span class="contador" id="contador"></span>
  </div>
  <div class="rolo">
    <table id="t-lista">
      <thead><tr>
        <th>Ativo</th><th>Tipo</th><th>Praça</th><th class="num">Abertura</th>
        <th>Item</th><th>Nome no parecer</th><th>Marca</th><th>Feito</th>
        <th class="num">Cadeias</th><th>Volta?</th><th>Primeira SS</th><th>Caminho no SGM</th>
      </tr></thead>
      <tbody></tbody>
    </table>
  </div>
</section>

<div class="metodo">
  <h3>A fonte</h3>
  <p>
    <b>EQP_JOAO_19082026.xlsx</b>, aba «Exportar Planilha»: 10.386 SS, 10.377 com parecer, de
    01/08/2020 a 19/08/2026. É a única base que traz o texto técnico junto da cadeia — o recorte local de SS/OS
    não tem descrição e a base crua de 36 MB está fora do repositório.
  </p>

  <h3>A cadeia</h3>
  <p>
    A cadeia se remonta pelo elo <code>SS_APOS_REPASSE</code>, e a cabeça é a SS que ninguém
    aponta. O SGM abre SS nova a cada passagem de posto, mas repasse não é fato novo:
    <b>a cadeia inteira conta como uma demanda só</b>.
  </p>

  <h3>A data</h3>
  <p>
    O ano é o da <b>abertura da primeira SS da cadeia</b> — a original, antes de a cadeia de
    repasse começar. O SGM abre SS nova a cada passagem de posto e a data vai andando; só a
    primeira marca quando a demanda nasceu. Conferido nas 4.418 cadeias do recorte: a cabeça da
    cadeia é <b>sempre</b> a abertura mais antiga, sem exceção. A <b>ocorrência</b> fica ao lado
    na lista — divergem em 63 fatos, 23 deles de peça grande.
  </p>

  <h3>O escopo — e por que ele mudou</h3>
  <p id="metodo-escopo"></p>

  <h3>As cinco classes</h3>
  <p>
    <b>Peça grande</b> — tanque, controle, célula, relé, equipamento completo e furto: é a régua
    de falha do gestor, a que entra na taxa. <b>Apoio</b> — trafo auxiliar, chave faca,
    para-raio, fusível, bateria, cabo, aterramento e telecom. <b>Fato de terceiro</b> — poste e
    poda. <b>Não é manutenção</b> — ajuste de proteção, comissionamento, obra nova e melhoria.
    <b>Nada</b> — sem defeito e não identificado.
  </p>

  <h3>Como se conta</h3>
  <p>
    A chave é <b>ativo + ano + item</b>, não ativo + ano: o mesmo religador pode ter perdido o
    tanque numa demanda e o para-raio noutra, e juntar os dois apagaria um fato. Dentro de uma
    mesma chave, duas demandas no mesmo ano contam uma vez.
  </p>

  <h3>A leitura</h3>
  <p>
    Cada cadeia foi lida por inteiro, parecer por parecer, por leitores em paralelo — não por
    palavra-chave. A triagem por regex de peça foi testada e <b>reprovada</b>: deixou escapar 6
    das 21 falhas conhecidas de 2025, 29% de fuga.
  </p>

  <h3>As quatro armadilhas</h3>
  <p>
    <b>1.</b> A descrição é cumulativa — o SGM cola parecer novo por cima do antigo, sem
    separador; vale o mais recente. <b>2.</b> Texto de terceiro: laudo de outro ativo colado na
    descrição, conferido pelo código em cada caso. <b>3.</b> «Equipamento ficou em operação?
    NÃO» significa que <b>não</b> ficou. <b>4.</b> Quando a SS e a OS discordam, vale a OS.
  </p>

  <h3>O horizonte</h3>
  <p>
    A base fecha em <b>19/08/2026</b>. Agosto de 2026 é mês parcial, e setembro em diante não
    existe nela. A faixa hachurada marca
    esse limite: <b>a queda não é melhora do parque, é o fim do dado</b>.
  </p>
</div>

<div class="rodape">
  <span>Fonte: EQP_JOAO_19082026.xlsx · aba Exportar Planilha</span>
  <span>Marca: GESTÃO DE EQUIPAMENTOS · abas de ajuste da proteção</span>
  <span>Posição: 19/08/2026</span>
</div>

</div>

<script>
const D = /*DADOS*/;
const MES=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const MESL=["janeiro","fevereiro","março","abril","maio","junho","julho","agosto",
            "setembro","outubro","novembro","dezembro"];
const CATS = D.categorias;
const ROT = Object.fromEntries(CATS.map(c=>[c.k,c.rot]));
const CLS = Object.fromEntries(CATS.map(c=>[c.k,c.classe]));
const ORD = Object.fromEntries(CATS.map((c,i)=>[c.k,i]));
const CLASSE_ROT = {grande:"Peça grande", apoio:"Apoio", meio:"Fato de terceiro",
                    fora:"Não é manutenção", nada:"Nada apurado"};
const CLASSES = ["grande","apoio","meio","fora","nada"];
const GRUPO = {falha:["grande","apoio"], grande:["grande"],
               "equip+meio":["grande","apoio","meio"], tudo:CLASSES};
const cor = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const eq = D.equipamentos, eixo = D.eixo, N = eixo.length;

/* uma cor por item, derivada da classe: a classe dá a família, o índice dá o tom */
const TOM = {};
(function(){
  const base = {grande:[0,72,50], apoio:[218,58,44], meio:[64,62,28], fora:[45,7,42], nada:[45,10,60]};
  CLASSES.forEach(c=>{
    const ks = CATS.filter(x=>x.classe===c).map(x=>x.k);
    const [h,s,l] = base[c];
    ks.forEach((k,i)=>{
      const f = ks.length>1 ? i/(ks.length-1) : 0;
      TOM[k] = `hsl(${h + (c==="apoio"? -46*f : 22*f)} ${Math.round(s-16*f)}% ${Math.round(l-14*f+22*f*f)}%)`;
    });
  });
})();

/* ------------------------------------------------------------------ placa */
(function(){
  const g = eq.filter(e=>e.classe==="grande");
  const fa = eq.filter(e=>e.classe==="grande"||e.classe==="apoio");
  const itens = [
    ["Cadeias lidas", D.linhas.length, ""],
    ["Universo 2024-26", D.universo, "cadeias"],
    ["Fatos apurados", eq.length, ""],
    ["Falha do equipamento", fa.length, ""],
    ["Peça grande", g.length, ""],
    ["Fora do DCMD", eq.filter(e=>!e.dcmd).length, "de "+eq.length],
  ];
  document.getElementById("placa").innerHTML = itens.map(([t,v,s])=>
    `<div><dt>${t}</dt><dd>${v}${s?`<small>${s}</small>`:""}</dd></div>`).join("");

  const naoLidas = D.fora_sem_falha;
  const txt = `<b>O que está aqui e o que não está.</b> O universo de 2024 a 2026 na base é de
    <b>${D.universo} cadeias</b> de RL e RT. Foram lidas <b>${D.n_lidas}</b>: as que passaram por
    um posto do DCMD, mais as que nunca passaram mas são de indisponibilidade ou anomalia.
    Ficaram de fora <b>${D.fora_sem_falha}</b> cadeias que nunca tocaram o DCMD e cuja pendência
    é ajuste de proteção, obra de equipamento novo, comissionamento ou cadastro — por definição
    não são falha.
    <br><br><b>Duas passadas por cima da leitura.</b> Uma verificação adversarial revisou cada
    classificação de peça grande com a pergunta invertida — <em>a citação nomeia a peça, ou só o
    sintoma?</em> — e <b>derrubou ${D.derrubados_n}</b>. Na primeira rodada a queda foi de 66%; depois de
    reescrever a régua dos leitores com os anti-exemplos, caiu para 26%. O que cai agora é
    fronteira de régua, não engano: furto de trafo auxiliar (que não conta pela peça), «a placa»
    sem dizer qual, «base do relé» que é soquete.
    <br><br><b>A terceira passada: a revisão.</b> ${D.revisao_ativos} ativos já passaram por uma
    segunda opinião, com o histórico inteiro do ativo à vista. Ela tirou <b>${D.duplicatas_n}
    duplicatas</b> — duas cadeias contando o mesmo conserto — e mudou <b>${D.mudados_n}</b>
    rótulos. O padrão da duplicata é sempre o mesmo: <b>a SS que o RD abre para executar,
    contada à parte da cadeia que pediu o serviço</b>. A base não liga as duas, porque a SS do
    RD não é repasse, é nota nova.
    <br><br>A duplicata se concentra onde o mecanismo prevê: quase uma a cada dois ativos com
    peça grande, e <b>zero</b> em mais de 400 ativos sem peça grande — onde não há troca, não há
    execução de campo separada. A revisão ainda não cobriu todos os ativos, então o número
    abaixo deve cair mais um pouco.`;
  document.getElementById("aviso-escopo").innerHTML = txt;
  document.getElementById("metodo-escopo").innerHTML = `O primeiro recorte era só o que passou
    pelo DCMD — <b>${D.no_dcmd} cadeias</b>, uma fração do universo. As outras ${D.fora_dcmd}
    morreram na TELE ou na PROT, e entre elas há falha de equipamento de verdade, resolvida sem a
    demanda chegar ao posto. A coluna <b>Posto</b> na lista guarda a diferença, para as duas
    leituras nunca virarem uma só por acidente.`;
})();

/* ------------------------------------------------------------------ séries */
let modo="tipo", grupoG="falha";
function visiveis(g){ const ok=new Set(GRUPO[g]); return eq.filter(e=>ok.has(e.classe)); }

function serie(chave, dados){
  if(chave==="tipo") return [
    {k:"RL", rot:"Religador", c:cor("--rl"), f:e=>e.fam==="RL"},
    {k:"RT", rot:"Regulador", c:cor("--rt"), f:e=>e.fam==="RT"}];
  if(chave==="posto") return [
    {k:"d", rot:"Passou pelo DCMD", c:cor("--sinal"), f:e=>e.dcmd},
    {k:"n", rot:"Não passou", c:cor("--ghost"), f:e=>!e.dcmd}];
  if(chave==="classe") return CLASSES.filter(c=>dados.some(e=>e.classe===c))
    .map(c=>({k:c, rot:CLASSE_ROT[c], c:cor("--c-"+c), f:e=>e.classe===c}));
  const ks=[...new Set(dados.map(e=>e.categoria))].sort((a,b)=>ORD[a]-ORD[b]);
  return ks.map(k=>({k, rot:ROT[k], c:TOM[k], f:e=>e.categoria===k}));
}

/* ------------------------------------------------------------------ gráfico */
const W=1000,H=330,ML=34,MR=8,MT=14,MB=50;
const IW=W-ML-MR, IH=H-MT-MB, passo=IW/N, larg=Math.min(passo-6,34);

function desenha(){
  const dados = visiveis(grupoG);
  const gs = serie(modo, dados).map(g=>({...g,
    v: eixo.map(([a,m])=>dados.filter(e=>e.ano===a&&e.mes===m).filter(g.f).length)}));
  const totais = eixo.map((_,i)=>gs.reduce((s,g)=>s+g.v[i],0));
  const pico = Math.max(1,...totais);
  const topo = Math.ceil(pico/10)*10 || 10;
  const y = v => MT + IH - (v/topo)*IH;
  const passoY = topo<=20?5:topo<=60?10:20;
  let s="";
  for(let v=0; v<=topo; v+=passoY){
    s+=`<line class="grade" x1="${ML}" y1="${y(v)}" x2="${W-MR}" y2="${y(v)}"/>`;
    s+=`<text class="gy" x="${ML-7}" y="${y(v)+3}" text-anchor="end">${v}</text>`;
  }
  s+=`<line class="eixo" x1="${ML}" y1="${y(0)}" x2="${W-MR}" y2="${y(0)}"/>`;
  const xFim=ML+D.ultimo*passo;
  s+=`<defs><pattern id="hach" width="7" height="7" patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="7" stroke="${cor("--filete")}" stroke-width="2"/></pattern></defs>`;
  s+=`<rect x="${xFim}" y="${MT}" width="${ML+N*passo-xFim}" height="${IH}" fill="url(#hach)" opacity=".5"/>`;
  s+=`<line class="eixo" x1="${xFim}" y1="${MT}" x2="${xFim}" y2="${MT+IH}" stroke-dasharray="3 3"/>`;

  eixo.forEach(([a,m],i)=>{
    const x=ML+i*passo+(passo-larg)/2; let acc=0;
    gs.forEach(g=>{
      const v=g.v[i]; if(!v) return;
      const alt=(v/topo)*IH, yy=y(acc+v);
      s+=`<rect class="anim" x="${x}" y="${yy}" width="${larg}" height="${alt}" fill="${g.c}"
            style="transform-origin:${x}px ${y(acc)}px; animation-delay:${i*18}ms">
            <title>${MESL[m-1]} de ${a} — ${g.rot}: ${v}</title></rect>`;
      acc+=v;
    });
    if(totais[i] && (N<=24 || totais[i]>=Math.max(4, pico*0.12)))
      s+=`<text class="vnum" x="${x+larg/2}" y="${y(acc)-5}" text-anchor="middle">${totais[i]}</text>`;
    if(m%2===1) s+=`<text class="gx" x="${x+larg/2}" y="${MT+IH+14}" text-anchor="middle">${MES[m-1]}</text>`;
  });
  [[0,12,"2024"],[12,24,"2025"],[24,36,"2026"]].forEach(([a,b,rot])=>{
    const x1=ML+a*passo+3, x2=ML+b*passo-3;
    s+=`<line class="eixo" x1="${x1}" y1="${MT+IH+24}" x2="${x2}" y2="${MT+IH+24}"/>`;
    s+=`<text class="anolab" x="${(x1+x2)/2}" y="${MT+IH+38}" text-anchor="middle">${rot}</text>`;
  });
  const xm=(xFim+ML+N*passo)/2;
  s+=`<text class="anolab" x="${xm}" y="${MT+IH/2-6}" text-anchor="middle" fill="${cor("--tinta-3")}">a base</text>`;
  s+=`<text class="anolab" x="${xm}" y="${MT+IH/2+10}" text-anchor="middle" fill="${cor("--tinta-3")}">vai até 19/08/2026</text>`;

  document.getElementById("g-falhas").innerHTML=s;
  document.getElementById("leg-falhas").innerHTML=gs.map(g=>
    `<span><i style="background:${g.c}"></i>${g.rot} · ${g.v.reduce((x,z)=>x+z,0)}</span>`).join("");
  document.getElementById("tit-falhas").textContent =
    `${dados.length} fatos no período · ${document.getElementById("f-classe-g").selectedOptions[0].text}`;
}

/* ------------------------------------------------------------------ itens */
(function(){
  const corpo=[]; let maior=1;
  CLASSES.forEach(c=>{
    const ks=[...new Set(eq.filter(e=>e.classe===c).map(e=>e.categoria))].sort((a,b)=>ORD[a]-ORD[b]);
    if(!ks.length) return;
    const tot=eq.filter(e=>e.classe===c).length;
    corpo.push(`<tr class="classe-cab"><td colspan="9">${CLASSE_ROT[c]} · ${tot}</td></tr>`);
    ks.forEach(k=>{
      ["RL","RT"].forEach(fam=>{
        const sub=eq.filter(e=>e.categoria===k&&e.fam===fam);
        if(!sub.length) return;
        maior=Math.max(maior,sub.length);
        corpo.push({k,c,fam,sub});
      });
    });
  });
  document.querySelector("#t-cat tbody").innerHTML = corpo.map(r=>{
    if(typeof r==="string") return r;
    const {k,c,fam,sub}=r;
    return `<tr data-cat="${k}" data-fam="${fam}">
      <td><span class="pill ${c}">${ROT[k]}</span></td>
      <td><span class="tipo ${fam}">${fam}</span></td>
      <td class="num">${sub.filter(e=>e.ano===2024).length}</td>
      <td class="num">${sub.filter(e=>e.ano===2025).length}</td>
      <td class="num"><b>${sub.length}</b></td>
      <td class="num">${sub.filter(e=>e.dcmd).length}</td>
      <td class="num">${sub.filter(e=>!e.dcmd).length}</td>
      <td class="num">${sub.filter(e=>e.executada).length}</td>
      <td class="barra-cel"><span class="barra" style="width:${100*sub.length/maior}%;
        background:${TOM[k]}"></span></td></tr>`;
  }).join("");

  const rein=eq.filter(e=>e.reincidente&&e.classe==="grande");
  const reinAtivos=[...new Set(rein.map(e=>e.ativo))];
  const poste=eq.filter(e=>e.classe==="meio").length;
  document.getElementById("aviso-objeto").innerHTML = `<b>O objeto do fato.</b> São
    <b>${poste}</b> fatos rotulados como poste, cruzeta, estrutura ou vegetação. A SS pendurou
    no código do religador porque ele é o marco do trecho, mas o equipamento não tinha defeito.
    Sem separar isso, a taxa do ativo vira taxa do alimentador.
    <br><br><b>A peça que volta.</b> ${reinAtivos.length} ativos perderam a MESMA peça grande
    em dois anos seguidos (${rein.length} fatos). Pela régua contam duas vezes, e está certo —
    mas na leitura do parque é um equipamento dois anos com o mesmo defeito, não dois
    equipamentos falhando. É o sinal mais direto de demanda cancelada sem resolver: no
    7908206074 a SS de 2024 pediu troca completa, foi cancelada, e em 2025 o mesmo tanque
    queimou de novo. A coluna <b>Volta?</b> na lista marca cada um.`;
})();

/* ------------------------------------------------------------------ marcas */
function marcas(grupo){
  const ok=new Set(GRUPO[grupo]);
  const linhas=[];
  ["RL","RT"].forEach(fam=>{
    const pq=D.parque_marca[fam]||{};
    const base=eq.filter(e=>e.fam===fam&&ok.has(e.classe));
    const ativos=new Set(base.map(e=>e.ativo+"|"+e.ano));
    const tf=ativos.size, tp=Object.values(pq).reduce((a,b)=>a+b,0);
    Object.entries(pq).sort((a,b)=>b[1]-a[1]).forEach(([mk,n])=>{
      const f=new Set(base.filter(e=>e.marca===mk).map(e=>e.ativo+"|"+e.ano)).size;
      linhas.push({mk,fam,n,f,pct:n?100*f/n:0,idx:(tf&&n)?(f/tf)/(n/tp):0});
    });
    const sem=new Set(base.filter(e=>e.marca==="SEM CADASTRO").map(e=>e.ativo+"|"+e.ano)).size;
    if(sem) linhas.push({mk:"SEM CADASTRO",fam,n:null,f:sem,pct:null,idx:null});
  });
  document.querySelector("#t-marca tbody").innerHTML = linhas.map(l=>`
    <tr data-marca="${l.mk}" data-fam="${l.fam}">
      <td class="cod">${l.mk}</td>
      <td><span class="tipo ${l.fam}">${l.fam}</span></td>
      <td class="num">${l.n===null?"—":l.n}</td>
      <td class="num"><b>${l.f}</b></td>
      <td class="num">${l.pct===null?"—":l.pct.toFixed(1)+"%"}</td>
      <td class="num">${l.idx===null?"—":l.idx.toFixed(2)}</td>
      <td class="barra-cel">${l.idx===null?"":`<span class="barra"
        style="width:${Math.min(100,l.idx*19)}%;
        background:${l.idx>=1.5?cor("--sinal"):cor(l.fam==="RL"?"--rl":"--rt")}"></span>`}</td>
    </tr>`).join("");

  const misto=[...new Set(eq.filter(e=>e.marca==="MISTO").map(e=>e.marca_bruta))].filter(Boolean);
  document.getElementById("aviso-misto").innerHTML = `<b>Cuidado com o MISTO.</b> São bancos de
    regulador cujas três células são de fabricantes diferentes${misto.length?" — "+misto.join(", "):""}.
    O índice alto deles não diz que misturar marca estraga o banco: diz que o banco ficou misto
    <em>porque</em> já trocaram uma célula. É efeito, não causa.`;
}

/* ------------------------------------------------------------------ lista */
const F={ano:"",tipo:"",cat:"",marca:"",dcmd:"",busca:""};
function opcoes(id,vals,rot){
  document.getElementById(id).innerHTML = `<option value="">todos</option>` +
    vals.map(v=>`<option value="${v}">${rot?rot(v):v}</option>`).join("");
}
opcoes("f-ano",[2024,2025]);
opcoes("f-tipo",["RL","RT"],v=>v==="RL"?"RL · religador":"RT · regulador");
opcoes("f-cat",[...new Set(eq.map(e=>e.categoria))].sort((a,b)=>ORD[a]-ORD[b]),v=>ROT[v]);
opcoes("f-marca",[...new Set(eq.map(e=>e.marca))].sort());

function pinta(){
  const lin=eq.filter(e=>
    (!F.ano||e.ano===+F.ano) && (!F.tipo||e.fam===F.tipo) && (!F.cat||e.categoria===F.cat) &&
    (!F.marca||e.marca===F.marca) && (F.dcmd===""||String(e.dcmd?1:0)===F.dcmd) &&
    (!F.busca||(e.ativo+" "+e.loc+" "+e.cadeia).toLowerCase().includes(F.busca))
  ).sort((a,b)=> a.abert<b.abert?-1 : a.abert>b.abert?1 : 0);

  document.querySelector("#t-lista tbody").innerHTML = lin.map(e=>`
    <tr>
      <td class="cod">${e.ativo}</td>
      <td><span class="tipo ${e.fam}">${e.fam}</span></td>
      <td>${e.loc}</td>
      <td class="num">${MES[e.mes-1]}/${String(e.ano).slice(2)}${
          e.ano_diverge?`<br><span class="marca-dcmd">ocor: ${MES[e.mes_ocor-1]}/${String(e.ano_ocor).slice(2)}</span>`:""}</td>
      <td><span class="pill ${e.classe}">${ROT[e.categoria]}</span></td>
      <td style="font-size:13px; color:var(--tinta-2)">${e.item||"—"}</td>
      <td class="cod">${e.marca_bruta||e.marca}</td>
      <td>${e.executada?'<span class="sim">sim</span>':'<span class="nao">não</span>'}</td>
      <td class="num">${e.cadeias}</td>
      <td>${e.reincidente?`<span class="nao">${e.reincidencia}</span>`:'<span style="color:var(--tinta-3)">—</span>'}</td>
      <td class="cod">${e.cadeia}<br><span class="marca-dcmd">${e.dcmd?"passou pelo DCMD":"não passou"}</span></td>
      <td style="font-size:12px; color:var(--tinta-2)">${e.postos}</td>
    </tr>`).join("");

  document.getElementById("contador").textContent =
    `${lin.length} de ${eq.length} fatos · ${lin.filter(e=>e.fam==="RL").length} RL · ` +
    `${lin.filter(e=>e.fam==="RT").length} RT · ${lin.filter(e=>e.dcmd).length} pelo DCMD`;
}
[["f-ano","ano"],["f-tipo","tipo"],["f-cat","cat"],["f-marca","marca"],["f-dcmd","dcmd"]]
  .forEach(([id,k])=>document.getElementById(id)
    .addEventListener("change",ev=>{F[k]=ev.target.value; pinta();}));
document.getElementById("f-busca").addEventListener("input",ev=>{
  F.busca=ev.target.value.trim().toLowerCase(); pinta();});

function filtraPor(tr){
  if(tr.dataset.cat){ F.cat=tr.dataset.cat; document.getElementById("f-cat").value=F.cat; }
  if(tr.dataset.marca){ F.marca=tr.dataset.marca; document.getElementById("f-marca").value=F.marca; }
  if(tr.dataset.fam){ F.tipo=tr.dataset.fam; document.getElementById("f-tipo").value=F.tipo; }
  pinta();
  document.getElementById("t-lista").scrollIntoView({behavior:"smooth",block:"start"});
}
["#t-cat tbody","#t-marca tbody"].forEach(sel=>{
  const b=document.querySelector(sel);
  b.style.cursor="pointer";
  b.addEventListener("click",ev=>{
    const tr=ev.target.closest("tr");
    if(tr && !tr.classList.contains("classe-cab")) filtraPor(tr);
  });
});

/* ------------------------------------------------------------------ chaves */
const BOTOES={tipo:"bt-tipo",classe:"bt-classe",cat:"bt-cat",posto:"bt-posto"};
function chave(m){
  modo=m;
  Object.entries(BOTOES).forEach(([k,id])=>
    document.getElementById(id).setAttribute("aria-pressed", k===m));
  desenha();
}
Object.entries(BOTOES).forEach(([k,id])=>
  document.getElementById(id).addEventListener("click",()=>chave(k)));
document.getElementById("f-classe-g").addEventListener("change",ev=>{
  grupoG=ev.target.value; desenha();});
document.getElementById("f-classe-m").addEventListener("change",ev=>marcas(ev.target.value));

desenha();
marcas("grande");
pinta();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",()=>{desenha(); marcas(
  document.getElementById("f-classe-m").value);});
</script>

"""


if __name__ == "__main__":
    monta()
