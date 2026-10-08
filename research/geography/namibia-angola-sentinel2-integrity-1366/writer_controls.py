#!/usr/bin/env python3
"""Exercise the authenticated shared fresh-vintage writer on owned fixtures."""
import hashlib, json, os, pathlib, resource, shutil, signal, subprocess, sys
from datetime import datetime, timezone

BASE=pathlib.Path(__file__).absolute().parent
REPO=BASE.parents[2]
OLD='research/geography/namibia-angola-sentinel2-followup-20261007/'
COMMIT='c53f0aa473eb32c07a5cf4f57df3a86663a625ae'
PACKET='f513f7d6cb5fb088c1fca0238d915426a14ecfa8'

def blob(path):
    return subprocess.check_output(['git','show',f'{COMMIT}:{path}'],cwd=REPO)

def admit_absent(path):
    path=pathlib.Path(path)
    try: path.relative_to(BASE)
    except ValueError: raise ValueError('writer control path escaped owned directory')
    for ancestor in (BASE,*BASE.parents):
        if ancestor.is_symlink(): raise ValueError('symlink in owned path ancestry')
        if ancestor==REPO.parent: break
    parent=path.parent
    while parent!=BASE:
        if parent.is_symlink(): raise ValueError('symlink in writer control path ancestry')
        if parent.exists() and not parent.is_dir(): raise ValueError('non-directory writer control ancestor')
        parent=parent.parent
    if path.is_symlink() or path.exists(): raise FileExistsError('writer control destination already exists')

def exclusive_bytes(path,data):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
    with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())

def main():
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')
    vintage=BASE/'vintages'; controls=BASE/'controls'
    receipt=controls/('writer-probes-'+stamp+'.json'); path_probe=controls/('path-probe-'+stamp)
    path_target=path_probe/'target'; path_link=path_probe/'link'
    for path in (path_probe,path_target,path_link,vintage/('probe-occupied-'+stamp),vintage/('probe-occupied-'+stamp)/'sentinel.txt',vintage/('probe-symlink-'+stamp),vintage/('probe-late-write-'+stamp),receipt): admit_absent(path)
    path_probe.mkdir(exist_ok=False); path_target.mkdir(exist_ok=False); path_link.symlink_to(path_target,target_is_directory=True)
    try: admit_absent(path_link/'escaped.json'); raise RuntimeError('symlinked control output parent admitted')
    except ValueError: control_symlink_parent_rejected=True
    finally: path_link.unlink(); shutil.rmtree(path_probe)
    manifest=json.loads(subprocess.check_output(['git','show',f'{PACKET}:{OLD}evidence-quality.json'],cwd=REPO))
    helper_pin=next(x for x in manifest['baseline']['files'] if x['path']=='scripts/evidence/immutable.py')
    helper=blob('scripts/evidence/immutable.py')
    if hashlib.sha256(helper).hexdigest()!=helper_pin['sha256']:
        raise RuntimeError('pinned shared writer changed')
    ns={'__name__':'worldatlas_immutable_pinned'}; exec(compile(helper,'scripts/evidence/immutable.py','exec'),ns)
    baseline=ns['Baseline'](REPO,COMMIT,manifest['baseline']['files'])
    owned='research/geography/namibia-angola-sentinel2-integrity-1366/'
    if not vintage.is_dir() or not controls.is_dir(): raise ValueError('pre-existing control directories missing')
    results={'control_symlink_parent_rejected':control_symlink_parent_rejected}
    try:
        ns['NewVintage'](baseline,owned,'../escape-20261008',['result.json'])
        raise AssertionError('traversal admitted')
    except ValueError:
        results['traversal_rejected']=True
    occupied='probe-occupied-'+stamp; od=vintage/occupied; od.mkdir(exist_ok=False)
    sentinel=od/'sentinel.txt'; exclusive_bytes(sentinel,b'preserve this occupied target\n')
    try:
        ns['NewVintage'](baseline,owned,occupied,['result.json'])
        raise AssertionError('occupied target admitted')
    except FileExistsError:
        results['occupied_target_rejected']=sentinel.read_text(encoding='utf-8')=='preserve this occupied target\n'
    link='probe-symlink-'+stamp; ld=vintage/link; ld.symlink_to(BASE/'controls',target_is_directory=True)
    try:
        ns['NewVintage'](baseline,owned,link,['result.json'])
        raise AssertionError('symlink target admitted')
    except ValueError:
        results['symlink_target_rejected']=True
    finally:
        ld.unlink()
    late='probe-late-write-'+stamp
    writer=ns['NewVintage'](baseline,owned,late,['large-result.json'])
    old_limit=resource.getrlimit(resource.RLIMIT_FSIZE)
    signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024,old_limit[1]))
        try:
            writer.publish({'large-result.json':{'fixture':'genuine OS RLIMIT_FSIZE failure','payload':'x'*65536}})
            raise AssertionError('size limited write unexpectedly completed')
        except OSError as exc:
            results['late_os_write_failure']=repr(exc)
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE,old_limit)
    late_dir=writer.root
    result_path=late_dir/'large-result.json'
    results['partial_result_bytes_after_failure']=result_path.stat().st_size if result_path.exists() else 0
    results['completion_receipt_absent_after_failure']=not (late_dir/'publication.json').exists()
    if not (results['control_symlink_parent_rejected'] and results['traversal_rejected'] and results['occupied_target_rejected'] and results['symlink_target_rejected'] and results['late_os_write_failure'] and results['partial_result_bytes_after_failure']==1024 and results['completion_receipt_absent_after_failure']):
        raise RuntimeError('writer safety control failed')
    out=receipt
    raw=(json.dumps({'version':1,'fixture_scope':owned,'writer':'authenticated scripts/evidence/immutable.py NewVintage','results':results},sort_keys=True,indent=2)+'\n').encode()
    exclusive_bytes(out,raw)
    print(json.dumps(results,sort_keys=True))

if __name__=='__main__': main()
