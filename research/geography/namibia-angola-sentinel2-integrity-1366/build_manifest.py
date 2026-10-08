#!/usr/bin/env python3
"""Assemble versioned evidence inventory from authenticated historical records."""
import hashlib,json,pathlib,subprocess

BASE=pathlib.Path(__file__).resolve().parent
REPO=BASE.parents[2]
C53='c53f0aa473eb32c07a5cf4f57df3a86663a625ae'
F513='f513f7d6cb5fb088c1fca0238d915426a14ecfa8'
MAIN='ffa32416fd946ac89da621d02b554ca27733e688'
OLD='research/geography/namibia-angola-sentinel2-followup-20261007/'
GAP='research/geography/gap-source-namibia-angola-20261006/'

def blob(commit,path): return subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=REPO,stderr=subprocess.DEVNULL)
def desc(path,raw): return {'path':path,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'hash_kind':'file-bytes'}

def main():
    old=json.loads(blob(F513,OLD+'evidence-quality.json'))
    issue=json.loads((BASE/'inputs/issue-contract-snapshot.json').read_bytes())
    start=issue['body'].rfind('<!-- worldatlas-work:v1\n'); end=issue['body'].find('-->',start)
    contract=json.loads(issue['body'][start+len('<!-- worldatlas-work:v1\n'):end])
    pins=contract['evidence_quality']['pins']
    versions={}
    for f in old['baseline']['files']:
        versions[(f['path'],C53)]=dict(f,commit=C53)
    for src in old['sources']:
        for f in src.get('files',[]): versions[(f['path'],F513)]=dict(f,commit=F513)
    for f in old['outputs']: versions[(f['path'],F513)]=dict(f,commit=F513)
    versions[(OLD+'evidence-quality.json',F513)]=desc(OLD+'evidence-quality.json',blob(F513,OLD+'evidence-quality.json'))|{'commit':F513}
    # Bind every pin exactly as declared by the issue, choosing only a retained
    # historical commit whose complete file bytes have the declared digest.
    pin_files={}; baseline_files=versions
    old_alias=old['baseline']['pin_files']
    for name,want in pins.items():
        path=name if name.startswith(('data/','coordination/','research/','scripts/')) else old_alias[name]
        matches=[]
        for commit in (C53,F513):
            try: raw=blob(commit,path)
            except subprocess.CalledProcessError: continue
            if hashlib.sha256(raw).hexdigest()==want:
                matches.append((commit,raw))
        if not matches: raise ValueError(f'issue pin vintage is missing: {name}')
        # Keep original alias pins on their recorded baseline when an identical
        # later commit contains the same bytes.
        commit,raw=next((m for m in matches if m[0]==C53),matches[0]); baseline_files[(path,commit)]=desc(path,raw)|{'commit':commit}
        pin_files[name]={'path':path,'commit':commit}
    for ident,path in old['baseline']['subject_files'].items():
        pin_files.setdefault('subject:'+ident,{'path':path,'commit':C53})
    subject_files={ident:{'path':path,'commit':C53} for ident,path in old['baseline']['subject_files'].items()}
    files=[baseline_files[k] for k in sorted(baseline_files)]
    old_manifest=json.loads(blob(C53,GAP+'evidence-quality.json'))
    old_sources=old['sources']
    for src in old_sources:
        src['files']=[]
        if src['id']=='copernicus-sentinel2-l2a-products':
            src['retention']='restoration-only'
            src['restoration']='Restore the exact retained product evidence from the #1366 commit f513f7d6cb5fb088c1fca0238d915426a14ecfa8 using the source and metadata paths inventoried in baseline.files; never substitute a newer COG or catalog response.'
            src['limit']='Original STAC pages, raw source-window NPZs, source metadata, object HEAD records and byte-range log remain available as hash-bound historical Git objects; no whole COG object or independent mirror terms are retained or claimed.'
    outputs=[]; change=[]
    for p in sorted(BASE.rglob('*')):
        if not p.is_file() or p==BASE/'evidence-quality.json' or '__pycache__' in p.parts: continue
        rel=str(p.relative_to(REPO)); d=desc(rel,p.read_bytes())
        outputs.append(d|{'role':'evidence-output'})
        change.append({'path':rel,'status':'added'})
    change.append({'path':'research/geography/namibia-angola-sentinel2-integrity-1366/evidence-quality.json','status':'added'})
    selected=json.loads(blob(F513,OLD+'inputs/selected-sentinel2-items.json'))
    result_paths=[f"research/geography/namibia-angola-sentinel2-integrity-1366/vintages/{v}/reconciliation.json" for v in ('reconciliation-20261008-213835465861','reconciliation-20261008-213841974785')]
    report=json.loads((BASE/'vintages/reconciliation-20261008-213841974785/reconciliation.json').read_bytes())
    metric_specs=[('component_count',21,'features',result_paths[1]),('source_contact_count',10,'source features',result_paths[1]),('scene_count',16,'scene items',result_paths[1]),('reconciled_observation_rows',496,'rows',result_paths[1]),('independently_checked_pixel_centers',1751344,'pixel centers',result_paths[1]),('issue_pins_verified',39,'whole-file SHA-256 pins',result_paths[1]),('membership_mismatches',0,'bit mismatches',result_paths[1]),('retained_measurement_mismatches',0,'row-field mismatches',result_paths[1])]
    metrics=[]; bindings=[]
    for mid,value,unit,path in metric_specs:
        raw=(BASE/path.split('namibia-angola-sentinel2-integrity-1366/',1)[-1]).read_bytes()
        m={'id':mid,'value':value,'unit':unit,'input_sha256':hashlib.sha256(raw).hexdigest(),'vintage':'current','evaluation_commit':MAIN}
        if path.startswith('research/geography/namibia-angola-sentinel2-integrity-1366/'):
            m['input_file']={'path':path,'commit':'candidate'}
        metrics.append(m)
        pointer={'component_count':'/component_count','source_contact_count':'/contact_count','scene_count':'/selected_scene_count','reconciled_observation_rows':'/reconciled_observation_rows','independently_checked_pixel_centers':'/independent_geometry_membership/pixel_centers','issue_pins_verified':'/issue_pin_count','membership_mismatches':'/independent_geometry_membership/component_bit_mismatches','retained_measurement_mismatches':'/independent_measurements_match_retained_report/mismatches'}[mid]
        bindings.append({'metric_id':mid,'path':path,'json_pointer':pointer})
    subject_ids=old['subject_ids']; subj_sha=old['subject_ids_sha256']
    pins_map=dict(pins)
    manifestsources=old_sources
    methods=[{'id':'retained-sentinel2-independent-reconciliation','kind':'integrity-reproduction','description':'Authenticate exact issue pins, historical whole-file sources, scene/window receipts, bounded NPZ members, array types and dimensions; reconcile every selected item against eight pinned discovery pages and all native band grids; independently recompute 31-mask × 16-scene membership from the unchanged WGS84 geometries and native affine pixel centers; recompute all original measurement fields and reconcile catalog/native sensing times. Actual unchanged selector/analysis entrypoints and the extractor NPZ writer are also exercised in owned fixtures to preserve engineering defect evidence.','software':'Python 3.12.14; NumPy 2.3.5; Shapely 2.1.2; pyproj 3.7.2; pinned scripts/evidence/immutable.py NewVintage writer','units':'Pixel-center membership counts and inherited spectral measurements; counts are nonadditive across dates and intersecting masks.'}]
    manifest={'version':1,'issue':1519,'lane':'geography','worker_id':'01a10948-7d38-75d0-bc01-4cc28ea41f49','subject_ids':subject_ids,'subject_ids_sha256':subj_sha,
      'baseline':{'version':2,'commit':MAIN,'files':files,'pins':pins_map,'pin_files':pin_files,'subject_files':subject_files},
      'sources':manifestsources,'outputs':outputs,'methods':methods,'metrics':metrics,
      'summaries':[{'metric_id':m['id'],'value':m['value'],'unit':m['unit'],'text':f"{m['id']} = {m['value']} {m['unit']}."} for m in metrics],
      'conclusions':[{'status':'supported','source_ids':['copernicus-sentinel2-l2a-products','element84-earth-search-sentinel-2-l2a'],'text':'All 496 inherited observations reproduce exactly against retained source-window bytes and all 1,751,344 sampled pixel-center component/contact memberships match the unchanged original geometries.'},{'status':'unresolved','source_ids':['copernicus-sentinel2-l2a-products','element84-earth-search-sentinel-2-l2a'],'text':'Four 2019-wet catalog and native granule sensing times differ by 63.992610–866.957175 seconds. Both fields are retained; the cause is unknown.'},{'status':'unresolved','source_ids':['element84-earth-search-sentinel-2-l2a'],'text':'No whole COG bytes or mirror service terms were verified. No independent ground-control, boundary authority, present/historic channel course, legal status or territorial assignment is established.'}],
      'stages':{'research':'partial','implementation':'proposed','geographic_approval':'unapproved'},
      'commands':['/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/reconcile.py','/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/input_controls.py','/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/writer_controls.py','/Users/chengshuli/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 research/geography/namibia-angola-sentinel2-integrity-1366/legacy_entrypoint_controls.py'],
      'validation':[{'method_id':methods[0]['id'],'kind':'complete-reproduction','outcome':'passed','evidence_path':result_paths[1]},{'method_id':methods[0]['id'],'kind':'negative-input-controls','outcome':'passed','evidence_path':report['negative_control_receipts']['input_controls_path']},{'method_id':methods[0]['id'],'kind':'writer-controls','outcome':'passed','evidence_path':report['negative_control_receipts']['writer_controls_path']},{'method_id':methods[0]['id'],'kind':'legacy-defect-reproduction','outcome':'observed','evidence_path':report['negative_control_receipts']['legacy_entrypoints_path']}],
      'change_receipts':change,'metric_bindings':bindings}
    target=BASE/'evidence-quality.json'; target.write_text(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'created {target} with {len(files)} historical bindings, {len(outputs)} candidate outputs and {len(pins)} issue pins')

if __name__=='__main__': main()
