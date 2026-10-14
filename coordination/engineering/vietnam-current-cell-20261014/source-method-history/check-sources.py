"""Bounded Vietnam source qualification; source-relative cells retain a physical hold."""
import collections, gzip, hashlib, json, resource, subprocess, time
from pathlib import Path
import numpy as np
import shapely
from shapely.geometry import shape, Polygon
BASE='f7c358326d776398bc1cffe84df81eac7033091c'
CORPUS='9431af7bce2729274500f6733843ebd5b1315117'
QUEUE='coordination/engineering/global-current-cell-work-queue-20261014/'
OUT=Path('.cache/vietnam-20261014/source-qualification')
KINDS=['repair-evaluation','physical-interpretation']
FAMILIES=['gb:CHN:ADM1','gb:KHM:ADM1','gb:LAO:ADM1','gb:VNM:ADM1','gb:VNM:ADM2']
START=time.monotonic(); CPU=time.process_time(); inputs={}
sha=lambda raw:hashlib.sha256(raw).hexdigest()
def read(path,commit=BASE):
    raw=subprocess.check_output(['git','show',commit+':'+path])
    record={'commit':commit,'path':path,'bytes':len(raw),'sha256':sha(raw),'git_blob_oid':subprocess.check_output(['git','rev-parse',commit+':'+path],text=True).strip()}
    if path.endswith('.gz'):
        decoded=gzip.decompress(raw);record.update(decoded_bytes=len(decoded),decoded_sha256=sha(decoded))
    else:decoded=raw
    inputs[commit+':'+path]=record
    return decoded
def jread(path,commit=BASE):return json.loads(read(path,commit))
def localread(path):
    raw=path.read_bytes();record={'path':str(path),'bytes':len(raw),'sha256':sha(raw),'role':'frozen-package-extraction'}
    if str(path).endswith('.gz'):
        decoded=gzip.decompress(raw);record.update(decoded_bytes=len(decoded),decoded_sha256=sha(decoded))
    else:decoded=raw
    inputs[str(path)]=record;return json.loads(decoded)
def write(name,value):
    raw=(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
    if name.endswith('.gz'):raw=gzip.compress(raw,compresslevel=9,mtime=0)
    with (OUT/name).open('xb') as f:f.write(raw)
    return {'path':str(OUT/name),'bytes':len(raw),'sha256':sha(raw)}
# Reject output collisions before computation. Complete receipt is written last.
for name in ['result.json','cells.json.gz','qualified-patch.json','held-selectors.json.gz','original-stage-inputs.json','publication.json']:
    assert not (OUT/name).exists() and not (OUT/name).is_symlink(),name
cat=jread(QUEUE+'retained-source-catalogue.json')
roster=jread(QUEUE+'source-feature-roster.json.gz')
featurebyid={f['source_id']:f for f in roster if any(f['source_id'].startswith(k+':') for k in FAMILIES)}
featurebysid={f['source_index']:f for f in featurebyid.values()};del roster
lineage=jread(QUEUE+'lineage.json.gz');byowner={f['index']:f for f in lineage['locations']}
packages={};cells=[];seen=set()
for kind in KINDS:
    folder=OUT.parent/kind;p=localread(folder/'package.json');packages[kind]=p
    start=len(cells)
    for block in p['native_blocks']:
        for y,a,z,owners,sids,physical in localread(folder/f'block-{block:03}.json.gz'):
            assert len(owners)==1
            for x in range(a,z):
                assert (x,y) not in seen;seen.add((x,y))
                cells.append({'x':x,'y':y,'owner':owners[0],'declared_sids':sids,'physical':physical,'package':kind,'flags':[]})
    assert len(cells)-start==p['native_cells']
assert len(cells)==40525
owners=sorted({c['owner'] for c in cells}); ownercells=collections.defaultdict(list)
for i,c in enumerate(cells):ownercells[c['owner']].append(i)
for owner in owners:
    rec=byowner[owner];assert rec['source_atoms']
    for atom in rec['source_atoms']:
        assert owner in lineage['reverse'][atom]
        assert owner in featurebyid[atom]['owners']
assert len(byowner[58]['source_atoms'])==7
latpath='coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'
latitudes=np.frombuffer(read(latpath,'5b32388df0501b013ac9a3ba97864932db493d59'),dtype='<f8')
assert len(latitudes)==262166
points=shapely.points([[(c['x']+.5)/262166*360-180,latitudes[c['y']]] for c in cells])
actual=[set() for _ in cells];boundary=[[] for _ in cells];invalid=[[] for _ in cells]
inventory=[];members=[];originals={};original_features={};selected_features={};geoms=[];idents=[];invalidfeatures=[]
for family in FAMILIES:
    p=next(p for p in cat['products'] if p['key']==family);pieces=[]
    for part in p['parts']:
        raw=read(part['path'],CORPUS);pin=inputs[CORPUS+':'+part['path']]
        assert pin['sha256']==part['sha256'] and sha(raw)==part['uncompressed_sha256'];pieces.append(raw)
    raw=b''.join(pieces);assert sha(raw)==p['original_sha256'] and len(raw)==p['original_bytes']
    data=json.loads(raw);assert data['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
    assert len(data['features'])==p['feature_count']
    inventory.append({k:p[k] for k in ['key','feature_count','original_bytes','original_sha256','recorded_license','source_represented_year_claim','recorded_consumed_url']})
    for f in data['features']:
        ident=family+':'+f['properties']['shapeID'];g=shape(f['geometry']);assert ident in featurebyid
        geoms.append(g);idents.append(ident);originals[ident]=g;original_features[ident]=f
        if not g.is_valid:invalidfeatures.append({'id':ident,'reason':shapely.is_valid_reason(g)})
    del data,raw,pieces
assert len(geoms)==849
# A tree prunes bounds only; covered_by still tests original unmodified geometries.
tree=shapely.STRtree(geoms);pairs=tree.query(points,predicate='covered_by');membercounts=collections.Counter()
for pi,gi in pairs.T:
    pi=int(pi);gi=int(gi);ident=idents[gi];actual[pi].add(featurebyid[ident]['source_index']);membercounts[ident]+=1
    if not geoms[gi].is_valid:invalid[pi].append(ident)
bpairs=tree.query(points,predicate='touches')
for pi,gi in bpairs.T:boundary[int(pi)].append(idents[int(gi)])
for ident,n in sorted(membercounts.items()):
    g=originals[ident];members.append({'id':ident,'name':featurebyid[ident]['name'],'cells':n,'valid':bool(g.is_valid),'interior_rings':sum(len(p.interiors) for p in ([g] if g.geom_type=='Polygon' else g.geoms))})
# All retained country polygons are tested, including marine disputed-country features.
nepath='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz'
raw=read(nepath);sourcepins=jread('data/sources.json');assert sha(raw)==sourcepins['hashes']['ne_10m_admin_0_countries']
countrydata=json.loads(raw)['features'];countrygeoms=[shape(f['geometry']) for f in countrydata];countryids=[f['properties']['ADM0_A3'] for f in countrydata]
countryhits=[[] for _ in cells];countryboundary=[[] for _ in cells]
for pi,gi in shapely.STRtree(countrygeoms).query(points,predicate='covered_by').T:countryhits[int(pi)].append(countryids[int(gi)])
for pi,gi in shapely.STRtree(countrygeoms).query(points,predicate='touches').T:countryboundary[int(pi)].append(countryids[int(gi)])
countryinventory={'features':len(countrygeoms),'invalid_features':[countryids[i] for i,g in enumerate(countrygeoms) if not g.is_valid]}
del countrydata,raw
# Accepted geometry and its existing exclusion holes; no geometry is repaired here.
selected={};selectedcovers=[False for _ in cells];selectedholes=[False for _ in cells]
for part in ['data/geography/part-27.json','data/geography/part-28.json']:
    data=jread(part)
    for f in data['features']:
        matched=[o for o in owners if byowner[o]['id']==f['id']]
        if not matched:continue
        owner=matched[0];selected_features[owner]=f;g=shape(f['geometry']);assert g.is_valid
        pp=[g] if g.geom_type=='Polygon' else list(g.geoms)
        rings=[Polygon(r) for p in pp for r in p.interiors]
        idx=ownercells[owner];hits=shapely.covers(g,points[idx])
        for i,hit in zip(idx,hits):selectedcovers[i]=bool(hit)
        for ring in rings:
            for i,hit in zip(idx,shapely.covers(ring,points[idx])):
                if hit:selectedholes[i]=True
        atoms=byowner[owner]['source_atoms']
        selected[owner]={'id':f['id'],'name':byowner[owner]['name'],'province_id':byowner[owner]['province_id'],'source_atoms':atoms,'accepted_geometry_sha256':sha(json.dumps(f['geometry'],sort_keys=True,separators=(',',':')).encode()),'accepted_geometry_valid':True,'accepted_interior_rings':len(rings),'original_interior_rings':sum(sum(len(p.interiors) for p in ([originals[a]] if originals[a].geom_type=='Polygon' else originals[a].geoms)) for a in atoms),'metadata':f['properties']['metadata']}
    del data
assert set(selected)==set(owners),(len(selected),len(owners),set(owners)-set(selected))
read('scripts/reconcile-topology.py');read('scripts/prepare.mjs')
topology=jread('data/topology-report.json');assert not set(x['id'] for x in topology['retired'])&set(byowner[o]['id'] for o in owners)
decisions=jread('data/geographic-decisions/asia.json')
scoped_reviews=[r for r in decisions['location_review'] if set(r.get('ids',[]))&set(byowner[o]['id'] for o in owners)]
for i,c in enumerate(cells):
    c['actual_sids']=sorted(actual[i]);c['reference_countries']=sorted(countryhits[i]);c['source_boundary_ids']=boundary[i];c['country_boundary_ids']=countryboundary[i];c['accepted_geometry_covers']=selectedcovers[i];c['accepted_hole_covers']=selectedholes[i]
    if actual[i]!=set(c['declared_sids']):c['flags'].append('source-membership-mismatch')
    if invalid[i]:c['flags'].append('invalid-original-geometry')
    if boundary[i] or countryboundary[i]:c['flags'].append('exact-source-or-country-boundary')
    if any(k!='VNM' for k in countryhits[i]):c['flags'].append('foreign-reference-country')
    if any(not featurebysid[s]['source_id'].startswith('gb:VNM:') for s in actual[i]):c['flags'].append('foreign-source-family')
    coveringowners=set(o for s in actual[i] for o in featurebysid[s]['owners'])
    c['covering_owners']=sorted(coveringowners)
    if coveringowners!={c['owner']}:c['flags'].append('source-owner-membership-conflict')
    atomids=set(byowner[c['owner']]['source_atoms'])
    if not atomids&set(featurebysid[s]['source_id'] for s in actual[i]):c['flags'].append('declared-owner-atom-not-covered')
    if selectedholes[i]:c['flags'].append('accepted-interior-ring-exclusion')
    if c['owner'] in [48444,48238]:c['flags'].append('disputed-island-territory-research')
    if c['owner']==58:c['flags'].append('merged-city-authority-constructor-unsupported')
# A conflict holds that entire current-location cohort in both packages, preserving coherent locality dispositions.
ownerflags={o:sorted(set(flag for i in idx for flag in cells[i]['flags'])) for o,idx in ownercells.items()}
for c in cells:
    c['territorial_hold_reasons']=ownerflags[c['owner']]
    c['hold_reasons']=list(c['territorial_hold_reasons'])
    if c['physical']=='source-relative':c['hold_reasons'].append('source-relative-physical-interpretation-unresolved')
    c['qualified']=not c['hold_reasons']
def compact(selected,with_reasons=False):
    grouped=collections.defaultdict(list)
    for c in selected:
        key=(c['package'],c['y'],c['owner'],c['physical'],tuple(c['hold_reasons']) if with_reasons else ())
        grouped[key].append(c['x'])
    rows=[]
    for (kind,y,owner,physical,reasons),xs in sorted(grouped.items()):
        a=z=sorted(xs)[0]
        for x in sorted(xs)[1:]+[None]:
            if x==z+1:z=x;continue
            rows.append({'package':kind,'y':y,'start':a,'end':z+1,'owner':owner,'physical':physical,**({'reasons':list(reasons)} if with_reasons else {})})
            a=z=x
    return rows
qualified=[c for c in cells if c['qualified']];held=[c for c in cells if not c['qualified']]
patch=collections.defaultdict(list)
for r in compact(qualified):patch[r['y']].append([r['start'],r['end'],r['owner']])
cohorts=[]
for o,idx in sorted(ownercells.items()):
    cs=[cells[i] for i in idx]
    cohorts.append({'owner':o,'id':byowner[o]['id'],'name':byowner[o]['name'],'province_id':byowner[o]['province_id'],'cells':len(cs),'packages':dict(collections.Counter(c['package'] for c in cs)),'physical_classes':dict(collections.Counter(c['physical'] for c in cs)),'qualified_cells':sum(c['qualified'] for c in cs),'direct_flag_counts':dict(collections.Counter(f for c in cs for f in c['flags'])),'territorial_hold_reasons':ownerflags[o],'reference_country_counts':[{'countries':list(k),'cells':v} for k,v in sorted(collections.Counter(tuple(c['reference_countries']) for c in cs).items())]})
summary={'version':1,'base_commit':BASE,'corpus_commit':CORPUS,'method':'All 849 original features of five complete families and every retained Natural Earth country polygon tested with Shapely covered_by at authenticated native centres. Original geometry, no repair/buffer. Cohort holds apply to whole current-location owner across both packages. Country absence alone is not a veto.','candidate_cells':len(cells),'qualified_cells':len(qualified),'held_cells':len(held),'package_counts':{kind:{'total':sum(c['package']==kind for c in cells),'qualified':sum(c['package']==kind for c in qualified),'held':sum(c['package']==kind for c in held)} for kind in KINDS},'direct_flag_counts':dict(collections.Counter(f for c in cells for f in c['flags'])),'complete_families':inventory,'covering_source_members':members,'invalid_original_features':invalidfeatures,'country_inventory':countryinventory,'cohorts':cohorts,'selected_targets':list(selected.values()),'existing_source_reviews':scoped_reviews,'accepted_topology_policy':topology['policy'],'disposition_limits':['Qualified means bounded additive source-fit eligibility to existing owner, subject to separate current-owner-zero and physical witness validation; it is not new regional semantic approval or proof of a repaired delivery.','All 24880 source-relative cells remain physical-interpretation holds: original source coverage alone does not distinguish river, coast, ocean or vintage mismatch. No blanket ocean inference.','Hoang Sa and Truong Sa are explicitly held as disputed-territory research regardless of positive source coverage. Natural Earth is a retained display convention, not a sovereignty adjudication.','All direct conflict flags hold the complete current-location owner cohort in both packages. Other cells of that cohort are not independently asserted wrong.','VNM ADM2 represented-year claim 2020 and ADM1 2008 are retained source claims, not independently verified current administrative boundaries.','Existing source review and aggregate-member semantic questions remain open, including Da Nang. The seven source atoms authenticate existing lineage only.'],'runtime':{'python':__import__('sys').version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'numpy':np.__version__,'elapsed_seconds':time.monotonic()-START,'cpu_seconds':time.process_time()-CPU,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},'inputs':list(inputs.values())}
summary['runtime']['input_raw_plus_decoded_bytes']=sum(p['bytes']+p.get('decoded_bytes',0) for p in inputs.values())
outputs=[]
outputs.append(write('result.json',summary))
outputs.append(write('original-stage-inputs.json',[{'target':byowner[o]['id'],'family':'vnm','consumed':original_features[byowner[o]['id']],'selected':selected_features[o]} for o in sorted({c['owner'] for c in qualified})]))
outputs.append(write('cells.json.gz',cells))
outputs.append(write('qualified-patch.json',{'rows':[{'y':y,'runs':sorted(runs)} for y,runs in sorted(patch.items())]}))
outputs.append(write('held-selectors.json.gz',compact(held,True)))
receipt={'outputs':outputs,'candidate_cells':len(cells),'qualified_cells':len(qualified),'held_cells':len(held),'elapsed_seconds':time.monotonic()-START,'cpu_seconds':time.process_time()-CPU,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'script_sha256':sha(Path(__file__).read_bytes())}
write('publication.json',receipt)
print(json.dumps(receipt),flush=True)
