#!/usr/bin/env python3
"""Check semantic invariants before/after CUMCM prose humanization."""
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

MATH_ENVS=('equation','equation*','align','align*','aligned','gather','gather*','multline','multline*','cases','matrix','pmatrix','bmatrix','vmatrix')
REF_COMMANDS=('cite','citep','citet','ref','eqref','autoref','label','SI','si','num')
STRONG_CLAIMS=('全局最优','唯一最优','严格证明','充分证明','有力证明','完全证明','普适','必然导致','证明了')
SCOPE_MARKERS=('局部最优','当前搜索域','当前搜索范围','所考察参数范围','预算内','候选','未收敛','不收敛','未证明','不能证明','不作全局最优','在该条件下','在上述条件下','模型内')
CAUSAL_WORDS=('导致','因果','证明')
OPTIMUM_WORDS=('最优','最大值','最小值','最佳')
NUMBER_RE=re.compile(r'(?<![A-Za-z_])[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?%?')

def read(path): return Path(path).read_text(encoding='utf-8-sig',errors='replace')

def extract_envs(text):
    out=[]
    for env in MATH_ENVS:
        pat=re.compile(rf'\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}',re.S)
        out.extend(m.group(0) for m in pat.finditer(text))
    out.extend(m.group(0) for m in re.finditer(r'\\\[.*?\\\]',text,re.S))
    out.extend(m.group(0) for m in re.finditer(r'\\\(.*?\\\)',text,re.S))
    out.extend(m.group(0) for m in re.finditer(r'(?<!\\)\$\$.*?(?<!\\)\$\$',text,re.S))
    out.extend(m.group(0) for m in re.finditer(r'(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$',text))
    return out

def extract_commands(text):
    names='|'.join(map(re.escape,REF_COMMANDS))
    pat=re.compile(rf'\\(?:{names})\*?(?:\[[^\]]*\])?\{{[^{{}}]*\}}')
    return [m.group(0) for m in pat.finditer(text)]

def extract_fenced_code(text):
    return [m.group(0) for m in re.finditer(r'```[^\n]*\n.*?```',text,re.S)]

def compare_counter(name,a,b,critical=True):
    ca,cb=Counter(a),Counter(b)
    lost=list((ca-cb).elements()); added=list((cb-ca).elements())
    return {'name':name,'critical':critical,'passed':not lost and not added,'lost':lost[:50],'added':added[:50],'original_count':sum(ca.values()),'rewritten_count':sum(cb.values())}

def added_by_count(terms, original, rewritten):
    """Return terms whose occurrence count increased after rewriting."""
    return [term for term in terms if rewritten.count(term) > original.count(term)]

def claim_guard(original,rewritten):
    added_strong=added_by_count(STRONG_CLAIMS,original,rewritten)
    orig_scope={term for term in SCOPE_MARKERS if term in original}
    new_scope={term for term in SCOPE_MARKERS if term in rewritten}
    scope_all_removed=bool(orig_scope) and not new_scope
    added_causal=added_by_count(CAUSAL_WORDS,original,rewritten)
    optimum_still_asserted=any(term in rewritten for term in OPTIMUM_WORDS)
    scope_loss_with_optimum=scope_all_removed and optimum_still_asserted
    passed=not added_strong and not added_causal and not scope_loss_with_optimum
    return {
        'name':'claim_guard',
        'critical':True,
        'passed':passed,
        'added_strong_claims':added_strong,
        'added_causal_or_proof_words':added_causal,
        'scope_markers_original':sorted(orig_scope),
        'scope_markers_rewritten':sorted(new_scope),
        'scope_all_removed_warning':scope_all_removed,
        'scope_loss_with_optimum_failure':scope_loss_with_optimum,
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--original',required=True); ap.add_argument('--rewritten',required=True); ap.add_argument('--json',action='store_true',dest='as_json'); ap.add_argument('--allow-number-formatting',action='store_true'); a=ap.parse_args()
    o,r=read(a.original),read(a.rewritten)
    checks=[]
    checks.append(compare_counter('math_spans',extract_envs(o),extract_envs(r),True))
    checks.append(compare_counter('latex_refs_cites_labels_units',extract_commands(o),extract_commands(r),True))
    checks.append(compare_counter('fenced_code',extract_fenced_code(o),extract_fenced_code(r),True))
    if not a.allow_number_formatting:
        checks.append(compare_counter('numbers',NUMBER_RE.findall(o),NUMBER_RE.findall(r),True))
    else:
        checks.append({'name':'numbers','critical':False,'passed':True,'note':'number formatting comparison explicitly disabled'})
    checks.append(claim_guard(o,r))
    critical_fail=[c for c in checks if c.get('critical') and not c.get('passed')]
    warnings=[]
    cg=checks[-1]
    if cg.get('scope_all_removed_warning') and not cg.get('scope_loss_with_optimum_failure'):
        warnings.append('all recognized scope markers disappeared; verify relocation or semantic preservation')
    report={'status':'PASS' if not critical_fail else 'FAIL','critical_failures':[c['name'] for c in critical_fail],'warnings':warnings,'checks':checks}
    if a.as_json: print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print(report['status'])
        for c in checks: print(f"{c['name']}: {'PASS' if c.get('passed') else 'FAIL'}")
        for w in warnings: print('WARNING:',w)
    return 0 if not critical_fail else 1
if __name__=='__main__': raise SystemExit(main())
