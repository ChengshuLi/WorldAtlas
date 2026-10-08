#!/usr/bin/env python3
"""Exercise the authenticated shared fresh-vintage writer on owned fixtures."""
import hashlib, json, os, pathlib, resource, signal, subprocess, sys
from datetime import datetime, timezone

BASE=pathlib.Path(__file__).resolve().parent
REPO=BASE.parents[2]
OLD='research/geography/namibia-angola-sentinel2-followup-20261007/'
COMMIT='c53f0aa473eb32c07a5cf4f57df3a86663a625ae'
PACKET='f513f7d6cb5fb088c1fca0238d915426a14ecfa8'

def blob(path):
    return subprocess.check_output(['git','show',f'{COMMIT}:{path}'],cwd=REPO)

def main():
    manifest=json.loads(subprocess.check_output(['git','show',f'{PACKET}:{OLD}evidence-quality.json'],cwd=REPO))
    helper_pin=next(x for x in manifest['baseline']['files'] if x['path']=='scripts/evidence/immutable.py')
    helper=blob('scripts/evidence/immutable.py')
    if hashlib.sha256(helper).hexdigest()!=helper_pin['sha256']:
        raise RuntimeError('pinned shared writer changed')
    ns={'__name__':'worldatlas_immutable_pinned'}; exec(compile(helper,'scripts/evidence/immutable.py','exec'),ns)
    baseline=ns['Baseline'](REPO,COMMIT,manifest['baseline']['files'])
    owned='research/geography/namibia-angola-sentinel2-integrity-1366/'
    vintage=BASE/'vintages'; vintage.mkdir(exist_ok=True)
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S%f')
    results={}
    try:
        ns['NewVintage'](baseline,owned,'../escape-20261008',['result.json'])
        raise AssertionError('traversal admitted')
    except ValueError:
        results['traversal_rejected']=True
    occupied='probe-occupied-'+stamp; od=vintage/occupied; od.mkdir(exist_ok=False)
    sentinel=od/'sentinel.txt'; sentinel.write_text('preserve this occupied target\n',encoding='utf-8')
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
    if not (results['traversal_rejected'] and results['occupied_target_rejected'] and results['symlink_target_rejected'] and results['late_os_write_failure'] and results['partial_result_bytes_after_failure']==1024 and results['completion_receipt_absent_after_failure']):
        raise RuntimeError('writer safety control failed')
    out=BASE/'controls'/('writer-probes-'+stamp+'.json'); out.parent.mkdir(exist_ok=True)
    raw=(json.dumps({'version':1,'fixture_scope':owned,'writer':'authenticated scripts/evidence/immutable.py NewVintage','results':results},sort_keys=True,indent=2)+'\n').encode()
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f: f.write(raw); f.flush(); os.fsync(f.fileno())
    print(json.dumps(results,sort_keys=True))

if __name__=='__main__': main()
