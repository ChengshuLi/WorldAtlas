"""Rebuild and byte-compare original 334-target stage and 2,566,967-cell patch.
Usage: Python verify-original-stage.py REPO PACKET_COMMIT
Read-only immutable Git inputs. No network, clipping, geometry repair or writes.
"""
import collections,gzip,hashlib,json,pathlib,subprocess,sys
W=pathlib.Path(sys.argv[1]);H=sys.argv[2];P='coordination/engineering/russia-repair-delivery-20261017/';BASE='9d564cf4083cb5499b00d6fb4ceb6fc724fdf01c';Q='coordination/engineering/global-current-cell-work-queue-20261014/'
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p])
def data(p,h=H):return json.loads(raw(p,h))
def whole(pin):
 b=raw(pin['path'],pin['commit']);assert len(b)==pin['bytes'] and hashlib.sha256(b).hexdigest()==pin['sha256'];return b
def canonical(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
pkg=data(P+'source-stage/package.json');queue=data(Q+'source-package-queue.json',BASE);assert pkg==next(p for p in queue['packages'] if p['package_id']=='gb-RUS-ADM2--repair-evaluation');assert pkg['native_cells']==2566967 and len(pkg['owners'])==334 and pkg['interval_segments']==346353
custody=data(P+'source-review/source-custody.json');catalogue=json.loads(whole(custody['catalogue']));sources={};count=0
for family in custody['families']:
 rec=next(r for r in catalogue['products'] if r['key']==family['family']);assert rec==family['catalogue_record'];chunks=[]
 for pin in family['parts']:
  b=gzip.decompress(whole(pin));assert len(b)==pin['decoded_bytes'] and hashlib.sha256(b).hexdigest()==pin['decoded_sha256'];chunks.append(b)
 b=b''.join(chunks);assert len(b)==rec['original_bytes'] and hashlib.sha256(b).hexdigest()==rec['original_sha256'];features=json.loads(b)['features'];assert len(features)==rec['feature_count'];count+=len(features)
 for f in features:
  ident=family['family']+':'+f['properties']['shapeID'];assert ident not in sources;sources[ident]=f
assert len(custody['families'])==8 and count==2532
review=data(P+'source-review/source-target-review.json');bank=json.loads(whole(review['selected_bank']));current={}
for part in review['selected_parts']:
 assert part in bank['unchanged_files']
 for f in json.loads(whole(part))['features']:assert f['id'] not in current;current[f['id']]=f
lineage=json.loads(gzip.decompress(raw(Q+'lineage.json.gz',BASE)));locations={r['index']:r for r in lineage['locations']};roster=json.loads(gzip.decompress(raw(Q+'source-feature-roster.json.gz',BASE)));sourceowners={r['source_id']:r['owners'] for r in roster};stages=[]
for owner in pkg['owners']:
 loc=locations[owner];ident=loc['id'];assert loc['source_atoms']==[ident] and sourceowners[ident]==[owner];assert current[ident]['properties']['name']==sources[ident]['properties']['shapeName'];stages.append({'target':ident,'family':'rus','consumed':sources[ident],'selected':current[ident]})
assert canonical(stages)==raw(P+'source-stage/original-stage-inputs.json')
rows=[]
for block in range(5,24):rows+=json.loads(gzip.decompress(raw(P+f'source-stage/frozen-block-{block:03d}.json.gz')))
assert len(rows)==346353;native=collections.defaultdict(list);counts=collections.Counter();seen=set()
for y,a,z,owners,originals,kind in rows:
 assert len(owners)==1 and owners[0] in pkg['owners'] and kind in ('land','inland-water') and a<z
 native[y].append([a,z,owners[0]]);counts[kind]+=z-a;seen.add(owners[0])
for runs in native.values():
 runs.sort();assert all(left[1]<=right[0] for left,right in zip(runs,runs[1:]))
assert counts=={'land':2515829,'inland-water':51138} and seen==set(pkg['owners'])
patch={'rows':[{'y':y,'runs':runs} for y,runs in sorted(native.items())]};assert canonical(patch)==raw(P+'source-stage/native-patch.json')
print(json.dumps({'byte_equal_original_stage':True,'byte_equal_native_patch':True,'whole_denominator':sum(counts.values()),'original_segments':len(rows),'targets':len(stages),'complete_source_families':len(custody['families']),'complete_source_features':count,'class_counts':dict(counts)}))
