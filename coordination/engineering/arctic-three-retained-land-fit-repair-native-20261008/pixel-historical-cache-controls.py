"""Real whole-cache/installed-record boundary controls; no area or GIS execution."""
import pathlib,sys,json,gzip,hashlib,runpy,copy
module=runpy.run_path(str(pathlib.Path(__file__).with_name('pixel-source-area.py')))
read=module['admitted_read'];guard=module['historical_source_area'];targets=module['TARGETS']
plan=json.loads(pathlib.Path(sys.argv[1]).read_text())
provenance=json.loads(pathlib.Path(sys.argv[2]).read_text())
caches=[]
for p in provenance:
    pin={'path':p['path'],'bytes':p['encoded_bytes'],'mode':0o644,'sha256':p['encoded_sha256']}
    wire=read(pin)
    import io
    with gzip.GzipFile(fileobj=io.BytesIO(wire)) as stream:
        raw=stream.read(p['decoded_bytes']+1)
        assert len(raw)==p['decoded_bytes'] and not stream.read(1)
    assert hashlib.sha256(raw).hexdigest()==p['decoded_sha256']
    caches.append(json.loads(raw))
pin=plan['original_context'];wire=read(pin);raw=gzip.decompress(wire)
assert len(raw)==pin['decoded_bytes'] and hashlib.sha256(raw).hexdigest()==pin['decoded_sha256']
rows=json.loads(raw);before={row['id']:row for row in rows if row['id'] in targets}
installed=json.loads(read(plan['original_pixel']))
historical_pin=json.loads(pathlib.Path(sys.argv[3]).read_text())
historical=json.loads(read(historical_pin))
# Whole bodies above are authenticated. Retain only the exact target views for
# repeated adverse mutations; no area or unrelated geometry operations.
installed={'records':[row for row in installed['records'] if row['id'] in targets]}
historical={'features':[row for row in historical['features'] if row['id'] in targets]}
for cache in caches:cache['areas']={identity:cache['areas'][identity] for identity in targets}
positive=negative=0
for identity in targets:
    value=guard(identity,before[identity],installed,historical,caches)
    assert value==provenance[0]['targets'][identity]==provenance[1]['targets'][identity]
    positive+=1
identity=targets[0]
def reject(change):
    global negative
    args=[identity,copy.deepcopy(before[identity]),copy.deepcopy(installed),copy.deepcopy(historical),copy.deepcopy(caches)]
    change(args)
    try: guard(*args)
    except (AssertionError,KeyError): negative+=1
    else: raise AssertionError('Historical cache guard wrongly accepted')
reject(lambda a:a.__setitem__(0,'foreign'))
reject(lambda a:a[3]['features'].extend([next(x for x in a[3]['features'] if x['id']==identity)]))
reject(lambda a:a[3]['features'].__setitem__(slice(None),[x for x in a[3]['features'] if x['id']!=identity]))
reject(lambda a:a[1].__setitem__('geometry',{'type':'Polygon','coordinates':[]}))
reject(lambda a:a[4][0]['areas'].__setitem__(identity,0))
reject(lambda a:a[4][1]['areas'].__setitem__(identity,a[4][1]['areas'][identity]+1))
reject(lambda a:a[4][0]['algorithms'][0].__setitem__('sha256','0'*64))
reject(lambda a:a[4][0].__setitem__('footprints_sha256','0'*64))
reject(lambda a:a[4][1]['incremental_reuse']['recomputed_ids'].append(identity))
reject(lambda a:next(x for x in a[2]['records'] if x['id']==identity).__setitem__('source_wgs84_area_m2',1))
reject(lambda a:a[2]['records'].append(next(x for x in a[2]['records'] if x['id']==identity)))
reject(lambda a:a[4].pop())
print(json.dumps({'positive':positive,'negative':negative,'areas_computed':0,'original_recomputation_claimed':False,'complete_original_caches_authenticated':True}))
