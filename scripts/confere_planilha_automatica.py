"""
Confere dist/GESTAO_AUTOMATICA.xlsx calculando as fórmulas com a biblioteca `formulas`
(LibreOffice não roda aqui). O que se checa:

  - Gestão: o total em fórmula bate com o total da carteira nos 53 (coluna «Bate?»);
  - Lançamento: os quatro exemplos dão código, descrição, preço e total esperados;
  - Falha Equipamentos: tensão, custo e chave preenchidos em todas as 90 linhas;
  - Resumo: 35 · 28 · 18 · 9 falhas por fatia;
  - estrutura: listas de validação, nomes definidos e tabelas existem.

Rodar: python3 scripts/confere_planilha_automatica.py [arquivo.xlsx]
"""

import os
import sys

import formulas
from openpyxl import load_workbook

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQ = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "dist", "GESTAO_AUTOMATICA.xlsx")


def valor(sol, aba, ref):
    alvo = f"'[{os.path.basename(ARQ)}]{aba}'!{ref}".upper()
    for k, v in sol.items():
        if k.upper() == alvo:
            x = v.value
            try:
                x = x[0][0]
            except (TypeError, IndexError):
                pass
            return x
    raise KeyError(alvo)


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def main():
    erros, ok = [], []
    wb = load_workbook(ARQ)
    # estrutura
    nomes = set(wb.defined_names.keys())
    for n in ("Pecas_RL", "Pecas_RT", "Pecas_Todas", "Tensoes", "Potencias", "Criticidades",
              "Status_DCMD", "Sim_Nao", "Causas"):
        (ok if n in nomes else erros).append(f"nome definido {n}")
    for aba, n_dv in (("Lançamento", 4), ("Gestão", 5), ("Falha Equipamentos", 5)):
        q = len(wb[aba].data_validations.dataValidation)
        (ok if q >= n_dv else erros).append(f"{aba}: {q} validações (esperado ≥ {n_dv})")
    for aba, tab in (("Lançamento", "Lancamento"), ("Gestão", "Gestao"), ("Falha Equipamentos", "Falhas")):
        (ok if tab in wb[aba].tables else erros).append(f"tabela {tab} em {aba}")
    peca_dv = [dv for dv in wb["Lançamento"].data_validations.dataValidation if "Pecas_" in str(dv.formula1)]
    (ok if peca_dv else erros).append("lista de peça dependente do tipo (INDIRECT) no Lançamento")

    # cálculo
    print("calculando as fórmulas…", flush=True)
    xl = formulas.ExcelModel().loads(ARQ).finish()
    sol = xl.calculate()

    # Gestão: total novo × total carteira
    ws = wb["Gestão"]
    bate, nao = 0, []
    for r in range(5, 5 + 53):
        ativo = ws[f"A{r}"].value
        p, v = num(valor(sol, "Gestão", f"P{r}")), num(ws[f"V{r}"].value)
        if p is not None and v is not None and abs(p - v) < 0.01:
            bate += 1
        else:
            nao.append((ativo, ws[f"S{r}"].value, p, v))
    (ok if bate == 53 else erros).append(f"Gestão: {bate} de 53 totais batem com a carteira; divergem: {nao}")
    w = valor(sol, "Gestão", "W59")
    (ok if str(w).startswith("53 de 53") else erros).append(f"Gestão W59 = {w!r}")

    # Lançamento: exemplos
    esperado = {
        5: dict(H="690005", J=38151.48, K=38151.48, L=13209.34, M=51360.82, D="RL", E="34,5",
                I="Tanque / Parte ativa — Religador 34,5 kV · NOJA RC10 · cód. 690005"),
        6: dict(H="690241", J=90230.0, K=180460.0, L=80318.5, M=260778.5, D="RT", E="34,5", G="400",
                I="Célula — Regulador 34,5 kV / 400 kVA · ITB / RUA · cód. 690241"),
        7: dict(H="690001 + 690916", J=55602.54, K=55602.54, L=11016.94, M=66619.48, D="RL", E="13,8"),
        8: dict(H="651638", J=23259.6, K=23259.6, L=20000.0, M=43259.6, D="RT", E="13,8"),
    }
    for r, campos in esperado.items():
        for c, e in campos.items():
            v = valor(sol, "Lançamento", f"{c}{r}")
            certo = (abs(num(v) - e) < 0.01) if isinstance(e, float) else (str(v) == e)
            (ok if certo else erros).append(f"Lançamento {c}{r}: {v!r} (esperado {e!r})")
    # linha vazia não pode dar erro nem lixo
    for c in ("D", "E", "I", "K", "M", "T"):
        v = valor(sol, "Lançamento", f"{c}20")
        (ok if v in ("", None) or str(v) == "" else erros).append(f"Lançamento {c}20 vazia = {v!r}")

    # Falha Equipamentos
    ws = wb["Falha Equipamentos"]
    sem = []
    for r in range(5, 5 + 90):
        t, u, m = valor(sol, "Falha Equipamentos", f"AB{r}"), valor(sol, "Falha Equipamentos", f"U{r}"), \
            valor(sol, "Falha Equipamentos", f"M{r}")
        if not t or num(u) is None or m not in ("13,8", "34,5"):
            sem.append((ws[f"C{r}"].value, ws[f"I{r}"].value, t, u, m))
    (ok if not sem else erros).append(f"Falha Equipamentos: {90 - len(sem)} de 90 com tensão, chave e custo; faltam: {sem}")
    r_caseara = [r for r in range(5, 95) if ws[f"C{r}"].value == "7930359149"][0]
    v = valor(sol, "Falha Equipamentos", f"M{r_caseara}")
    (ok if v == "34,5" else erros).append(f"7930359149 (Caseara) tensão = {v!r}")
    # furto: 3 células de 400 a 90.230 + MO 80.318,50 = 351.008,50
    r_furto = [r for r in range(5, 95) if ws[f"C{r}"].value == "5858783119"][0]
    v = num(valor(sol, "Falha Equipamentos", f"U{r_furto}"))
    (ok if v and abs(v - 351008.5) < 0.01 else erros).append(f"5858783119 furto = 3 células 400: {v}")

    # Resumo
    for ref, e in (("B14", 35), ("C14", 28), ("D14", 18), ("E14", 9)):
        v = num(valor(sol, "Resumo", ref))
        (ok if v == e else erros).append(f"Resumo {ref} = {v} (esperado {e})")

    print(f"\n{len(ok)} conferências ok · {len(erros)} erro(s)")
    for e in erros:
        print("  ERRO:", e)
    return 1 if erros else 0


if __name__ == "__main__":
    sys.exit(main())
