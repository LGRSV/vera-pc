"""Tabela unificada das cadeias 2024-25 com o rótulo vigente (verificação > leitura)."""
import json, glob, os, sys, datetime as dt
from collections import Counter, defaultdict
RAIZ='/home/user/vera-pc'; sys.path.insert(0, RAIZ+'/scripts')
import base_eqp as be, falha_dcmd_mae as fm
A=RAIZ+'/data/analise_ia'
BIG={'tanque','controle','celula','rele','completo','furto'}

mae=json.load(open(f'{A}/falha_dcmd_mae.json'))['linhas']
cat=[]; 
for f in sorted(glob.glob(f'{A}/categoria_dcmd/out*.json')): cat+=json.load(open(f))
fora=[]
for f in sorted(glob.glob(f'{A}/falha_fora_dcmd/f*.json')): fora+=json.load(open(f))
ver=[]
for f in sorted(glob.glob(f'{A}/verificacao_peca_grande/v*.json')): ver+=json.load(open(f))
n26=[]
for f in sorted(glob.glob(f'{A}/leitura_2026/n*.json')): n26+=json.load(open(f))
cat_by={x['cadeia']:x for x in cat}; ver_by={x['cadeia']:x for x in ver}

est={}
for x in mae:
    o={'ativo':x['ativo'],'cadeia':x['cadeia'],'fonte':'mae','familia':x['fam'],'data':x['abert'],
       'categoria_leitura': x['peca'] if x['falha'] else (cat_by.get(x['cadeia'],{}).get('categoria') or 'nao identificado'),
       'item': cat_by.get(x['cadeia'],{}).get('item',''), 'executada':x['executada'],
       'evidencia':x['evidencia'],'motivo':x['motivo'],'confianca':x['confianca'],'verificada':False}
    o['categoria_vigente']=o['categoria_leitura']
    est[x['cadeia']]=o
for x in fora:
    o={'ativo':x['ativo'],'cadeia':x['cadeia'],'fonte':'fora','familia':x['familia'],'data':x['data_primeira_ss'],
       'categoria_leitura':x['categoria'],'item':x.get('item',''),'executada':x.get('executada'),
       'evidencia':x.get('evidencia',''),'motivo':x.get('motivo',''),'confianca':x.get('confianca'),'verificada':False}
    v=ver_by.get(x['cadeia'])
    if v:
        o['verificada']=True; o['ver_mantem']=v['mantem']; o['ver_porque']=v['porque']; o['ver_confianca']=v['confianca']
        o['categoria_vigente']= x['categoria'] if v['mantem'] else v['categoria_final']
    else:
        o['categoria_vigente']=x['categoria']
    est[x['cadeia']]=o

# dossiê 2024-25: mesmas cadeias do recorte
reg,prox,comeco=be.ler()
todas=fm.monta_cadeias(reg,prox,comeco)
alvo=[c for c in todas if reg[c[0]]['abert'] and reg[c[0]]['abert'].year in (2024,2025)
      and (fm.do_dcmd(c,reg) or reg[c[0]]['pend'] in be.PENDENCIA_FALHA)]
print("dossiê 2024-25:", len(alvo), "cadeias em", len({reg[c[0]]['ativo'] for c in alvo}), "ativos")
sem=[c for c in alvo if c[0] not in est]
print("sem veredito anterior:", len(sem), "por ano:", Counter(reg[c[0]]['abert'].year for c in sem),
      "dcmd:", sum(1 for c in sem if fm.do_dcmd(c,reg)), "pend:", Counter(reg[c[0]]['pend'] for c in sem).most_common(4))
# leitura_2026 keys: 'NNNNN/AAAA' sem posto — tenta casar pelo sufixo
suf26={}
for x in n26:
    suf26.setdefault(x['cadeia'],[]).append(x)
casa=0; amb=0
for c in sem:
    s=c[0].split(' ',1)[-1] if ' ' in c[0] else c[0]
    cands=[x for x in suf26.get(s,[]) if x['ativo']==reg[c[0]]['ativo']]
    if len(cands)==1:
        x=cands[0]; casa+=1
        est[c[0]]={'ativo':x['ativo'],'cadeia':c[0],'fonte':'n26','familia':x['familia'],'data':x['data_primeira_ss'],
                   'categoria_leitura':x['categoria'],'item':x.get('item',''),'executada':x.get('executada'),
                   'evidencia':x.get('evidencia',''),'motivo':x.get('motivo',''),'confianca':x.get('confianca'),
                   'verificada':False,'categoria_vigente':x['categoria']}
    elif len(cands)>1: amb+=1
print("casadas com leitura_2026:", casa, "ambíguas:", amb, "ainda sem veredito:", len([c for c in alvo if c[0] not in est]))
print("cadeias de est fora do dossiê:", len([k for k in est if k not in {c[0] for c in alvo}]))

# só o que está no dossiê
alvo_set={c[0] for c in alvo}
E={k:v for k,v in est.items() if k in alvo_set}
print("\nvigente por categoria:", Counter(v['categoria_vigente'] for v in E.values()).most_common())
print("peça grande vigente por fonte:", Counter((v['fonte'],v['categoria_vigente']) for v in E.values() if v['categoria_vigente'] in BIG).most_common())
print("peça grande vigente por ano/familia:", Counter((v['data'][:4],v['familia'],v['categoria_vigente']) for v in E.values() if v['categoria_vigente'] in BIG).most_common())
print("ativos com peça grande vigente:", len({v['ativo'] for v in E.values() if v['categoria_vigente'] in BIG}))
json.dump({'cadeias':E,'sem_veredito':[c[0] for c in alvo if c[0] not in est]}, open(os.path.dirname(os.path.abspath(__file__))+'/estado_2425.json','w'), ensure_ascii=False, indent=0)
