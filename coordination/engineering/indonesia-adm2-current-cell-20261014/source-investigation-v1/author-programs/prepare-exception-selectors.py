"""Private exact interval disposition preparation; no scientific repair writer."""
import bisect, collections, gzip, hashlib, json, os, resource, subprocess, sys, time
from pathlib import Path
os.environ['GIT_NO_LAZY_FETCH'] = '1'
BASE = 'f7c358326d776398bc1cffe84df81eac7033091c'
OUT = Path('.cache/idn-source-qualification-1884-v1')
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
EXTRACT = Path('.cache/idn-adm2-extraction-20261014-v1')
start = time.monotonic()
sha = lambda b: hashlib.sha256(b).hexdigest()
inputs = []

def read(path, expected=None, git=False):
    body = subprocess.check_output(['git', 'show', BASE+':'+str(path)]) if git else Path(path).read_bytes()
    if expected:
        assert len(body)==expected['bytes'] and sha(body)==expected['sha256']
    pin = {'path': str(path), 'bytes': len(body), 'sha256': sha(body)}
    if git:
        pin.update(commit=BASE, git_blob_oid=subprocess.check_output(['git','rev-parse',BASE+':'+str(path)],text=True).strip())
    if str(path).endswith('.gz'):
        body=gzip.decompress(body)
        pin.update(decoded_bytes=len(body), decoded_sha256=sha(body))
    assert len(body)<=32*1024*1024
    inputs.append(pin)
    return json.loads(body)

def holes(g):
    return sum(max(0,len(p)-1) for p in (g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]))

def publish(name, obj):
    body=(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode()
    assert len(body)<=32*1024*1024
    with (OUT/name).open('xb') as f:f.write(body)
    return {'path':str(OUT/name),'bytes':len(body),'sha256':sha(body)}

receipt=read('.cache/idn-adm2-current-accounting-v1/receipt.json')
assert receipt['accepted_head']==BASE
packages={category:read(EXTRACT/category/'package.json',receipt['input_files'][str(EXTRACT/category/'package.json')]) for category in ['repair','physical','conflict']}
owner_indices=set(n for p in packages.values() for n in p['owners'])
assert len(owner_indices)==344
lineage=read(QUEUE+'lineage.json.gz',git=True)
locations={r['index']:r for r in lineage['locations'] if r['index'] in owner_indices}
assert set(locations)==owner_indices
del lineage
current={f['id']:f for f in read('data/geography/part-10.json',git=True)['features']}
jakarta=next(f for f in read('data/geography/part-28.json',git=True)['features'] if f['id']=='atlas:city:IDN-1227')
current[jakarta['id']]=jakarta
raw=read('coordination/engineering/original-geography-source-corpus-20261006/payloads/gb-IDN-ADM2-000.bin.gz',git=True)
raw_holes={'gb:IDN:ADM2:'+f['properties']['shapeID']:holes(f['geometry']) for f in raw['features']}
assert len(raw_holes)==519
del raw
qualified=read(OUT/'source-qualification.json')
north={t['pixelIndex'] for t in qualified['targets']}
owner_rows=[]
exceptions=set()
for owner,loc in sorted(locations.items()):
    ident=loc['id'];feature=current.get(ident);metadata=feature['properties']['metadata'] if feature else {}
    reasons=[]
    if ident=='atlas:city:IDN-1227':reasons.append('aggregate-needs-admitted-source-mapping')
    if metadata.get('topology_reconciled'):reasons.append('retained-topology-exclusions-need-qualification')
    if metadata.get('display_geometry_repaired'):reasons.append('repaired-display-geometry-needs-qualification')
    if ident in raw_holes and (raw_holes[ident] or holes(feature['geometry'])):reasons.append('original-current-rings-need-territorial-interpretation')
    if reasons:exceptions.add(owner)
    owner_rows.append({'id':ident,'pixelIndex':owner,'name':loc['name'],'province_id':loc['province_id'],
      'source_atoms':loc['source_atoms'],'hold_reasons':reasons,
      'source_rings':raw_holes.get(ident),'current_rings':holes(feature['geometry']) if feature else None,
      'recorded_topology_conflicts':metadata.get('topology_conflicts'),
      'source_prerequisites_measured':owner in north,
      'next_action': 'Complete physical hierarchy and native authority' if owner in north else
                     'Qualify exact retained mapping/topology/territorial exclusions' if reasons else
                     'Resolve shared source mapping with relevant countries' if not ident.startswith('gb:IDN:ADM2:') else
                     'Run admitted source/physical qualification for a coherent next locality'})

patch_path='coordination/engineering/myeik-native-followup-20261014/patch.json'
patch=read(patch_path,receipt['input_files'][patch_path],git=True)
patch_rows={r['y']:r['runs'] for r in patch['rows']}
counts=collections.defaultdict(collections.Counter)
dispositions=[]
held_exceptions=[]
for category,package in packages.items():
    for block in package['native_blocks']:
        path=EXTRACT/category/f'block-{block:03}.json.gz'
        for y,a,z,owners,sids,physical in read(path,receipt['input_files'][str(path)]):
            rs=patch_rows.get(y,[])
            k=bisect.bisect_right([r[1] for r in rs],a)
            boundaries={a,z}
            overlaps=[]
            for p,t,occupied_owner in rs[k:]:
                if p>=z:break
                left,right=max(a,p),min(z,t)
                if left<right:
                    boundaries.update([left,right]);overlaps.append((left,right,occupied_owner))
            for left,right in zip(sorted(boundaries),sorted(boundaries)[1:]):
                occupied=next((n for p,t,n in overlaps if p<=left and right<=t),None)
                if occupied is not None:status='already-owned'
                elif category=='conflict':status='held-source-conflict'
                elif set(owners).intersection(exceptions):status='held-mapping-topology-rings'
                elif owners[0] in north:status='awaiting-physical-native' if category=='repair' else 'held-physical-interpretation'
                else:status='held-pending-cohort-qualification'
                row=[category,y,left,right,owners,sids,physical,status,occupied]
                dispositions.append(row);counts[category][status]+=right-left
                if occupied is None and (category=='conflict' or set(owners).intersection(exceptions)):
                    held_exceptions.append(row)
    assert sum(counts[category].values())==package['native_cells']
    assert counts[category]['already-owned']==receipt['categories'][category]['currently_owned_candidate_cells']
assert sum(v['already-owned'] for v in counts.values())==2794
assert sum(sum(v.values())-v['already-owned'] for v in counts.values())==321928
outputs=[]
outputs.append(publish('session-target-exceptions.json',{'version':1,'issue':1884,'accepted_head':BASE,
    'worker_id':'/root/idn_sources_61','subjects':344,'owner_rows':owner_rows,
    'exception_owner_indices':sorted(exceptions),'limits':['Metadata/rings identify conservative holds; they do not establish territorial or physical exclusion. Neighbor targets retain source-conflict holds independently.']}))
outputs.append(publish('held-exception-intervals.json',{'version':1,'issue':1884,'accepted_head':BASE,
    'columns':['category','y','start','end','owners','source_feature_indices','physical','status','occupied_owner'],
    'rows':held_exceptions,'cells':sum(r[3]-r[2] for r in held_exceptions),
    'repaired_credit':0,'next_action':'Qualify applicable mapping/territorial exclusions, retaining all source competitors; no nearest owner or bank inference.'}))
outputs.append(publish('session-preparation-dispositions.json',{'version':1,'issue':1884,'accepted_head':BASE,
    'stage':'private-source-preparation; no final scientific dispositions or repairs',
    'columns':['category','y','start','end','owners','source_feature_indices','physical','status','occupied_owner'],
    'rows':dispositions,'counts':dict(counts),'remaining_candidate_cells':321928,
    'already_owned_cells':2794,'native_authority_qualified_cells':0,'repaired_credit':0,
    'limits':['Exact current subtraction reuses authenticated current-ownership receipt and reads the same actual cumulative patch.',
              'Every frozen package interval is represented disjointly. Pending qualification holds are work remaining, not completed scientific exceptions.']}))
rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
rss=rss if sys.platform=='darwin' else rss*1024
assert rss<500*1024*1024
outputs.append(publish('exception-preparation-receipt.json',{'version':1,'issue':1884,'complete':True,
    'worker_id':'/root/idn_sources_61','program_sha256':sha((OUT/'prepare-exception-selectors.py').read_bytes()),
    'inputs':inputs,'outputs':outputs,'exception_locations':len(exceptions),
    'exception_interval_cells':sum(r[3]-r[2] for r in held_exceptions),'counts':dict(counts),
    'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss,'repaired_credit':0}))
print(json.dumps({'outputs':outputs,'exception_locations':len(exceptions),'counts':dict(counts),
                  'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss,'repaired_credit':0}))
