"""Small genuine Git code-custody operation; exits before source repair calculation."""
import json, pathlib, subprocess, sys, hashlib, os
import producer as p
GIT = {'path': '/Library/Developer/CommandLineTools/usr/bin/git', 'bytes': 7058848,
       'mode': '100755', 'sha256': '4c5ca299b5311572b4f948d11efd7c66dcadf30950fbf260688ee32f4a63f6a4'}

def capture(commit, output):
    destination = p.safe_output(output)
    if len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
        raise ValueError('Exact immutable source head required')
    p.decoded(p.deterministic_gzip(b'[]\n'), {'decoded_bytes': 3, 'decoded_sha256': p.digest(b'[]\n')})
    p.canonical_prepared_land(p.Polygon([(0,0), (1,0), (0,1), (0,0)]))
    runtime = json.loads((p.HERE / 'runtime.json').read_bytes())
    p.require_callables(runtime)
    paths = {p.HERE / name for name in ('producer.py','kernel.py','input-plan.json','runtime.json','capture-code.py')}
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if name and pathlib.Path(name).resolve().is_relative_to(p.ROOT):
            paths.add(pathlib.Path(name).resolve())
    stat_rows = [{'actual_path': str(path), 'bytes': p.ordinary(path).stat().st_size} for path in sorted(paths)]
    total = 2 * sum(row['bytes'] for row in stat_rows) + sum(row['bytes'] for row in runtime['runtime_files']) + GIT['bytes'] + 65536
    if total > p.PHASE_CAP or len(stat_rows) + len(runtime['runtime_files']) + 1 > 512 or any(row['bytes'] > p.FILE_CAP for row in stat_rows):
        raise ValueError('Whole code/tool/runtime/source-proof metadata phase exceeds cap')
    if p.loaded_runtime_paths() - {row['path'] for row in runtime['runtime_files']}:
        raise ValueError('Source issuer runtime exceeds immutable roster')
    p.authenticate_installed_runtime(runtime)
    p.read(GIT['path'], GIT)
    def git(*args):
        return subprocess.check_output([GIT['path'],'-C',str(p.ROOT),*args],text=True)
    if git('rev-parse','HEAD').strip() != commit:
        raise ValueError('Wrong actual source head')
    rows = []
    for path in sorted(paths):
        relative = str(path.relative_to(p.ROOT))
        fields = git('ls-tree','-l',commit,'--',relative).split(None,4)
        if len(fields) != 5 or fields[0] not in ('100644','100755') or fields[1] != 'blob':
            raise ValueError('Original ordinary Git source missing')
        pin = {'path': relative,'mode':fields[0],'git_blob_oid':fields[2],'bytes':int(fields[3])}
        raw = p.read(path,{**pin,'sha256':hashlib.sha256(git_blob(commit, fields[2])).hexdigest()})
        if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != fields[2]:
            raise ValueError('Source body differs from immutable Git OID')
        rows.append({**pin,'sha256':p.digest(raw)})
    p.read(GIT['path'],GIT)
    if git('rev-parse','HEAD').strip() != commit:
        raise ValueError('Source head drifted')
    result={'kind':'immutable-git-code-source-v1','head':commit,'root':str(p.ROOT),'files':rows,
            'issuer_tool':GIT,'installed_runtime_bytes':sum(row['bytes'] for row in runtime['runtime_files']),
            'complete_phase_bytes':total,'original_git_and_filesystem_code_bytes':2 * sum(row['bytes'] for row in stat_rows),'output_reserve_bytes':65536,'source_repair_calculated':False}
    raw=p.canonical_json(result)
    if len(raw)>65536:raise ValueError('Actual metadata exceeds reserve')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as stream:stream.write(raw)
    print(json.dumps({'path':str(destination),'bytes':len(raw),'sha256':p.digest(raw),'head':commit,'complete_phase_bytes':total}))

def git_blob(commit, oid):
    size=int(subprocess.check_output([GIT['path'],'-C',str(p.ROOT),'cat-file','-s',oid],text=True))
    if size>p.FILE_CAP:raise ValueError('Bounded original Git blob required')
    raw=subprocess.check_output([GIT['path'],'-C',str(p.ROOT),'cat-file','blob',oid])
    if len(raw)!=size:raise ValueError('Original blob changed')
    return raw

if __name__=='__main__':
    if len(sys.argv)!=3:raise SystemExit('Exact head and fresh owned-cache output required')
    capture(*sys.argv[1:])
