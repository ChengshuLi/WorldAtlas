"""Bounded independent Myeik source qualification at immutable repository base."""
import collections, gzip, hashlib, json, struct, subprocess, sys
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import shape
BASE = 'aaad1215c1b215b415d219b682bc0ff0380d8c73'
CORPUS = '9431af7bce2729274500f6733843ebd5b1315117'
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
OWNER_IDS = {30149:'gb:MMR:ADM3:66882298B30308301468052',30179:'gb:MMR:ADM3:66882298B36911639137507',30185:'gb:MMR:ADM3:66882298B40667774005147'}
inputs = {}
sha = lambda raw: hashlib.sha256(raw).hexdigest()
def read(path, commit=BASE):
    raw = subprocess.check_output(['git','show',commit+':'+path])
    inputs[commit+':'+path] = {'commit':commit,'path':path,'bytes':len(raw),'sha256':sha(raw),'git_blob_oid':subprocess.check_output(['git','rev-parse',commit+':'+path],text=True).strip()}
    if path.endswith('.gz'):
        decoded=gzip.decompress(raw); inputs[commit+':'+path].update(decoded_bytes=len(decoded),decoded_sha256=sha(decoded));return decoded
    return raw
def jread(path,commit=BASE):return json.loads(read(path,commit))
cat=jread(QUEUE+'retained-source-catalogue.json')
features=jread(QUEUE+'source-feature-roster.json.gz'); featurebyid={f['source_id']:f for f in features}
lineage=jread(QUEUE+'lineage.json.gz');byowner={f['index']:f for f in lineage['locations']}
for owner,ident in OWNER_IDS.items():
    assert byowner[owner]['id']==ident and byowner[owner]['source_atoms']==[ident]
    assert byowner[owner]['province_id']=='framework:province:myeik:2820a791707f'
    assert lineage['reverse'][ident]==[owner] and featurebyid[ident]['owners']==[owner]
sources=jread(QUEUE+'source-census-summary.json');physical=jread(QUEUE+'physical-unassigned-summary.json')
def intervals(kind,block):
    pin=sources['blocks'][block] if kind=='source-candidates' else next(f for f in physical['phases'][block]['files'] if f['kind']==kind)
    path=QUEUE+f'{kind}-block-{block:03}.json.gz';raw=read(path);actual=inputs[BASE+':'+path]
    assert actual['sha256']==pin['sha256'] and actual['decoded_sha256']==pin['decoded_sha256'];return json.loads(raw)
# Bounds are from immutable lineage, so examine every row block intersecting the three targets.
blocks=sorted(set(b for owner in OWNER_IDS for b in range(int(byowner[owner]['bounds'][1])//4096,int(byowner[owner]['bounds'][3])//4096+1)))
cells=[];counts=collections.Counter()
for block in blocks:
    land={r['y']:r['runs'] for r in intervals('physical-support',block)}
    water={r['y']:r['runs'] for r in intervals('inland-water-support',block)}
    for row in intervals('source-candidates',block):
        for a,z,owners,sids in row['runs']:
            if not set(OWNER_IDS).intersection(owners):continue
            for x in range(a,z):
                physical_class='land' if any(c<=x<d for c,d in land.get(row['y'],[])) else 'inland-water' if any(c<=x<d for c,d in water.get(row['y'],[])) else 'source-relative'
                counts[tuple(owners),physical_class]+=1
                cells.append({'x':x,'y':row['y'],'owners':owners,'sids':sids,'physical':physical_class})
latpath='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'
latitudes=np.frombuffer(read(latpath,'5b32388df0501b013ac9a3ba97864932db493d59'),dtype='<f8')
assert len(latitudes)==262166
points=shapely.points([[(c['x']+.5)/262166*360-180,latitudes[c['y']]] for c in cells])
actual=[set() for c in cells];family_inventory=[];source_members=[];geometries={}
for family in ['gb:MMR:ADM1','gb:MMR:ADM2','gb:MMR:ADM3','gb:THA:ADM1','gb:THA:ADM2']:
    product=next(p for p in cat['products'] if p['key']==family);pieces=[]
    for part in product['parts']:
        decoded=read(part['path'],CORPUS);pin=inputs[CORPUS+':'+part['path']]
        assert pin['sha256']==part['sha256'] and sha(decoded)==part['uncompressed_sha256'];pieces.append(decoded)
    raw=b''.join(pieces);assert len(raw)==product['original_bytes'] and sha(raw)==product['original_sha256']
    data=json.loads(raw); assert data['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
    assert len(data['features'])==product['feature_count']
    family_inventory.append({'source_family':family,'complete_features':len(data['features']),'source_bytes':len(raw),'sha256':sha(raw),'represented_year':product['source_represented_year_claim'],'recorded_license':product['recorded_license']})
    for f in data['features']:
        ident=family+':'+f['properties']['shapeID'];g=shape(f['geometry']);r=featurebyid[ident];hits=shapely.covers(g,points)
        if ident in OWNER_IDS.values():geometries[ident]=g
        if any(hits):
            assert g.is_valid
            source_members.append({'id':ident,'name':f['properties']['shapeName'],'candidate_cells':int(sum(hits)),'valid':g.is_valid})
        for i in np.flatnonzero(hits):actual[i].add(r['source_index'])
assert all(a==set(c['sids']) for a,c in zip(actual,cells))
nepath='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz'
raw=read(nepath);sourcepins=jread('data/sources.json');assert sha(raw)==sourcepins['hashes']['ne_10m_admin_0_countries']
countries={f['properties']['ADM0_A3']:shape(f['geometry']) for f in json.loads(raw)['features']}
for i,c in enumerate(cells):c['reference_countries']=[name for name in ['MMR','THA'] if countries[name].covers(points[i])]
base=jread('data/geography/part-15.json');selected=[]
for f in base['features']:
    if f['id'] not in OWNER_IDS.values():continue
    g=shape(f['geometry']);original=geometries[f['id']]
    holes=lambda s:sum(len(p.interiors) for p in ([s] if s.geom_type=='Polygon' else s.geoms))
    assert g.is_valid and original.is_valid and holes(g)==holes(original)==0
    selected.append({'id':f['id'],'properties':f['properties'],'base_geometry_sha256':sha(json.dumps(f['geometry'],separators=(',',':')).encode()),'base_holes':holes(g),'source_holes':holes(original)})
read('scripts/reconcile-topology.py');read('scripts/prepare.mjs')
decisions=jread('data/geographic-decisions/asia.json')
scoped_review=[r for r in decisions['location_review'] if set(r.get('ids',[])).intersection(OWNER_IDS.values())]
proposed=[c for c in cells if c['owners'] in [[30185],[30179]] and c['physical']=='land']
assert len(proposed)==1109 and all('THA' not in c['reference_countries'] for c in proposed)
held=[c for c in cells if c['owners']==[30149]];assert len(held)==56
border_counts=collections.Counter(tuple(c['reference_countries']) for c in held);assert border_counts=={('THA',):50,('MMR',):6}
rows={}
for c in proposed:rows.setdefault(c['y'],[]).append([c['x'],c['x']+1,c['owners'][0]])
patch=[]
for y,runs in sorted(rows.items()):
    merged=[]
    for r in sorted(runs):
        if merged and merged[-1][1]==r[0] and merged[-1][2]==r[2]:merged[-1][1]=r[1]
        else:merged.append(r)
    patch.append({'y':y,'runs':merged})
result={'version':1,'reviewer':'root-complete-measured-followup-review-myeik-qualification','base_commit':BASE,'method':'Independent Shapely covers at authenticated native centres, every feature of five complete relevant original source families; exact interval hash checks and original reference-country pin comparison. No global raster rerun.','runtime':{'shapely':shapely.__version__,'geos':shapely.geos_version_string},'blocks':blocks,'candidate_cells':len(cells),'counts':[{'owners':list(k[0]),'physical':k[1],'cells':n} for k,n in sorted(counts.items())],'complete_families':family_inventory,'covering_source_members':source_members,'source_membership_mismatch_cells':0,'selected_targets':selected,'existing_source_review':scoped_review,'recommended_proposed_cells':len(proposed),'proposed_patch':{'rows':patch},'tanintharyi_deferred_cells':held,'tanintharyi_reference_country_counts':[{'reference_countries':list(k),'cells':v} for k,v in border_counts.items()],'conflict_cells':[c for c in cells if len(c['owners'])>1],'source_relative_cells':sum(c['physical']=='source-relative' for c in cells),'limits':['Natural Earth is an existing display-reference border convention, not sovereignty adjudication; all 56 Tanintharyi land candidates deferred for coherent border reconciliation, including six on its Myanmar side.','GeoBoundaries 2019 source identification and selected lineage do not grant new regional semantic approval or historical attribute authority.','Absence from GSHHG land/water support does not establish ocean; 897 cells remain a physical-interpretation question. Existing river water is not an ownership exclusion.','Current-owner-zero and final cumulative preservation require separate selected-native readback; this receipt alone is source qualification.'],'inputs':list(inputs.values())}
output=Path(sys.argv[1]);output.parent.mkdir(parents=True,exist_ok=True)
with output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'output':str(output),'sha256':sha(output.read_bytes()),'candidate_cells':len(cells),'proposed_cells':len(proposed),'deferred_border':len(held),'source_membership_mismatches':0,'input_raw_plus_decoded_bytes':sum(p['bytes']+p.get('decoded_bytes',0) for p in inputs.values())}))
