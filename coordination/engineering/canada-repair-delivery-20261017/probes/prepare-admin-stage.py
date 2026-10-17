import json,gzip,pathlib,subprocess,hashlib,collections,shutil
D=pathlib.Path(__file__).resolve().parent;W=pathlib.Path((D/'workspace.txt').read_text().strip());H=(D/'base.txt').read_text().strip();O=W/'coordination/engineering/canada-repair-delivery-20261017'
def raw(p,h=H):return subprocess.check_output(['git','-c','protocol.allow=never','-C',str(W),'show',h+':'+p])
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):
 dest=O/p;dest.parent.mkdir(parents=True,exist_ok=True)
 with dest.open('xb') as f:f.write((json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode())
screen=json.load(open(D.parent/'screen-complex-large-packages-20261017/screening.json'));pkg=next(p for p in screen['results'] if p['package']['primary_source']=='gb:CAN:ADM3');cat=json.loads(raw('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'));r=next(c for c in cat['products'] if c['key']=='gb:CAN:ADM3');parts=[]
for p in r['parts']:
 b=raw(p['path']);assert len(b)==p['bytes'] and sha(b)==p['sha256'];z=gzip.decompress(b);assert len(z)==p['uncompressed_bytes'] and sha(z)==p['uncompressed_sha256'];parts.append(z)
b=b''.join(parts);assert sha(b)==r['original_sha256'] and len(b)==r['original_bytes'];sources={'gb:CAN:ADM3:'+f['properties']['shapeID']:f for f in json.loads(b)['features']};assert len(sources)==r['feature_count']
sel=json.loads(raw('data/ownership-selection.json'));bp=sel['selected_geography'];b=raw(bp['path']);assert sha(b)==bp['sha256'] and len(b)==bp['bytes'];bank=json.loads(b);features={}
for commit,path in sorted({(o['target_pin']['commit'],o['target_pin']['path']) for o in pkg['owners']}):
 p=next(x for x in bank['unchanged_files']+bank['overrides'] if x['commit']==commit and x['path']==path);b=raw(path,commit);assert len(b)==p['bytes'] and sha(b)==p['sha256']
 if p.get('encoding')=='gzip':b=gzip.decompress(b);assert len(b)==p['decoded_bytes'] and sha(b)==p['decoded_sha256']
 features.update({x['id']:x for x in json.loads(b)['features']})
stages=[];mapping=[]
for o in pkg['owners']:
 f=features[o['id']];assert f['properties']==o['target_properties']
 if f['properties']['metadata'].get('source_id','').startswith('aafc:'):continue
 for s in o['source_atoms']:
  assert o['source_reverse_owners'][s]==[o['index']];stages.append({'target':s,'family':'can','consumed':sources[s],'selected':f});mapping.append({'source_id':s,'target_id':o['id'],'pixelIndex':o['index']})
assert len({s['target'] for s in stages})==len(stages)==1603
save('source-stage/admin-original-stage-inputs.json',stages);save('source-review/admin-source-target-membership.json',mapping);save('source-stage/package.json',pkg['package']);save('source-review/source-target-screening.json',pkg)
rows=[r for p in sorted((W/'.scratch/frozen-repair').glob('block-*.gz')) for r in json.loads(gzip.decompress(p.read_bytes()))];admins={m['pixelIndex'] for m in mapping};native=collections.defaultdict(list)
for y,a,z,owners,sids,kind in rows:
 if owners[0] in admins:native[y].append([a,z,owners[0]])
for r in native.values():r.sort()
save('source-stage/admin-requested-native-patch.json',{'rows':[{'y':y,'runs':r} for y,r in sorted(native.items())]})
for file in ['input-analysis.json','full-source-custody.json','current-overlap.json','aafc-applicability.json','membership-probe.json']:
 with (O/'source-review'/file).open('xb') as f:f.write((D/file).read_bytes())
for file in ['foreign-original-intervals.json.gz','aafc-point-observations.json.gz']:
 with (O/'source-review'/file).open('xb') as f:f.write((D/file).read_bytes())
for file in ['analyze-inputs.py','analyze-aafc.py','probe-membership.mjs','prepare-admin-stage.py']:
 dest=O/'probes'/file;dest.parent.mkdir(exist_ok=True)
 with dest.open('xb') as f:f.write((D/file).read_bytes())
print(json.dumps({'positive_members':len(stages),'owners':len(admins),'candidate_cells':sum(z-a for rs in native.values() for a,z,o in rs),'stage_bytes':(O/'source-stage/admin-original-stage-inputs.json').stat().st_size,'packet_total_bytes':sum(p.stat().st_size for p in O.rglob('*') if p.is_file())}))
