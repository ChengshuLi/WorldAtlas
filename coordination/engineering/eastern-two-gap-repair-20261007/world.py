"""Read-only prepared current-world closure for #1295. No geometry operations."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess

TARGETS=('atlas:physical:CAN-103:QUE','atlas:physical:CAN-114:NFL')
def load_world(repo,commit,expected):
    if not re.fullmatch('[a-f0-9]{40}',commit):raise ValueError('Immutable lowercase40hex before any Git')
    used={}
    def read(path):
        if path not in expected:raise ValueError('Undeclared complete-world source: '+path)
        entry=subprocess.check_output(['git','-C',repo,'ls-tree','-z',commit,'--',path])
        if not entry.startswith((b'100644 blob ',b'100755 blob ')) or not entry.endswith(path.encode()+b'\0'):
            raise ValueError('Require exact ordinary source blob')
        raw=subprocess.check_output(['git','-C',repo,'show',commit+':'+path])
        pin=expected[path]
        if len(raw)!=pin['logical_bytes'] or hashlib.sha256(raw).hexdigest()!=pin['logical_sha256']:
            raise ValueError('Whole current source bytes changed: '+path)
        used[path]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'commit':commit}
        return json.loads(raw)
    index=read('data/world-index.json');parts=index['parts']
    if len(parts)!=36 or len(set(parts))!=36:raise ValueError('Exact complete36 current source parts required')
    if {'data/world-index.json',*('data/'+p for p in parts)}!=set(expected):
        raise ValueError('No omitted or extra full-world source')
    features={};part_counts={};physical={}
    for name in parts:
        path='data/'+name;collection=read(path)
        if collection.get('type')!='FeatureCollection':raise ValueError('Whole source collection required')
        part_counts[path]=len(collection['features'])
        for f in collection['features']:
            identity=f['id']
            if identity in features:raise ValueError('Duplicate full-world ID')
            features[identity]=f
            m=f['properties']['metadata']
            if m.get('source_id','').startswith(('aafc:','resolve:','ibra:')) and m.get('source_member_ids'):
                physical[identity]=m['source_member_ids']
    if len(features)!=49625 or not set(TARGETS)<=set(features):raise ValueError('Complete49625 world required')
    subjects=set(TARGETS);members=set()
    while True:
        old=(set(subjects),set(members))
        for identity,ids in physical.items():
            if identity in subjects or members.intersection(ids):subjects.add(identity);members.update(ids)
        if old==(subjects,members):break
    if len(subjects)!=24 or len(members)!=477:raise ValueError('Full approved24/477 fixedpoint closure changed')
    return features,{'commit':commit,'complete_feature_count':len(features),'whole_source_pins':used,
                     'part_counts':part_counts,'fixedpoint_current_subject_ids':sorted(subjects),
                     'fixedpoint_retired_member_ids':sorted(members),'geometry_operations':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',required=True);p.add_argument('--commit',required=True)
    p.add_argument('--input-plan',required=True);p.add_argument('--receipt',required=True);a=p.parse_args()
    plan=json.loads(Path(a.input_plan).read_bytes());expected={x['logical_path']:x for x in plan['inputs']if x['group']=='complete-current-world'}
    _,receipt=load_world(a.repo,a.commit,expected)
    target=Path(a.receipt)
    with target.open('x')as f:json.dump(receipt,f,sort_keys=True,separators=(',',':'));f.write('\n')
    print(json.dumps({'whole_world':receipt['complete_feature_count'],'parts':len(receipt['part_counts']),
                      'closure':len(receipt['fixedpoint_current_subject_ids']),'members':len(receipt['fixedpoint_retired_member_ids'])}))
