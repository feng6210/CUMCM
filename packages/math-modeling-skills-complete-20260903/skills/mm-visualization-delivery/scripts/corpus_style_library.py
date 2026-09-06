"""Full local style inventory and retrieval. Never executes or redistributes source assets.

Indexing a reference is not certifying its renderer, visual quality or scientific claims.
"""
import argparse
import collections
import hashlib
import html
import json
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = SKILL / 'assets/full-corpus/catalog.json'
IMAGE_EXT = {'.jpg', '.jpeg', '.png'}
ROLE = {'.m':'source_code', '.py':'source_code', '.txt':'technique_text', '.pdf':'tutorial_document',
        '.docx':'export_document', '.mat':'demo_data_or_palette', '.xlsx':'demo_data', '.fig':'native_reference'}
FAMILY_ROUTES = {
    '三维散点图': ('corpus','scatter_3d'), '三维曲面拟合图': ('reference','warm-surface-projection'),
    '三维面积图': ('corpus','area_3d'), '二维散点图': ('corpus','scatter_2d'),
    '单组箱式图': ('legacy','paired-distribution'), '双Y轴组合图': ('corpus','dual_axis'),
    '堆叠柱状图': ('corpus','stacked_bar'), '多组箱式图': ('legacy','paired-distribution'),
    '实用柱状图': ('corpus','bar'), '对数坐标图': ('corpus','log_xy'),
    '小窗图：折线图+柱状图': ('reference','teal-coral-inset'), '普通折线图': ('corpus','line'),
    '普通热力图': ('reference','rose-heatmap'), '曲面映射图': ('reference','warm-surface-projection'),
    '误差折线图': ('corpus','line_interval'), '进阶柱状图': ('corpus','grouped_bar'),
    '进阶热力图': ('reference','rose-heatmap'), '面积填充图': ('legacy','area-comparison'),
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write_new(path, obj):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(obj, ensure_ascii=False, indent=2) if not isinstance(obj, str) else obj)
def stable_id(prefix, relative):
    return prefix + '-' + hashlib.sha256(relative.encode('utf-8')).hexdigest()[:16]

def scan(root):
    root = Path(root).resolve()
    if not root.is_dir(): raise ValueError('source directory is missing')
    files = []
    for f in sorted(root.rglob('*')):
        if not f.is_file(): continue
        # Do not follow a symlink to material outside the user-selected corpus.
        if not f.resolve().is_relative_to(root): raise ValueError('source escapes corpus root')
        relative = f.relative_to(root).as_posix()
        files.append({'file_id': stable_id('file',relative), 'source_relative':relative,
            'sha256':sha(f), 'bytes':f.stat().st_size, 'extension':f.suffix.lower(),
            'role':'visual_reference' if f.suffix.lower() in IMAGE_EXT else ROLE.get(f.suffix.lower(),'other'),
            'family_directory':f.parent.name, 'source_execution':'NOT_EXECUTED_BY_INDEXER'})
    return {'schema_version':1, 'source_root_hint':str(root), 'files':files,
            'counts':dict(collections.Counter(f['extension'] for f in files)), 'file_count':len(files)}

def verify_inventory(inventory, root):
    actual = scan(root)
    old = {f['source_relative']:f['sha256'] for f in inventory['files']}
    now = {f['source_relative']:f['sha256'] for f in actual['files']}
    return {'passed':old == now, 'added':sorted(now.keys()-old.keys()),
        'missing':sorted(old.keys()-now.keys()), 'changed':sorted(k for k in now.keys() & old.keys() if now[k]!=old[k])}

def index_adapters(output):
    cards=[]
    for spec in sorted((SKILL/'assets/corpus-adapters').glob('*/spec.json')):
        s=read(spec); report=spec.parent/'preview'/(s['figure_id']+'.manifest.json')
        m=read(report); png=report.parent/(s['figure_id']+'.png')
        source=(spec.parent/s['source_csv']).resolve()
        if sha(spec)!=m['spec']['sha256'] or sha(source)!=m['source']['sha256']:
            raise ValueError('stale adapter spec/data: '+s['family'])
        for item in m['outputs']:
            if sha(report.parent/item['path'])!=item['sha256']:raise ValueError('stale adapter output')
        cards.append({'card_id':'adapter-'+s['family'], 'family_id':s['family'],
            'preview':png.relative_to(output.parent).as_posix(), 'preview_sha256':sha(png),
            'spec':spec.relative_to(output.parent).as_posix(), 'spec_sha256':sha(spec),
            'manifest':report.relative_to(output.parent).as_posix(), 'manifest_sha256':sha(report),
            'runtime_status':m['status'], 'visual_review_status':m['visual_review'],
            'data_status':m['data_status'], 'source_use':'ORIGINAL_SYNTHETIC_DEMO_NOT_EXPERIMENT_EVIDENCE'})
    if not cards:raise ValueError('no generated adapter previews to index')
    write_new(output,{'schema_version':1,'runtime_source_dependency':False,'cards':cards})
    return {'adapter_cards':len(cards)}

def route(group, variant=None):
    kind, family = FAMILY_ROUTES.get(group, ('custom','unassigned'))
    if group == '对数坐标图' and variant:
        components=variant.get('components',[])
        if 'multi_panel' in components:
            return {'status':'CUSTOM_ADAPTATION_REQUIRED', 'family_id':'log_comparison_panels',
                'component_adapters':[{'family_id':{'log_log':'log_xy'}.get(c,c), 'renderer':'scripts/render_corpus_chart.py'}
                    for c in components if c in ('line','log_x','log_y','log_log')],
                'scope':'Separate linear/log axis panels with identical source data; do not force both axes logarithmic.'}
        family = 'line' if 'linear_scale' in components else 'log_xy' if 'log_log' in components else 'log_x' if 'log_x' in components else 'log_y'
    if kind == 'corpus':
        spec = SKILL / 'assets/corpus-adapters' / family / 'spec.json'
        preview = SKILL / 'assets/corpus-adapters' / family / 'preview' / ('demo-'+family+'.png')
        renderer = 'scripts/render_corpus_chart.py'
    elif kind in ('reference','legacy'):
        original = read(SKILL/'assets/style-library/catalog.json')
        card = next(c for c in original['cards'] if c['card_id']==family)
        spec = SKILL/'assets/style-library'/card['spec']
        preview = SKILL/'assets/style-library'/card['preview']
        renderer = card['renderer']
    else: return {'status':'CUSTOM_ADAPTATION_REQUIRED','family_id':family}
    return {'status':'BASE_ADAPTER_AVAILABLE' if spec.is_file() else 'ADAPTER_NOT_BUILT',
        'family_id':family, 'kind':kind, 'renderer':renderer,
        'spec':spec.relative_to(SKILL).as_posix(),
        'fallback_preview':preview.relative_to(SKILL).as_posix(),
        'scope':'Base family only; exact multi-panel, markers, palette and view require per-variant adaptation and review.'}

def assemble(root, visual_path, audit_path, output):
    inventory = scan(root)
    visual = read(visual_path)
    if isinstance(visual,dict): visual = visual.get('variants', visual.get('items', []))
    indexed = {v['source_relative'].replace('\\','/'):v for v in visual}
    expected = {f['source_relative'] for f in inventory['files'] if f['role']=='visual_reference'}
    if set(indexed)!=expected or len(visual)!=len(expected):
        raise ValueError('visual variants must cover every image exactly once; no duplicate, missing or extra path')
    cards = []
    for f in inventory['files']:
        if f['role'] != 'visual_reference': continue
        v = indexed[f['source_relative']]
        if v['sha256'] != f['sha256']: raise ValueError('stale visual review: '+f['source_relative'])
        cards.append({**v, 'card_id':stable_id('variant',f['source_relative']),
            'family_directory':f['family_directory'], 'preview_sha256':f['sha256'],
            'preview_location':'OPTIONAL_LOCAL_SOURCE_ONLY', 'source_use':'LOCAL_REFERENCE_NOT_REDISTRIBUTED',
            'variant_runtime_status':'REFERENCE_ONLY_NOT_EXACTLY_REPRODUCED',
            'adapter':route(f['family_directory'],v)})
    audit = read(audit_path)
    audited = {f['relative_path'].replace('\\','/'): f['sha256'] for f in audit['files']}
    expected_audit = {f['source_relative']:f['sha256'] for f in inventory['files'] if f['extension'] in ('.m','.py','.txt')}
    if audited != expected_audit or len(audit['files']) != len(expected_audit):
        raise ValueError('code/text audit is stale, incomplete or duplicated; reread changed source before assembling')
    catalog = {'schema_version':1,'scope':'All local image variants, all source files and tutorial slots; not all runtime-certified',
        'source_root_hint':str(Path(root).resolve()), 'runtime_source_dependency':False,
        'inventory':inventory, 'cards':cards, 'code_audit':audit,
        'review_provenance':{'visual_review_sha256':sha(visual_path),'code_audit_sha256':sha(audit_path),
                            'visual_origin':'same-family-fresh','raw_sources_redistributed':False},
        'source_documents':{'pdf_pages_visually_read':8,'pdf_named_slots':50,
            'pdf_reading_note_zh':'8页逐页查看；表格内的赛题分类只是启发。第6页3D等高线示意实际为曲面，第8页马赛克示意为等宽堆叠条，树状图示意为矩形面积布局，不能据此替代正确图型语义。',
            'docx_reading_note_zh':'完整读取高清导出说明：GUI导出或print指定分辨率；300/600/900/1200 dpi仅光栅导出选项，矢量PDF不靠提高dpi改善几何。'},
        'counts':{'files':len(inventory['files']), 'image_variants':len(cards),
                  'image_directories':len({c['family_directory'] for c in cards}),
                  'source_code_files':sum(f['role']=='source_code' for f in inventory['files'])}}
    write_new(output,catalog)
    return catalog['counts']

def search(catalog, query):
    terms=query.casefold().split()
    pool = [dict(c, record_type='image_variant') for c in catalog['cards']]
    pool += [dict(c, record_type='tutorial_slot') for c in catalog['code_audit']['tutorial_slots']]
    pool += [dict(c, record_type='source_or_technique') for c in catalog['code_audit']['files']]
    return [c for c in pool if all(t in json.dumps(c,ensure_ascii=False).casefold() for t in terms)]

def gallery(catalog_path, output, root=None):
    catalog=read(catalog_path); root=Path(root or catalog['source_root_hint']).resolve()
    rows=[]
    for c in catalog['cards']:
        source=root/c['source_relative']; adapter=c['adapter']
        source_ok = source.is_file() and sha(source)==c['sha256']
        palette=c.get('palette_approx',[])
        notes=c.get('design_notes_zh',c.get('design_notes',''))
        details=html.escape(json.dumps({'观察':notes,'布局':c.get('layout'), '风险':c.get('risks'), '基础适配器':adapter},ensure_ascii=False,indent=2))
        preview=(SKILL/adapter.get('fallback_preview','')).resolve()
        fallback=f'<a href="{html.escape(preview.as_uri())}">打开原创基础预览（不是原图的逐项复刻）</a>' if preview.is_file() else '<span>基础适配待实现</span>'
        swatches=''.join(f'<span class="swatch" style="background:{html.escape(str(color),quote=True)}"></span>' for color in palette if isinstance(color,str) and len(color)==7 and color.startswith('#'))
        row=f'<article data-search="{html.escape(json.dumps(c,ensure_ascii=False).casefold(),quote=True)}"><h2>{html.escape(c["family_directory"])} · {html.escape(source.name)}</h2><a href="{html.escape(source.as_uri())}"><img loading="lazy" src="{html.escape(source.as_uri())}" alt="本地原始参考图；不可访问时请重建gallery并指定source-root"></a><p>{swatches}</p><code>{c["card_id"]}</code><p>原样图参考已索引；精确变体尚未逐张适配验证</p>{fallback}<details><summary>配色、构图、风险与入口</summary><pre>{details}</pre></details></article>'
        rows.append(row)
        if not source_ok:
            # Do not show changed pixels under an old hash-bound observation.
            start=row.index('<a href='); end=row.index('</a>',start)+4
            rows[-1]=row[:start]+'<p>原图缺失或SHA-256变化：不显示旧审查对应的图像；请重新扫描和查看。</p>'+row[end:]
    for slot in catalog['code_audit']['tutorial_slots']:
        rows.append('<article data-search="'+html.escape(json.dumps(slot,ensure_ascii=False).casefold(),quote=True)+'"><h2>教程 '+html.escape(slot['slot_id'])+' · '+html.escape(slot['name_zh'])+'</h2><p>全量保留的命名图型；源实现与命名不符处见下方。原始演示代码不自动执行。</p><pre>'+html.escape(json.dumps(slot,ensure_ascii=False,indent=2))+'</pre></article>')
    adapter_catalog=SKILL/'assets/corpus-adapters/catalog.json'
    if adapter_catalog.is_file():
        for card in read(adapter_catalog)['cards']:
            preview=adapter_catalog.parent/card['preview']
            if not preview.is_file() or sha(preview)!=card['preview_sha256']:
                raise ValueError('stale original adapter preview')
            rows.append('<article data-search="'+html.escape(json.dumps(card,ensure_ascii=False).casefold(),quote=True)+'"><h2>原创基础模板 · '+html.escape(card['family_id'])+'</h2><a href="'+html.escape(preview.as_uri())+'"><img loading="lazy" src="'+html.escape(preview.as_uri())+'" alt="原创合成数据演示，非论文实验"></a><p>运行验证：'+html.escape(card['runtime_status'])+'。DEMO_ONLY，不是原参考图的逐张复刻。</p><a href="'+html.escape((adapter_catalog.parent/card['spec']).as_uri())+'">打开可改数据字段的spec</a></article>')
    audit_text=html.escape(json.dumps(catalog['code_audit'],ensure_ascii=False,indent=2))
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>全量绘图样式库</title><style>body{font:16px/1.6 "Microsoft YaHei",sans-serif;background:#f5f3ed;color:#253648;margin:0}header,main{max-width:1440px;margin:auto;padding:26px}header{background:#e1efec;border-bottom:5px solid #e77b66}h1{font-size:32px;margin:0}input{padding:14px;width:min(80%,700px);font:inherit;border:1px solid #819f9e;border-radius:9px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:22px}article{background:white;border-radius:12px;padding:20px;box-shadow:0 4px 18px #25364812}h2{font-size:18px}img{width:100%;height:280px;object-fit:contain}pre{white-space:pre-wrap;font-size:13px;overflow-wrap:anywhere}.swatch{display:inline-block;width:24px;height:24px;border-radius:50%;margin-right:5px}code{font-size:12px}a{color:#087e82}details{margin:15px 0}</style><header><h1>全量绘图样式库 · 不止六张代表卡</h1><p>145文件 / 68张本地参考变体 / 37份代码 / 教程50命名槽位（具体计数以当前索引为准）。原图仅本机读取，没有复制进Skill。基础模板可离线运行；原图移动后用 --source-root 重建此页面。</p><p>“已查看参考” ≠ “逐张复刻成功” ≠ “论文证据通过”。同类配色、构图和视角分别保留。</p><input id="q" placeholder="搜索：三维、粉、箱线、热图、误差、面板……"><span id="count"></span></header><main><div class="grid">'''+''.join(rows)+'''</div><details><summary>全部代码与教程图型审计（包括缺失和名称不符）</summary><pre>'''+audit_text+'''</pre></details></main><script>const q=document.querySelector('#q');function filter(){const terms=q.value.toLowerCase().split(/ +/).filter(Boolean);let n=0;for(const card of document.querySelectorAll('article')){card.hidden=!terms.every(t=>card.dataset.search.includes(t));if(!card.hidden)n++;}document.querySelector('#count').textContent=' '+n+' / '+document.querySelectorAll('article').length+' 个图片/教程条目';}q.addEventListener('input',filter);filter();</script></html>'''
    page=page.replace('145文件 / 68张本地参考变体 / 37份代码 / 教程50命名槽位（具体计数以当前索引为准）',
        f"{catalog['counts']['files']}文件 / {len(catalog['cards'])}张本地参考变体 / {catalog['counts']['source_code_files']}份代码 / 教程{len(catalog['code_audit']['tutorial_slots'])}命名槽位")
    write_new(output,page)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('scan');s.add_argument('--source-root',type=Path,required=True);s.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('assemble');a.add_argument('--source-root',type=Path,required=True);a.add_argument('--visual-review',type=Path,required=True);a.add_argument('--code-audit',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('index-adapters');a.add_argument('--output',type=Path,default=SKILL/'assets/corpus-adapters/catalog.json')
    for name in ('search','verify','gallery','select'):
        c=sub.add_parser(name);c.add_argument('--catalog',type=Path,default=DEFAULT_CATALOG)
        if name=='search':c.add_argument('--query',default='')
        if name in ('verify','gallery','select'):c.add_argument('--source-root',type=Path)
        if name=='gallery':c.add_argument('--output',type=Path,required=True)
        if name=='select':c.add_argument('--id',required=True)
    a=p.parse_args()
    try:
        if a.command=='scan':r=scan(a.source_root);write_new(a.output,r);r=r['counts']
        elif a.command=='assemble':r=assemble(a.source_root,a.visual_review,a.code_audit,a.output)
        elif a.command=='index-adapters':r=index_adapters(a.output.resolve())
        else:
            c=read(a.catalog)
            if a.command=='search':r=search(c,a.query)
            elif a.command=='verify':
                r=verify_inventory(c['inventory'],a.source_root or c['source_root_hint'])
                print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['passed'] else 2
            elif a.command=='gallery':gallery(a.catalog,a.output,a.source_root);r={'gallery':str(a.output)}
            else:
                matches=[v for v in c['cards'] if v['card_id']==a.id]
                if len(matches)!=1:raise ValueError('unknown or duplicate card_id')
                v=matches[0];source=Path(a.source_root or c['source_root_hint'])/v['source_relative']
                available=source.is_file() and sha(source)==v['sha256']
                r={'variant':v,'source_available_and_hash_matches':available,
                   'style_reference':{'card_id':v['card_id'],'catalog':{'file':str(a.catalog.resolve()),'sha256':sha(a.catalog)},
                                      'preview':{'file':str(source.resolve()),'sha256':v['sha256']}} if available else None,
                   'next_action_zh':'先确认复合面板全部成分；基础模板不是完整复刻。按本题字段、配色、marker、视角配置后独立审图。' if available else '原图不可用；读已蒸馏样式参数与基础预览。须改绑定所选基础卡，不能伪称看过该原图。'}
        print(json.dumps(r,ensure_ascii=False,indent=2));return 0
    except (OSError,ValueError,KeyError,TypeError) as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':raise SystemExit(main())
