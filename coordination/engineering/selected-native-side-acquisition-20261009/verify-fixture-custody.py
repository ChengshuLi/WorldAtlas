"""Verify complete retained synthetic Git objects, without producer execution."""
import base64,gzip,hashlib,json,pathlib,sys
MAX=32*1024*1024
root=pathlib.Path(__file__).resolve().parent/'qualification'/'fixtures'
objects=commits=encoded=decoded=0
for p in sorted(root.glob('*.json.gz')):
    raw=p.read_bytes();assert len(raw)<=MAX
    with gzip.open(p,'rb') as f: body=f.read(MAX+1)
    assert len(body)<=MAX
    value=json.loads(body);assert value['kind']=='complete-synthetic-immutable-entry-fixture' and value['source_approval'] is False
    seen=set()
    for row in value['objects']:
        data=base64.b64decode(row['base64'],validate=True)
        assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        assert row['type'] in ('blob','tree','commit')
        assert hashlib.sha1((row['type']+' '+str(len(data))+'\0').encode()+data).hexdigest()==row['oid']
        assert row['oid'] not in seen;seen.add(row['oid'])
    assert all(c in seen for c in value['commits'])
    objects+=len(seen);commits+=len(value['commits']);encoded+=len(raw);decoded+=len(body)
assert objects>0
print(json.dumps({'kind':'whole-synthetic-git-object-inverse','files':len(list(root.glob('*.json.gz'))),'objects':objects,'issued_commits':commits,'encoded_bytes':encoded,'decoded_bytes':decoded,'source_approval':False,'producer_reexecuted':False},sort_keys=True))
