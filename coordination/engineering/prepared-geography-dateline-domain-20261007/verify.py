"""Whole-byte, whole-row readback; not a third worldwide geometry execution."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

CASE=Path(__file__).resolve().parent
ROOT=CASE.parents[2]
spec=importlib.util.spec_from_file_location('prepared_validation_producer',CASE/'producer.py')
p=importlib.util.module_from_spec(spec);sys.modules[spec.name]=p;spec.loader.exec_module(p)


def checked(root,pin):
    name=p.safe_path(pin['path'])
    target=root/name
    if not target.is_relative_to(root) or any(x.is_symlink() for x in [target,*target.parents]):
        raise ValueError('Output escapes ordinary nonsymlink run root')
    raw=target.read_bytes()
    if len(raw)>p.MAX or len(raw)!=pin['bytes'] or p.hash_bytes(raw)!=pin['sha256']:
        raise ValueError('Output whole-byte mismatch')
    if name.endswith('.gz'):
        import io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            decoded=stream.read(p.MAX+1)
        if len(decoded)>p.MAX or len(decoded)!=pin['uncompressed_bytes'] or p.hash_bytes(decoded)!=pin['uncompressed_sha256']:
            raise ValueError('Output decoded-byte mismatch')
        return decoded
    return raw


def verify(one,two,science_commit,reader_commit):
    for commit in [science_commit,reader_commit]:
        if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable commits required')
    actual=[]
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if not filename:continue
        path=Path(filename).resolve()
        if path.is_relative_to(ROOT) and path.suffix=='.py':
            rel=str(path.relative_to(ROOT));raw=path.read_bytes()
            if raw!=p.read_git(reader_commit,rel):raise ValueError('Actual reader import differs from immutable reader')
            actual.append(p.descriptor(rel,raw))
    config=json.loads(p.read_git(science_commit,str((CASE/'config.json').relative_to(ROOT))))
    reports=[]
    for root in [one,two]:
        if not root.is_absolute() or '..' in root.parts or any(x.is_symlink() for x in [root,*root.parents]):raise ValueError('Bad run root')
        if (root/'report.json').is_symlink():raise ValueError('Report must be ordinary')
        raw=(root/'report.json').read_bytes()
        if len(raw)>p.MAX:raise ValueError('Report exceeds bound')
        report=json.loads(raw)
        if report['code_commit']!=science_commit or report['input_commit']!=config['input_commit'] or report['runtime']!=p.PINNED:
            raise ValueError('Actual execution/code/input/runtime mismatch')
        expected=[p.descriptor(path,p.read_git(science_commit,path)) for path in config['execution_code_paths']]
        if report['execution_code']!=expected:raise ValueError('Incomplete science execution closure')
        for pin in report['outputs']:checked(root,pin)
        if report['input_files']!=config['snapshot_files']+config['source_files'] or report['retained_fji']!=config['retained_fji']:
            raise ValueError('Incomplete actual scientific inputs')
        reports.append(report)
    if reports[0]['outputs']!=reports[1]['outputs'] or reports[0]['scientific_sha256']!=reports[1]['scientific_sha256']:
        raise ValueError('Two complete scientific families differ')
    first=reports[0]
    summary=json.loads(checked(one,first['outputs'][0]))
    if p.hash_bytes(p.canonical_json(summary))!=first['scientific_sha256']:raise ValueError('Summary scientific binding differs')
    if summary['complete_row_shards']!=first['outputs'][1:]:raise ValueError('Undeclared or omitted scientific shards')
    if summary['domain']!=p.geometry.PREPARED_DOMAIN or summary['input_commit']!=config['input_commit']:
        raise ValueError('Wrong full-family domain/vintage')
    p.checked_retained(config['retained_fji'])
    for pin in config['complete_diagnosis_files']:p.checked_retained(pin)
    lineage=json.loads((CASE/'diagnosis/complete-source-predecessor-lineage.json').read_bytes())
    original_by_id={r['current_id']:r for r in lineage['matches']}
    observations=summary['source_predecessor_observations']
    if len(observations)!=len(original_by_id) or {r['id'] for r in observations}!=set(original_by_id):
        raise ValueError('Incomplete original predecessor observations')
    for row in observations:
        old=original_by_id[row['id']]
        if row['source_geometry_sha256']!=old['source_geometry_sha256'] or row['original_members']!=old['source_members']:
            raise ValueError('Original source observation binding mismatch')
    rows={};ordered=[]
    for pin in summary['complete_row_shards']:
        body=json.loads(checked(one,pin))
        if body['domain']!=p.geometry.PREPARED_DOMAIN or len(body['rows'])!=pin['rows']:raise ValueError('Shard domain/count mismatch')
        for row in body['rows']:
            if row['id'] in rows:raise ValueError('Duplicate world row')
            rows[row['id']]=row;ordered.append(row['id'])
    if ordered!=sorted(ordered) or len(rows)!=config['expected_features']:raise ValueError('Incomplete ordered whole roster')
    baseline=p.Baseline(ROOT,config['input_commit'],config['snapshot_files']+config['source_files'])
    index=json.loads(baseline.read('data/world-index.json'))
    seen=set();failures=[];contacts=0
    for part in index['parts']:
        path='data/'+part
        for ordinal,feature in enumerate(json.loads(baseline.read(path))['features']):
            identity=feature['id'];row=rows[identity]
            if identity in seen:raise ValueError('Duplicate original input')
            seen.add(identity)
            expected={'containing_file':path,'feature_ordinal':ordinal,'original_feature_sha256':p.hash_bytes(p.canonical_json(feature)),
                      'original_geometry_sha256':p.hash_bytes(p.canonical_json(feature['geometry'])),'domain':p.geometry.PREPARED_DOMAIN}
            if any(row[k]!=v for k,v in expected.items()):raise ValueError('Complete original feature binding differs')
            if row['strict_default']['status']!='valid':
                failures.append(identity)
                if p.canonical_json(row['strict_default']['original_geometry'])!=p.canonical_json(feature['geometry']):raise ValueError('Original defect evidence lost')
                if p.canonical_json(row)!=p.canonical_json(p.validate_feature(feature,path,ordinal)):raise ValueError('Complete exceptional-feature method replay differs')
            if row['prepared']['status']!='valid':raise ValueError('Prepared failure hidden by successful receipt')
            if not re.fullmatch('[a-f0-9]{64}',row['prepared']['canonical_geometry_sha256']):raise ValueError('Missing canonical measurement binding')
            contacts+=len(row['prepared']['seam_contacts'])
    if seen!=set(rows) or sorted(failures)!=config['expected_default_failures'] or summary['containing_file_pins']!=config['snapshot_files']:
        raise ValueError('Full original/current roster or containing closure differs')
    if first['outcome']!='passed' or first['prepared_failures']!=0 or first['strict_default_failures']!=len(failures):raise ValueError('Wrong complete dispositions')
    return {'outcome':'passed','science_commit':science_commit,'reader_commit':reader_commit,'feature_count':len(rows),
            'strict_default_failure_ids':sorted(failures),'prepared_failure_count':0,'complete_directed_seam_contacts':contacts,
            'scientific_sha256':first['scientific_sha256'],'actual_reader_modules':actual,
            'actual_report_sha256':[p.hash_bytes((root/'report.json').read_bytes()) for root in [one,two]],
            'limits':['Two actual complete science executions authenticated. Every original feature and row bound; only three exceptional geometry cases replayed here, not a third world measurement. No source, water, authority, ownership, cause or repair approval.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-one',required=True);parser.add_argument('--run-two',required=True)
    parser.add_argument('--science-commit',required=True);parser.add_argument('--reader-commit',required=True)
    args=parser.parse_args();print(json.dumps(verify(Path(args.run_one),Path(args.run_two),args.science_commit,args.reader_commit),sort_keys=True))
