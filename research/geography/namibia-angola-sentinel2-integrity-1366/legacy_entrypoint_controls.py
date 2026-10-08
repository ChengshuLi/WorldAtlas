#!/usr/bin/env python3
"""Run unchanged inherited offline entry points only in owned private fixtures."""
import ast, hashlib, io, json, os, pathlib, resource, shutil, signal, subprocess, sys, zipfile
from datetime import datetime, timezone

BASE=pathlib.Path(__file__).resolve().parent
REPO=BASE.parents[2]
PACKET='f513f7d6cb5fb088c1fca0238d915426a14ecfa8'
OLD='research/geography/namibia-angola-sentinel2-followup-20261007/'
GAP='research/geography/gap-source-namibia-angola-20261006/'

def blob(path): return subprocess.check_output(['git','show',f'{PACKET}:{path}'],cwd=REPO)
def write_once(path,raw):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f: f.write(raw);f.flush();os.fsync(f.fileno())
def run(script,*args,preexec_fn=None):
    return subprocess.run([sys.executable,str(script),*args],cwd=script.parent,capture_output=True,text=True,preexec_fn=preexec_fn)
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    manifest=json.loads(blob(OLD+'evidence-quality.json'))
    descriptors={x['path']:x for x in manifest['baseline']['files']}
    for source in manifest['sources']:
        for d in source.get('files',[]): descriptors[d['path']]=d
    for d in manifest['outputs']: descriptors[d['path']]=d
    def authenticated(path):
        raw=blob(path); d=descriptors.get(path)
        if d is None or len(raw)!=d['bytes'] or hashlib.sha256(raw).hexdigest()!=d['sha256']:
            raise ValueError('fixture source does not match inherited whole-file pin: '+path)
        return raw
    fixture=BASE/'legacy-fixtures'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    fixture.mkdir(parents=True,exist_ok=False)
    # Exact unchanged scene selector plus all of its retained complete discovery pages.
    select_root=fixture/'select'/OLD.rstrip('/')
    select_script=select_root/'select_scenes.py'; write_once(select_script,authenticated(OLD+'select_scenes.py'))
    pages=[f'inputs/earth-search-stac-{year}-{season}-page-{page:02}.json' for year in (2019,2020) for season in ('wet','dry') for page in (1,2)]
    for p in pages: write_once(select_root/p,authenticated(OLD+p))
    selected_expected=json.loads(authenticated(OLD+'inputs/selected-sentinel2-items.json'))
    selection_results={}
    normal=run(select_script); selection_results['normal_exit']=normal.returncode
    selected_path=select_root/'inputs'/'selected-sentinel2-items.json'
    selection_results['selected_output_matches_retained_bytes']=selected_path.read_bytes()==authenticated(OLD+'inputs/selected-sentinel2-items.json')
    sentinel=b'preserve-me\n'; sentinel_copy=select_root/'inputs'/'selection-sentinel-copy.bin'
    selected_path.write_bytes(sentinel); sentinel_copy.write_bytes(sentinel)
    overwrite=run(select_script); selection_results['occupied_output_overwritten']=overwrite.returncode==0 and selected_path.read_bytes()!=sentinel
    selection_results['sentinel_copy_preserved']=sentinel_copy.read_bytes()==sentinel
    selected_path.unlink(); symlink_target=select_root/'selection-symlink-target.json'; selected_path.symlink_to(pathlib.Path('..')/symlink_target.name)
    linked=run(select_script); selection_results['dangling_symlink_followed']=linked.returncode==0 and symlink_target.exists()
    selection_results['symlink_target_sha256']=sha(symlink_target) if symlink_target.exists() else None
    selected_path.unlink()

    # Complete private analysis fixture: all unchanged selected windows and original geometries.
    analysis_root=fixture/'analysis'/OLD.rstrip('/')
    analysis_script=analysis_root/'analyze_sentinel2_windows.py'; write_once(analysis_script,authenticated(OLD+'analyze_sentinel2_windows.py'))
    for p in ('inputs/selected-sentinel2-items.json','inputs/source-window-receipts.json'):
        write_once(analysis_root/p,authenticated(OLD+p))
    receipts=json.loads(authenticated(OLD+'inputs/source-window-receipts.json'))['records']
    for rec in receipts: write_once(analysis_root/rec['npz_path'],authenticated(OLD+rec['npz_path']))
    gap_root=fixture/'analysis'/GAP.rstrip('/')
    for p in ('inputs/original-components.geojson','inputs/source-contact-features.geojson','evidence-quality.json'):
        write_once(gap_root/p,subprocess.check_output(['git','show',f'{manifest["baseline"]["commit"]}:{GAP+p}'],cwd=REPO))
    analysis_results={}
    normal=run(analysis_script,'--output','runs/reproduced.json');analysis_results['normal_exit']=normal.returncode
    expected_hash=hashlib.sha256(authenticated(OLD+'runs/run-one.json')).hexdigest()
    actual_path=analysis_root/'runs'/'reproduced.json'
    analysis_results['complete_output_matches_retained_run_one']=actual_path.exists() and sha(actual_path)==expected_hash
    occupied=analysis_root/'runs'/'occupied-sentinel.json'; occupied.write_bytes(sentinel)
    overwrite=run(analysis_script,'--output','runs/occupied-sentinel.json');analysis_results['occupied_output_overwritten']=overwrite.returncode==0 and sha(occupied)!=hashlib.sha256(sentinel).hexdigest()
    analysis_results['outside_path_traversal_created']=False
    traversal=analysis_root.parent/'traversal-result.json'
    escaped=run(analysis_script,'--output','../traversal-result.json')
    analysis_results['outside_path_traversal_created']=escaped.returncode==0 and traversal.exists()
    analysis_results['traversal_result_sha256']=sha(traversal) if traversal.exists() else None
    link=analysis_root/'symlink-result.json'; symlink_output=analysis_root.parent/'symlink-target.json'; link.symlink_to(pathlib.Path('..')/symlink_output.name)
    symlink=run(analysis_script,'--output','symlink-result.json')
    analysis_results['dangling_symlink_followed']=symlink.returncode==0 and symlink_output.exists()
    analysis_results['symlink_target_sha256']=sha(symlink_output) if symlink_output.exists() else None
    link.unlink()
    late=analysis_root/'runs'/'late-os-failure.json'
    def file_limit():
        signal.signal(signal.SIGXFSZ,signal.SIG_IGN);resource.setrlimit(resource.RLIMIT_FSIZE,(1024,resource.getrlimit(resource.RLIMIT_FSIZE)[1]))
    failed=run(analysis_script,'--output','runs/late-os-failure.json',preexec_fn=file_limit)
    analysis_results['late_os_file_limit_exit']=failed.returncode
    analysis_results['partial_result_bytes_after_os_failure']=late.stat().st_size if late.exists() else 0
    analysis_results['completion_receipt_present']=(late.parent/'publication.json').exists()

    # Execute the exact deterministic NPZ writer function AST from the pinned extractor.
    extract_source=authenticated(OLD+'extract_sentinel2_windows.py'); tree=ast.parse(extract_source)
    fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='deterministic_npz')
    ns={'hashlib':hashlib,'io':io,'zipfile':zipfile,'pathlib':pathlib,'np':__import__('numpy')}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),OLD+'extract_sentinel2_windows.py','exec'),ns)
    extract_root=fixture/'extract'; extract_root.mkdir()
    arrays={'row':ns['np'].array([1],dtype=ns['np'].int32),'col':ns['np'].array([2],dtype=ns['np'].int32)}
    npz=extract_root/'occupied.npz';npz.write_bytes(sentinel);before=hashlib.sha256(sentinel).hexdigest()
    ns['deterministic_npz'](npz,arrays); extractor_results={'occupied_npz_overwritten':sha(npz)!=before}
    npz_link=extract_root/'dangling.npz';target=fixture/'extract'/'linked-target.npz';npz_link.symlink_to(target.name)
    ns['deterministic_npz'](npz_link,arrays);extractor_results['dangling_npz_symlink_followed']=target.exists();extractor_results['linked_target_sha256']=sha(target) if target.exists() else None
    npz_link.unlink()

    observation={'version':1,'execution':'unchanged pinned #1366 offline selector and complete analysis CLI copied into this owned fixture; extractor deterministic_npz function executed directly from its authenticated AST','source_commit':PACKET,'results':{'selection':selection_results,'analysis':analysis_results,'extractor_writer':extractor_results},'limits':['No remote STAC query or COG acquisition was made. Rasterio/GDAL are unavailable in the bundled runtime, so the full remote extractor pipeline and its HTTP readers were not run.','The shared NewVintage result writer is covered separately in writer-probes; these observations reproduce defects in the unchanged inherited entry points and do not claim those entry points are repaired.']}
    controls=BASE/'controls';controls.mkdir(exist_ok=True)
    output=controls/('legacy-entrypoints-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    write_once(output,(json.dumps(observation,sort_keys=True,indent=2)+'\n').encode())
    print(json.dumps({'receipt':str(output.relative_to(BASE)),'selection':selection_results,'analysis':analysis_results,'extractor_writer':extractor_results},sort_keys=True))

if __name__=='__main__':main()
