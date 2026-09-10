#!/usr/bin/env python3
"""Read-only style audit for Chinese CUMCM prose.

The scanner surfaces observable template/audit/responder patterns. It does not
classify provenance and does not output an AI probability.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
TEXT_EXTENSIONS={'.tex','.md','.markdown','.txt','.rst'}
MATH_ENVS=('equation','equation*','align','align*','aligned','gather','gather*','multline','multline*','cases','matrix','pmatrix','bmatrix','vmatrix')
VERBATIM_ENVS=('verbatim','lstlisting','minted')
RULES={
'responder_frame':('medium',re.compile(r'(?:这里(?:需要|要)(?:说明|强调|指出)|需要(?:特别)?(?:说明|强调|指出)的是|值得注意的是|不容忽视的是|容易(?:产生)?误解的是|接下来(?:我们)?将|下面(?:我们)?(?:将|来))')),
'defensive_negation':('medium',re.compile(r'(?:本文不声称|不据此(?:认为|声称)|并不(?:代表|意味着)|不等于|不能(?:简单)?(?:认为|说明|推出|据此)|不是.{0,40}而是|并非.{0,40}而是)')),
'audit_jargon':('high',re.compile(r'(?:已验证候选|预算内候选|严格复算|实现一致性|覆盖缺口|claim[ _-]?scope|workflow[ _-]?state|backend[ _-]?report|evidence[ _-]?commit|fail[ _-]?closed|seed[ _-]?virginity|PASS_WITH|NOT_ALLOWED_BY_USER|registered_before_run|\bmanifest\b|\bhash\b|\bgate\b)',re.I)),
'stock_opening':('low',re.compile(r'(?:随着.{0,30}(?:发展|推进|深入)|近年来.{0,25}(?:受到|引起).{0,10}关注|在(?:当今|当前|新时代|新形势|新背景).{0,30}(?:下|背景下))')),
'mechanical_connector':('low',re.compile(r'(?:首先|其次|再次|最后|此外|进一步(?:地)?|与此同时|一方面|另一方面|换言之|也就是说|综上所述|总的来说|由此可见)')),
'empty_evaluation':('medium',re.compile(r'(?:具有(?:较强|很强|良好|较好)的(?:鲁棒性|可靠性|科学性|合理性|有效性)|(?:显著|有效)(?:提升|提高|改善)|充分证明|有力证明|全面(?:提升|优化)|具有重要(?:理论|实践|现实)?意义)')),
'service_closer':('high',re.compile(r'(?:希望(?:以上|上述)?内容.{0,12}(?:有所帮助|帮助到)|如果(?:你)?需要|如有(?:任何)?问题|欢迎(?:继续)?(?:提问|交流))')),
'algorithm_chaining':('medium',re.compile(r'(?:首先|先).{0,60}(?:然后|再).{0,60}(?:随后|接着).{0,60}(?:最后|最终)')),
'repetitive_hedging':('low',re.compile(r'(?:可能|通常|往往|一般而言|一般来说|相对而言|一定程度上|某种程度上)')),
}
COMMENT_RE=re.compile(r'(?<!\\)%.*$'); INLINE_CODE_RE=re.compile(r'`[^`]*`'); URL_RE=re.compile(r'https?://\S+')
def mask_latex_nonprose(text):
    out=text
    for env in VERBATIM_ENVS+MATH_ENVS:
        pat=re.compile(rf'\\begin\{{{re.escape(env)}\}}.*?\\end\{{{re.escape(env)}\}}',re.S)
        out=pat.sub(lambda m:'\n'*m.group(0).count('\n'),out)
    out=re.sub(r'\\\[.*?\\\]',lambda m:'\n'*m.group(0).count('\n'),out,flags=re.S)
    out=re.sub(r'\\\(.*?\\\)',' ',out,flags=re.S)
    out=re.sub(r'(?<!\\)\$\$.*?(?<!\\)\$\$',lambda m:'\n'*m.group(0).count('\n'),out,flags=re.S)
    out=re.sub(r'(?<!\\)\$(?:\\.|[^$])*?(?<!\\)\$',' ',out)
    out=re.sub(r'\\(?:cite|citep|citet|ref|eqref|autoref|label|url|href)\*?(?:\[[^\]]*\])?\{[^{}]*\}',' ',out)
    return out
def prose_lines(path):
    raw=path.read_text(encoding='utf-8-sig',errors='replace')
    if path.suffix.lower()=='.tex': raw=mask_latex_nonprose(raw)
    lines=[]; in_fence=False; in_front=False
    for no,line in enumerate(raw.splitlines(),1):
        s=line.strip()
        if path.suffix.lower() in {'.md','.markdown'}:
            if no==1 and s=='---': in_front=True; continue
            if in_front:
                if s=='---': in_front=False
                continue
            if s.startswith(('```','~~~')): in_fence=not in_fence; continue
            if in_fence: continue
        if path.suffix.lower()=='.tex': line=COMMENT_RE.sub('',line)
        line=URL_RE.sub('',INLINE_CODE_RE.sub('',line))
        if line.strip(): lines.append((no,line))
    return lines
def section_key(line,current):
    m=re.search(r'\\(?:section|subsection|subsubsection)\*?\{([^{}]+)\}',line)
    return m.group(1).strip() if m else current
def audit_file(path,strict=False):
    lines=prose_lines(path); findings=[]; counts=Counter(); per=defaultdict(Counter); sec='(frontmatter)'
    ct=2 if strict else 3; ht=2 if strict else 3
    for no,line in lines:
        sec=section_key(line,sec)
        for rid,(sev,pat) in RULES.items():
            ms=[m.group(0) for m in pat.finditer(line)]
            if not ms: continue
            if rid=='mechanical_connector' and len(ms)<ct: continue
            if rid=='repetitive_hedging' and len(ms)<ht: continue
            counts[rid]+=len(ms); per[sec][rid]+=len(ms)
            findings.append({'file':str(path),'line':no,'section':sec,'rule':rid,'severity':sev,'matches':ms,'text':line.strip()})
    lims={'responder_frame':3 if strict else 4,'defensive_negation':3 if strict else 4,'audit_jargon':2 if strict else 3}
    dens=[]
    for sec,c in per.items():
        for rid,lim in lims.items():
            if c[rid]>=lim:
                dens.append({'file':str(path),'section':sec,'rule':rid+'_density','severity':'high' if rid=='audit_jargon' else 'medium','count':c[rid],'message':f'{sec} 中 {rid} 局部密度偏高（{c[rid]} 次）。'})
    return {'file':str(path),'provenance_claim':'none','ai_probability':None,'findings':findings,'density_findings':dens,'counts':dict(counts),'status':'REVIEW' if findings or dens else 'NO_CHANGE_RECOMMENDED'}
def iter_paths(inputs):
    out=[]
    for item in inputs:
        p=Path(item)
        if p.is_file(): out.append(p)
        elif p.is_dir(): out.extend(q for q in p.rglob('*') if q.is_file() and q.suffix.lower() in TEXT_EXTENSIONS)
        else: raise FileNotFoundError(item)
    return sorted(set(out))
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('paths',nargs='+'); ap.add_argument('--json',action='store_true',dest='as_json'); ap.add_argument('--strict',action='store_true'); a=ap.parse_args()
    try: paths=iter_paths(a.paths)
    except FileNotFoundError as e: print(f'not found: {e}',file=sys.stderr); return 2
    reps=[audit_file(p,a.strict) for p in paths]
    if a.as_json: print(json.dumps({'reports':reps},ensure_ascii=False,indent=2))
    else:
        for r in reps:
            print(f"{r['file']}: {r['status']}")
            for f in r['density_findings']: print(f"  [{f['severity']}] {f['section']}: {f['message']}")
            for f in r['findings']: print(f"  L{f['line']} [{f['severity']}] {f['rule']}: {', '.join(f['matches'])}")
    return 0
if __name__=='__main__': raise SystemExit(main())
