#!/usr/bin/env python3
"""Pacote compacto de revisão: histórico do ativo, veredito anterior por cadeia e texto deduplicado.
Uso: pack.py --parte N [--n K] [--kb KB]   (próximos itens da parte sem revisão, até KB)
     pack.py ATIVO [ATIVO...]
"""
import json, sys, re, os, datetime as dt
from collections import defaultdict
SP=os.path.dirname(os.path.abspath(__file__)); import os as _o; SP=SP if _o.path.exists(SP+'/estado_2425.json') else '/home/user/vera-pc/.analise/revisao-2425/ferramentas'
RUN='/home/user/vera-pc/.analise/revisao-2425'
sys.path.insert(0,'/home/user/vera-pc/scripts')
import base_eqp as be, falha_dcmd_mae as fm
E=json.load(open(SP+'/estado_2425.json'))['cadeias']
T=json.load(open(SP+'/tiers_2425.json'))
reg,prox,comeco=be.ler()
todas=fm.monta_cadeias(reg,prox,comeco)
por_ativo=defaultdict(list)
for c in todas: por_ativo[reg[c[0]]['ativo']].append(c)
JAN=90
MARCA_A='[... = texto da '
MARCA_B=' ...]'

def norm(t): return re.sub(r'[ \t]+',' ',re.sub(r'\n\s*\n+','\n',t or '')).strip()

def fam(d):
    if d['ativo'][:2] in ('79','78'): return 'RL'
    if d['ativo'][:2]=='58': return 'RT'
    return d['tipo']

def texto_dedup(t, vistos):
    t=norm(t)
    if not t: return '(sem descrição)'
    for ss,p in vistos:
        if t==p: return '(= texto da %s)' % ss
    usados=set()
    while True:
        best=None
        for ss,p in vistos:
            if ss in usados or len(p)<60: continue
            i=t.find(p)
            if i>=0 and (best is None or len(p)>len(best[1])): best=(ss,p,i)
        if not best: break
        ss,p,i=best; usados.add(ss)
        t=t[:i]+'\n'+MARCA_A+ss+MARCA_B+'\n'+t[i+len(p):]
    return t.strip()

def pack(a):
    cs=sorted(por_ativo[a], key=lambda c: reg[c[0]]['abert'] or dt.date(1900,1,1))
    info=T.get(a,{}); alvo=set(info.get('cadeias',[]))
    d0=reg[cs[0][0]]
    L=['#'*80, 'ATIVO %s · %s · %s · alim %s · nível %s' % (a, fam(d0), d0['loc'], d0['alimentador'], info.get('tier','?')), '#'*80]
    L.append('HISTÓRICO (%d cadeias):' % len(cs))
    datas_alvo=[reg[c[0]]['abert'] for c in cs if c[0] in alvo]
    for c in cs:
        d=reg[c[0]]; u=reg[c[-1]]
        e=E.get(c[0]); lab='—'
        if e:
            lab=e['categoria_vigente']+('' if e['categoria_vigente']==e['categoria_leitura'] else ' (leitura: %s)'%e['categoria_leitura'])+' ['+e['fonte']+']'
        L.append('  %s%s · ab %s · %d SS · %s · %s · %s · %s' % ('>> ' if c[0] in alvo else '   ', c[0], d['abert'], len(c), ' > '.join(reg[s]['posto'] for s in c), u['status'], d['pend'][:22], lab))
    vistos=[]
    for c in cs:
        d=reg[c[0]]
        perto=any(abs((d['abert']-x).days)<=JAN for x in datas_alvo if d['abert'] and x)
        if c[0] not in alvo and not perto: continue
        L.append('')
        if c[0] in alvo:
            e=E.get(c[0],{})
            L.append('>>> REVISAR %s · aberta %s · ocorrência %s · %d SS' % (c[0], d['abert'], d['ocor'], len(c)))
            s_=info.get('suspeitas',{}).get(c[0],[])
            if s_:
                s_=[x for x in s_ if not x.startswith('cancelamento_em_bloco')]+(['cancelamento_em_bloco(%d SS)' % sum(1 for x in info['suspeitas'][c[0]] if x.startswith('cancelamento_em_bloco'))] if any(x.startswith('cancelamento_em_bloco') for x in info['suspeitas'][c[0]]) else [])
                L.append('    suspeitas: '+', '.join(s_))
            if e:
                L.append('    ANTERIOR [%s]: %s%s · item=%s · executada=%s · conf=%s' % (e['fonte'], e['categoria_leitura'], '' if e['categoria_vigente']==e['categoria_leitura'] else ' -> vigente %s'%e['categoria_vigente'], e.get('item') or '', e.get('executada'), e.get('confianca')))
                if e.get('evidencia'): L.append('    evidência: «%s»' % norm(e['evidencia'])[:220])
                if e.get('motivo'): L.append('    motivo: %s' % e['motivo'][:220])
                if e.get('verificada'): L.append('    verificação: mantém=%s · %s' % (e['ver_mantem'], e['ver_porque'][:200]))
            else:
                L.append('    ANTERIOR: (sem veredito)')
        else:
            L.append('... contexto %s · aberta %s · %d SS (fora do escopo, a %d dias)' % (c[0], d['abert'], len(c), min(abs((d['abert']-x).days) for x in datas_alvo)))
        for s in c:
            r=reg[s]
            L.append('    - %s | %s | %s | %s | %s -> %s' % (s, r['posto'], r['status'], r['pend'][:30], r['abert'], r['concl'] or '—'))
            t=texto_dedup(r['desc'], vistos)
            L.append('      '+t.replace('\n','\n      '))
            if r['desc'].strip(): vistos.append((s, norm(r['desc'])))
    return '\n'.join(L)

if __name__=='__main__':
    args=sys.argv[1:]
    if args and args[0]=='--parte':
        p=args[1]; n=8; kb=26
        if '--n' in args: n=int(args[args.index('--n')+1])
        if '--kb' in args: kb=int(args[args.index('--kb')+1])
        man=json.load(open(RUN+'/manifesto.json'))
        feitos=set()
        cam=RUN+'/dados/revisao/%s.jsonl'%p
        if os.path.exists(cam):
            for ln in open(cam):
                try: feitos.add(json.loads(ln)['_chave'])
                except Exception: pass
        cand=[x for x in man['partes'][p] if x not in feitos]
        ativos=[]; partes=[]; tot=0
        for a in cand:
            pk=pack(a)
            if ativos and tot+len(pk.encode())>kb*1024: break
            ativos.append(a); partes.append(pk); tot+=len(pk.encode())+2
            if len(ativos)>=n: break
        out='\n\n'.join(partes)
    else:
        ativos=args; out='\n\n'.join(pack(a) for a in ativos)
    print(out)
    sys.stderr.write('%d ativos · %d KB · %s\n' % (len(ativos), len(out.encode())//1024, ' '.join(ativos)))
