"""
Extrai o recorte de religador e regulador da base crua de SS/OS.

A base crua é um texto com separador «@» e a descrição quebrando linha — um
registro ocupa várias linhas. Aqui os registros são remontados pelo padrão do
número da SS e fica só quem tem NUM_TRAFO de religador (79…) ou regulador (58…),
com 10 dígitos. É o mesmo recorte que gerou o ssos_min original, validado por
reproduzir byte a byte os 6.305 registros da extração de 11/08.

Grava data/missao/ssos_min.json com os mesmos 20 campos de sempre.

Rodar: python3 scripts/extrai_ssos_min.py [caminho_da_base ...]
"""

import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
import cadeia_obra as co  # noqa: E402  — o remontador de registros mora lá

SAIDA = os.path.join(RAIZ, "data", "missao", "ssos_min.json")
RE_RLRT = re.compile(r"(79|58)\d{8}$")

CAMPOS = {
    "NUMERO_SS": 0, "NUMERO_OS": 1, "NUM_OBRA": 2, "ORIGEM_SS": 3, "ESQUEMA": 7,
    "ANO": 9, "ORG_SOLIC": 10, "COD_EQUIPE": 11, "NUM_TRAFO": 13,
    "CRITICIDADE_SS": 17, "SITUACAO_SS": 18, "DATA_ABERTURA_SS": 19,
    "DATA_TERMINO_SS": 20, "DATA_LIMITE_SS": 21, "DESCICAO_DO_ATIVO": 22,
    "LOCALIDADE": 23, "SOLICITANTE": 24, "TIPOSS": 26,
    # estes dois moram na cauda do registro, depois da descrição livre
    "FABRICANTE_INSTALADO": 31, "FABRICANTE_RETIRADO": 32,
}
N_FRENTE, N_CAUDA, N_TOTAL = 27, 35, 64


def _normaliza(campos):
    """Devolve o registro com exatamente 64 campos, colapsando «@» do texto livre."""
    if len(campos) == N_TOTAL:
        return campos
    if len(campos) > N_TOTAL:
        frente, cauda = campos[:N_FRENTE], campos[-N_CAUDA:]
        miolo = campos[N_FRENTE:len(campos) - N_CAUDA]
        miolo = ["@".join(miolo[:-1]), miolo[-1]] if len(miolo) >= 2 else miolo + [""]
        return frente + miolo + cauda
    return campos + [""] * (N_TOTAL - len(campos))


def extrair(caminhos):
    saida = []
    for caminho in caminhos:
        buffer = None
        with open(caminho, encoding="latin-1") as fh:
            for i, linha in enumerate(fh):
                linha = linha.rstrip("\r\n")
                if i == 0 and linha.startswith("NUMERO_SS@"):
                    continue
                if co.RE_INICIO.match(linha):
                    if buffer is not None:
                        yield_um(buffer, saida)
                    buffer = linha
                elif buffer is not None:
                    buffer += "\n" + linha
            if buffer is not None:
                yield_um(buffer, saida)
    return saida


def yield_um(bruto, saida):
    campos = _normaliza(bruto.split("@"))
    cod = campos[CAMPOS["NUM_TRAFO"]].strip()
    if not RE_RLRT.fullmatch(cod):
        return
    saida.append({nome: campos[pos].strip() for nome, pos in CAMPOS.items()})


def main():
    caminhos = sys.argv[1:] or co.PARTES
    registros = extrair(caminhos)
    from collections import Counter
    anos = Counter(r["ANO"] for r in registros)
    datas = [r["DATA_ABERTURA_SS"] for r in registros if r["DATA_ABERTURA_SS"]]
    iso = sorted(f"{d[6:10]}-{d[3:5]}-{d[:2]}" for d in datas if len(d) >= 10)
    print(f"registros de RL/RT: {len(registros)}")
    print(f"por ano: {dict(sorted(anos.items()))}")
    print(f"abertura: {iso[0]} a {iso[-1]}")
    with open(SAIDA, "w", encoding="utf-8") as fh:
        json.dump(registros, fh, ensure_ascii=False)
    print(f"gravado: {SAIDA}")


if __name__ == "__main__":
    main()
