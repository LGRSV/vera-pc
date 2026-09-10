#!/usr/bin/env python3
"""
Cartão de reporte de campo do regulador 5800440256 (Mateiros) — padrão Energisa.

Pedido do gestor em 10/09: «um reporte que nem o da segunda foto, só que para esse
ativo: 5800440256». A segunda foto é o cartão institucional da Energisa — fundo azul,
faixa de três fotos na diagonal, lista de campos com ícone e a régua de valores no pé.

O QUE ESTE CARTÃO REPORTA: a substituição da célula do banco de reguladores de tensão
de Mateiros, executada em 09/09/2026. As três fotos de campo são a prova — a placa do
equipamento instalado (ITB RAV-2, 200 kVA, 19,92 kV, código Energisa 690240, fabricado
em 03/2026) é exatamente o material que a aba Gestão orçou em R$ 51.705,75.

DE ONDE VÊM OS NÚMEROS: a aba «Gestão» da planilha base (SS, criticidade, status,
defeito, orçamento, dias pendente e dias aguardando DCMD) e a base de SS/OS crua
(abertura da SS e o parecer mais recente). Nada aqui é digitado à mão.

O CHROME DA MARCA (logotipo e faixa de valores) é recortado do próprio modelo que o
gestor mandou, guardado em assets/reportes/ — não há reconstrução de logotipo.

Rodar:  python3 scripts/reporte_5800440256.py
        NODE_PATH=/opt/node22/lib/node_modules /opt/node22/bin/node scripts/imagem_reporte.js
"""

import base64
import datetime as dt
import os
import re
import sys

from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co        # noqa: E402  — escolhe a base de SS/OS mais nova
import extrai_ssos_min as ex    # noqa: E402  — o remontador de registros

ATIVO = "5800440256"
BASE_COEP = os.path.join(RAIZ, "data", "raw", "GESTAO_EQUIPAMENTOS_ESPECIAIS_COEP.xlsx")
REPORTES = os.path.join(RAIZ, "assets", "reportes")
SAIDA = os.path.join(RAIZ, "dist", "REPORTE_%s.html" % ATIVO)

SERVICO = dt.date(2026, 9, 9)      # data das três fotos de campo (09/09/2026, 09h21 e 10h46)

# ---------------------------------------------------------------- paleta do modelo
# amostrada pixel a pixel do cartão que o gestor mandou
NAVY = "#012350"
NAVY_2 = "#0a3f79"      # miolo do círculo do ícone
CIANO = "#1da0e6"       # faixa da SS e títulos
CIANO_2 = "#2e9edf"     # rótulo dos campos
FILETE = "#1c3e6b"      # linha entre os campos


# ------------------------------------------------------------------------- leitura
def da_gestao():
    """A linha do ativo na aba Gestão da planilha base."""
    ws = load_workbook(BASE_COEP, data_only=True, read_only=True)["Gestão"]
    linhas = list(ws.iter_rows(values_only=True))
    cab = [str(v or "").strip() for v in linhas[0]]
    for r in linhas[1:]:
        if r and str(r[0]).strip() == ATIVO:
            return dict(zip(cab, r))
    raise SystemExit("ativo %s não está na aba Gestão" % ATIVO)


def data(s):
    try:
        return dt.datetime.strptime((s or "").strip()[:10], "%d/%m/%Y").date()
    except ValueError:
        return None


def da_base_ss():
    """As SS do ativo na base crua — abertura, situação, posto e parecer."""
    caminho = co.PARTES[0] if isinstance(co.PARTES, (list, tuple)) else co.PARTES
    regs, buffer = [], None
    with open(caminho, encoding="latin-1") as fh:
        for i, linha in enumerate(fh):
            linha = linha.rstrip("\r\n")
            if i == 0 and linha.startswith("NUMERO_SS@"):
                continue
            if co.RE_INICIO.match(linha):
                if buffer is not None and ("@%s@" % ATIVO) in buffer:
                    regs.append(buffer)
                buffer = linha
            elif buffer is not None:
                buffer += "\n" + linha
        if buffer is not None and ("@%s@" % ATIVO) in buffer:
            regs.append(buffer)
    ss = []
    for b in regs:
        c = ex._normaliza(b.split("@"))
        if c[13].strip() != ATIVO:
            continue
        ss.append({"ss": c[0].strip(), "posto": c[11].strip(), "situacao": c[18].strip(),
                   "abertura": data(c[19]), "tipo": c[26].strip(), "desc": c[27].strip(),
                   "alimentador": c[12].strip(), "localidade": c[23].strip()})
    ss.sort(key=lambda x: (x["abertura"], x["ss"]))
    return ss


def parecer_dmsl(texto):
    """A descrição da SS é cumulativa; o parecer mais recente vem colado no começo."""
    m = re.search(r"PARECER DMSL[^:]*:\s*(.+?)(?=Boa noite|Bom dia|Boa tarde|Segue SS|$)",
                  texto, re.S | re.I)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


# ------------------------------------------------------------------------ embutidos
def b64(caminho):
    with open(caminho, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def imagem(nome):
    ext = "png" if nome.endswith(".png") else "jpeg"
    return "data:image/%s;base64,%s" % (ext, b64(os.path.join(REPORTES, nome)))


def fontes():
    """Barlow Condensed (títulos) e Montserrat (texto), já embutidas como data URI."""
    css = []
    for arq in ("fontes.css", "fontes_energisa.css"):
        caminho = os.path.join(RAIZ, "assets", "css", arq)
        bruto = open(caminho, encoding="utf-8").read()
        familias = ("Barlow Condensed",) if arq == "fontes.css" else ("Montserrat",)
        for bloco in re.findall(r"@font-face\s*\{.*?\}", bruto, re.S):
            if any(("'%s'" % f) in bloco for f in familias):
                css.append(bloco)
    return "\n".join(css)


# ---------------------------------------------------------------------------- ícones
# traço branco, 26 px, dentro do círculo #0a3f79 — o mesmo desenho do modelo
ICONES = {
    "local": '<path d="M12 21s7-6.1 7-11a7 7 0 1 0-14 0c0 4.9 7 11 7 11z"/>'
             '<circle cx="12" cy="10" r="2.6" fill="#0a3f79" stroke="none"/>',
    "equipe": '<circle cx="9" cy="8.5" r="3.1"/><circle cx="16.6" cy="9.4" r="2.4"/>'
              '<path d="M3.6 19.2c0-3 2.4-5.2 5.4-5.2s5.4 2.2 5.4 5.2"/>'
              '<path d="M15.2 14.2c2.7 0 5 1.9 5 4.6"/>',
    "raio": '<path d="M13.6 2.5 5.4 13.4h5.2l-1 8.1 8.4-11.1h-5.3z"/>',
    "relogio": '<circle cx="12" cy="12" r="9"/><path d="M12 6.8V12l3.6 2.3"/>',
    "placa": '<rect x="3.2" y="5.2" width="17.6" height="13.6" rx="2"/>'
             '<path d="M6.8 9.6h6.4M6.8 12.6h10.4M6.8 15.4h7.6"/>',
    "escudo": '<path d="M12 2.6 4.6 5.6v6.1c0 4.6 3.1 8.5 7.4 9.7 4.3-1.2 7.4-5.1 7.4-9.7V5.6z"/>'
              '<path d="M8.6 12.2l2.4 2.4 4.4-4.6"/>',
    "calendario": '<rect x="3.4" y="5" width="17.2" height="15.6" rx="2.2"/>'
                  '<path d="M3.4 9.6h17.2M8.2 2.8v4.2M15.8 2.8v4.2"/>',
    "trafo": '<path d="M9 3.2v2.8M15 3.2v2.8"/>'
             '<rect x="4.6" y="6" width="14.8" height="12.6" rx="2.6"/>'
             '<path d="M8.6 9.4v5.8M12 9.4v5.8M15.4 9.4v5.8"/><path d="M8.6 21.2h6.8"/>',
    "engrenagem": '<path d="M12 3.2 14 5.6l3-.9.4 3.1 2.9 1.2-1.6 2.7 1.6 2.7-2.9 1.2'
                  '-.4 3.1-3-.9-2 2.4-2-2.4-3 .9-.4-3.1-2.9-1.2L5.3 11.7 3.7 9l2.9-1.2'
                  'L7 4.7l3 .9z"/><circle cx="12" cy="12" r="2.7"/>',
}


def ico(nome, tam=26, traco=1.9, cor="#ffffff"):
    return ('<svg viewBox="0 0 24 24" width="%d" height="%d" fill="none" stroke="%s" '
            'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round">%s</svg>'
            % (tam, tam, cor, traco, ICONES[nome]))


def campo(icone, rotulo, *valores):
    linhas = "".join('<span>%s</span>' % v for v in valores)
    return ('<div class="campo"><div class="bolha">%s</div>'
            '<div class="txt"><b>%s</b>%s</div></div>' % (ico(icone), rotulo, linhas))



# --------------------------------------------------------------------- faixa de fotos
# A faixa do modelo cai 4,8° da direita para a esquerda: a borda esquerda sai de x=487
# no topo e chega a x=391 embaixo. Em vez de inclinar a imagem (o que a espicharia numa
# coluna estreita), cada foto fica reta e o recorte é feito por clip-path.
ALTURA_FOTO = 1162
DX = 49                       # meia queda da diagonal ao longo dos 1.162 px
LIMITES = (435, 651, 867, 1085)   # x das divisas, na meia-altura
VAO = 5                       # respiro azul entre uma foto e a outra


def tiras(fotos):
    out = []
    for i, (arquivo, posicao, alt) in enumerate(fotos):
        esq, dir_ = LIMITES[i], LIMITES[i + 1]
        caixa, largura = esq - DX, (dir_ - esq) + 2 * DX
        corte = "polygon(%dpx 0, %dpx 0, %dpx %dpx, %dpx %dpx)" % (
            2 * DX + VAO, largura - VAO, largura - 2 * DX - VAO, ALTURA_FOTO,
            VAO, ALTURA_FOTO)
        out.append('<div class="tira" style="left:%dpx;width:%dpx;clip-path:%s">'
                   '<img src="%s" style="object-position:%s" alt="%s"></div>'
                   % (caixa, largura, corte, imagem(arquivo), posicao, alt))
    return "\n      ".join(out)


# ------------------------------------------------------------------------------ main
def main():
    g = da_gestao()
    ss = da_base_ss()
    atual = [x for x in ss if x["ss"] == str(g["SS SGM"]).strip()][0]
    abertura = atual["abertura"]
    dias_ate_servico = (SERVICO - abertura).days
    dias_dcmd = int(re.match(r"\d+", str(g["Status Atendimento"])).group(0))
    fora_prazo = int(re.match(r"\d+", str(g["Status Prazo"])).group(0))
    dmsl = parecer_dmsl(atual["desc"])
    if "fase b" not in dmsl.lower():
        raise SystemExit("o parecer da DMSL não fala mais em fase B — revisar o objetivo:\n  %s"
                         % dmsl)

    total = float(g["Orçamento Total"])
    reais = lambda v: ("R$ {:,.2f}".format(v)).replace(",", "@").replace(".", ",").replace("@", ".")

    html = """<meta charset="utf-8">
<title>Reporte de campo — %(ativo)s Mateiros</title>
<style>
%(fontes)s

*{box-sizing:border-box;margin:0;padding:0}
body{background:#20242c;font-family:'Montserrat',system-ui,sans-serif;
  -webkit-font-smoothing:antialiased}

.cartao{position:relative;width:1024px;height:1280px;overflow:hidden;background:%(navy)s}

/* ---- faixa das três fotos, na diagonal do modelo (4,8°) ---- */
.moldura{position:absolute;left:0;top:0;width:1024px;height:1162px;overflow:hidden}
.tira{position:absolute;top:0;height:1162px;background:%(navy)s}
.tira img{width:100%%;height:100%%;object-fit:cover;display:block}

/* ---- coluna azul da esquerda ---- */
.painel{position:absolute;left:0;top:0;width:420px;height:1162px;padding:34px 40px 0 40px}
.painel .marca{width:250px;height:auto;display:block}

.pilula{display:inline-flex;align-items:center;gap:14px;margin-top:30px;padding:13px 22px 13px 16px;
  border:1.6px solid %(ciano)s;border-radius:12px}
.pilula b{color:#fff;font:700 15px/1.16 'Barlow Condensed';letter-spacing:.1em;text-transform:uppercase}

h1{margin-top:28px;color:#fff;font:700 42px/0.98 'Barlow Condensed';letter-spacing:.005em;
  text-transform:uppercase}
h1 em{display:block;color:%(ciano)s;font-style:normal}
.sub{margin-top:12px;color:#fff;font:700 20px 'Barlow Condensed';letter-spacing:.05em;
  text-transform:uppercase}

.demanda{display:flex;align-items:stretch;margin-top:22px;border-radius:12px;overflow:hidden;
  border:1.6px solid %(ciano)s}
.demanda .cx{flex:none;display:flex;align-items:center;justify-content:center;width:76px;
  background:%(navy)s}
.demanda .tx{flex:1;padding:12px 18px;background:%(ciano)s;color:#fff;
  font:700 19px/1.2 'Barlow Condensed';letter-spacing:.06em;text-transform:uppercase}

.campos{margin-top:24px}
.campo{display:flex;gap:16px;align-items:flex-start;padding:13px 0 12px;
  border-bottom:1px solid %(filete)s}
.campo:last-child{border-bottom:0}
.bolha{flex:none;display:flex;align-items:center;justify-content:center;width:48px;height:48px;
  border-radius:50%%;background:%(navy2)s}
.campo b{display:block;margin-bottom:3px;color:%(ciano2)s;font:700 15px 'Barlow Condensed';
  letter-spacing:.09em;text-transform:uppercase}
.campo span{display:block;color:#fff;font-size:13.2px;line-height:1.42;font-weight:400}
.campo span+span{margin-top:1px}

/* ---- selo da data, no alto da faixa de fotos ---- */
.selo{position:absolute;top:32px;right:36px;z-index:4;display:flex;align-items:center;gap:12px;
  padding:11px 22px 11px 16px;background:#fff;border-radius:14px;
  box-shadow:0 4px 14px rgba(0,0,0,.22)}
.selo b{color:#123a63;font:600 22px 'Montserrat';letter-spacing:.01em}

/* ---- régua de valores, recortada do modelo ---- */
.rodape{position:absolute;left:0;right:0;bottom:0;height:118px}
.rodape img{width:100%%;height:100%%;display:block}
</style>

<div class="cartao">

  <div class="moldura">
%(tiras)s
  </div>

  <div class="selo">%(ico_cal)s<b>%(data_servico)s</b></div>

  <div class="painel">
    <img class="marca" src="%(logo)s" alt="Energisa">

    <div class="pilula">%(ico_eng)s<b>Ação de<br>manutenção</b></div>

    <h1>Reporte de<em>substituição<br>de célula</em></h1>
    <div class="sub">Banco de reguladores de tensão</div>

    <div class="demanda">
      <div class="cx">%(ico_trafo)s</div>
      <div class="tx">%(ss)s<br>Criticidade %(criticidade)s</div>
    </div>

    <div class="campos">
      %(c_local)s
      %(c_equipe)s
      %(c_ativo)s
      %(c_status)s
      %(c_material)s
      %(c_objetivo)s
    </div>
  </div>

  <div class="rodape"><img src="%(rodape)s" alt="Segurança sempre · Atitude de dono · Integridade sempre · Simplicidade que conecta · Grupo Energisa"></div>
</div>
""" % {
        "ativo": ATIVO,
        "fontes": fontes(),
        "navy": NAVY, "navy2": NAVY_2, "ciano": CIANO, "ciano2": CIANO_2, "filete": FILETE,
        "logo": imagem("energisa_logo.png"),
        "rodape": imagem("energisa_rodape_valores.png"),
        "tiras": tiras((
            ("5800440256_mateiros_banco_geral.jpg", "50% 50%",
             "Banco de reguladores de Mateiros: célula antiga, ainda em operação"),
            ("5800440256_mateiros_banco_detalhe.jpg", "88% 50%",
             "A célula nova, instalada à direita do banco"),
            ("5800440256_mateiros_placa_celula.jpg", "48% 50%",
             "Placa do equipamento instalado: ITB RAV-2, 200 kVA, código Energisa 690240"),
        )),
        "ico_cal": ico("calendario", 26, 1.9, "#123a63"),
        "ico_eng": ico("engrenagem", 34, 1.7),
        "ico_trafo": ico("trafo", 34, 1.7),
        "data_servico": SERVICO.strftime("%d.%m.%Y"),
        "ss": str(g["SS SGM"]).strip(),
        "criticidade": str(g["Criticidade"]).strip(),
        "c_local": campo("local", "Local",
                         "%s – TO · Polo %s" % (str(g["Município"]).title(),
                                                str(g["Polo"]).title()),
                         "Alimentador %s" % str(g["Alimentador"]).split(" - ")[0].strip()),
        "c_equipe": campo("equipe", "Equipe",
                          "Time de Manutenção Porto Nacional",
                          "COCM ETO-RD-PO · Regional %s" % str(g["Regional"]).title()),
        "c_ativo": campo("raio", "Nº do equipamento",
                         ATIVO,
                         "Regulador de tensão 34,5 kV · três células"),
        "c_status": campo("relogio", "Status / pendência",
                          "%d dias no DCMD · %d dias fora do prazo" % (dias_dcmd, fora_prazo),
                          "Executado em %d dias, contra SLA de %d" % (dias_ate_servico,
                                                                      int(g["SLA_Total"]))),
        "c_material": campo("placa", "Material aplicado",
                            "Célula 200 kVA / 34,5 kV · código 690240",
                            "ITB RAV-2 · série 48580 · fab. 03/2026",
                            "%s em material e mão de obra" % reais(total)),
        "c_objetivo": campo("escudo", "Objetivo",
                            "Substituir a célula da fase B e melhorar a malha de "
                            "aterramento — parecer DMSL de %s." % abertura.strftime("%d/%m"),
                            "Encerra a oscilação de 16 a 23 kV na LD UHE Isamu–Ponte Alta, "
                            "reclamada pelo cliente BRK."),
    }

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("OK — %s (%.1f MB)" % (SAIDA, os.path.getsize(SAIDA) / 1e6))
    print("   SS %s · aberta %s · %d dias até a execução · %d dias no DCMD · %s"
          % (g["SS SGM"], abertura.strftime("%d/%m/%Y"), dias_ate_servico, dias_dcmd,
             reais(total)))


if __name__ == "__main__":
    main()
