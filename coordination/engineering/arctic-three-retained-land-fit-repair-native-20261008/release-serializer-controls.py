"""Actual whole-record serialization boundary; no full successor qualification."""
import pathlib,sys,json,gzip,hashlib,importlib.util,copy
script=pathlib.Path(__file__).with_name('serialize-release-groups.py')
spec=importlib.util.spec_from_file_location('serializer',script);serializer=importlib.util.module_from_spec(spec);spec.loader.exec_module(serializer)
plan=json.loads(pathlib.Path(sys.argv[1]).read_bytes())
header=json.loads(pathlib.Path(sys.argv[2]).read_bytes())
codec=serializer.load_codec(plan['root'] if 'root' in plan else str(script.parents[3]))
positive=negative=0
for offset in (0,84750):
    original=next(p for p in plan['members'] if p['relative']==f'data/geographic-releases/8-memberships-{offset}.json.gz')
    pin={**original,'offset':offset};raw=serializer.admitted_read(pin)
    decoded=gzip.decompress(raw);assert hashlib.sha256(decoded).hexdigest()==pin['decoded_sha256']
    body=json.loads(decoded);payload=serializer.successor_member_payload(body,header,pin)
    assert payload['memberships'] is body['memberships']
    assert len(codec.canonical_json(payload))==len(decoded)
    assert json.loads(gzip.decompress(codec.deterministic_gzip(codec.canonical_json(payload))))==payload
    positive+=1
    cases=[(body,header,{**pin,'offset':offset+1}),
        (body,header,{**pin,'sha256':'0'*64}),
        ({**body,'release_id':'foreign'},header,pin),
        ({**body,'ingestion_id':'foreign'},header,pin),
        ({**body,'memberships':body['memberships'][:-1]},header,pin),
        (body,{**header,'complete_member_inputs':header['complete_member_inputs']*2},pin),
        (body,{**header,'release':{**header['release'],'version':8}},pin)]
    for source,binding,badpin in cases:
        try:serializer.successor_member_payload(source,binding,badpin)
        except AssertionError:negative+=1
        else:raise AssertionError('Wrongly accepted corrupted actual source boundary')
print(json.dumps({'positive':positive,'negative':negative,'complete_actual_first_last_records':True,
    'real_qualified_header':True,'unchanged_original_codec':True,'limit':'Per-batch boundary; full343 successor remains unexecuted.'}))
