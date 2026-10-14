"""Exploratory east MMR qualification; adapted from reviewed Myeik covers method.

Run only with the lead's heavy-job slot. Does not propose or apply a native patch.
Inputs are immutable local Git blobs; unavailable blobs fail without network fetch.
"""
import collections, gzip, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path.cwd()
BASE = 'f7c358326d776398bc1cffe84df81eac7033091c'
CORPUS = '9431af7bce2729274500f6733843ebd5b1315117'
QUEUE = 'coordination/engineering/global-current-cell-work-queue-20261014/'
LATCOMMIT = '5b32388df0501b013ac9a3ba97864932db493d59'
LATPATH = 'coordination/engineering/native-grid-fidelity-1010-20261005-local15/results-v1/native-row-latitudes.f64le.gz'
OWNERS = {30111:'66882298B20948488348117',30113:'66882298B21195914889348',30135:'66882298B27866808767172',30163:'66882298B33854457780857',30170:'66882298B34816344861267',30263:'66882298B59879554977018',30292:'66882298B65618262001870',30354:'66882298B84564180686688',30374:'66882298B91132834391640',30387:'66882298B94192188096874'}
OWNERS = {k:'gb:MMR:ADM3:'+v for k,v in OWNERS.items()}
FAMILIES = ['gb:MMR:ADM1','gb:MMR:ADM2','gb:MMR:ADM3','gb:THA:ADM1','gb:THA:ADM2','gb:LAO:ADM1','gb:LAO:ADM2']
ENV = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
INPUTS = {}
SHA = lambda b: hashlib.sha256(b).hexdigest()

def read(path, commit=BASE):
    key = commit+':'+path
    oid = subprocess.check_output(['git','rev-parse',key],cwd=ROOT,env=ENV,text=True).strip()
    raw = subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT,env=ENV)
    body = gzip.decompress(raw) if path.endswith('.gz') else raw
    INPUTS[key] = dict(commit=commit,path=path,git_blob_oid=oid,bytes=len(raw),sha256=SHA(raw),decoded_bytes=len(body),decoded_sha256=SHA(body))
    assert sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values()) <= 256*1024*1024, 'Combined input byte budget'
    return body

def jread(path, commit=BASE):
    return json.loads(read(path,commit))

def unique(rows,key):
    out={}
    for row in rows:
        k=row[key]
        assert k not in out, ('Duplicate',key,k)
        out[k]=row
    return out

def prepare():
    queue=jread(QUEUE+'source-package-queue.json')
    shared={}
    for name,digest in queue['input_sha256'].items():
        path=QUEUE+name+('.gz' if name in ['lineage.json','source-feature-roster.json'] else '')
        body=read(path); assert SHA(body)==digest, name
        shared[name]=json.loads(body)
    assert len(shared)==8
    metadata_body=read('data/administrative-sources.json')
    catalogue=shared['retained-source-catalogue.json']
    assert SHA(metadata_body)==catalogue['baseline_pins']['data/administrative-sources.json']
    metadata=json.loads(metadata_body)
    for family in FAMILIES:
        product=next(p for p in catalogue['products'] if p['key']==family);m=metadata[family]
        assert SHA(json.dumps(m,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==product['metadata_sha256']
        assert m['boundaryISO']==family.split(':')[1] and m['boundaryType']==family.split(':')[2]
        assert int(m['admUnitCount'])==product['feature_count'] and m['sha256']==product['original_sha256']
        assert m['boundaryYearRepresented']==product['source_represented_year_claim'] and m['boundaryLicense']==product['recorded_license']
        assert m['simplifiedGeometryGeoJSON']==product['recorded_consumed_url']
    roster=shared['source-feature-roster.json'];byid=unique(roster,'source_id');bysid=unique(roster,'source_index')
    lineage=shared['lineage.json'];byowner=unique(lineage['locations'],'index');unique(lineage['locations'],'id')
    for owner,ident in OWNERS.items():
        loc=byowner[owner]
        assert loc['id']==ident and loc['source_atoms']==[ident]
        assert lineage['reverse'][ident]==[owner] and byid[ident]['owners']==[owner]
    def intervals(kind,b):
        pin=shared['source-census-summary.json']['blocks'][b] if kind=='source-candidates' else next(p for p in shared['physical-unassigned-summary.json']['phases'][b]['files'] if p['kind']==kind)
        path=QUEUE+f'{kind}-block-{b:03}.json.gz';body=read(path);actual=INPUTS[BASE+':'+path]
        assert actual['sha256']==pin['sha256'] and actual['decoded_sha256']==pin['decoded_sha256']
        return json.loads(body)
    blocks=sorted({b for owner in OWNERS for b in range(int(byowner[owner]['bounds'][1])//4096,int(byowner[owner]['bounds'][3])//4096+1)})
    assert blocks==[28,29]
    cells=[];seen=set()
    for b in blocks:
        land={r['y']:r['runs'] for r in intervals('physical-support',b)};water={r['y']:r['runs'] for r in intervals('inland-water-support',b)}
        for row in intervals('source-candidates',b):
            for a,z,owners,sids in row['runs']:
                if not set(owners).intersection(OWNERS):continue
                assert len(owners)==len(set(owners)) and len(sids)==len(set(sids))
                assert all(s in bysid for s in sids)
                for x in range(a,z):
                    assert (x,row['y']) not in seen;seen.add((x,row['y']))
                    onland=any(c<=x<d for c,d in land.get(row['y'],[]));onwater=any(c<=x<d for c,d in water.get(row['y'],[]));assert not(onland and onwater)
                    cells.append(dict(x=x,y=row['y'],owners=owners,sids=sids,physical='land' if onland else 'inland-water' if onwater else 'source-relative'))
    assert len(cells)==469
    assert collections.Counter((len(c['owners'])==1,c['physical']) for c in cells)=={(True,'land'):438,(False,'land'):18,(True,'source-relative'):13}
    current=jread('data/geography/part-15.json');currentbyid=unique(current['features'],'id')
    for owner,ident in OWNERS.items():
        f=currentbyid[ident];p=f['properties'];m=p['metadata']
        assert p['id']==ident and p['parent_id']==byowner[owner]['province_id']
        assert m['source_id']=='gb:MMR:ADM3' and m['original_id']==ident.split(':')[-1]
        assert p['reference_owner']=='Myanmar' and m['reference_year']=='2019' and m['source_role']=='Township'
    decisions=jread('data/geographic-decisions/asia.json')
    scoped=[d for d in decisions['location_review'] if set(d.get('ids',[])).intersection(OWNERS.values())]
    assert len(scoped)==8 and all(d['status']=='open' for d in scoped)
    changes=[d for d in decisions['location_changes'] if any(i in json.dumps(d) for i in OWNERS.values())]
    assert not changes, 'Unexamined location decision'
    read('scripts/reconcile-topology.py');read('scripts/prepare.mjs')
    return shared,byid,bysid,byowner,cells,currentbyid,scoped

def run(output):
    assert output.parent.is_dir() and not output.exists() and not output.is_symlink(), 'Fresh admitted output required'
    started=time.monotonic()
    shared,byid,bysid,byowner,cells,currentbyid,scoped=prepare()
    import numpy as np
    import shapely
    from shapely.geometry import shape, Polygon
    latitude_bytes=read(LATPATH,LATCOMMIT)
    assert SHA(latitude_bytes)=='66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23'
    latitudes=np.frombuffer(latitude_bytes,dtype='<f8');assert len(latitudes)==262166
    points=shapely.points([[(c['x']+.5)/262166*360-180,latitudes[c['y']]] for c in cells])
    actual=[set() for c in cells];boundary=[set() for c in cells];inventories=[];members=[];target_geometries={}
    catalogue=shared['retained-source-catalogue.json'];products=unique(catalogue['products'],'key')
    for family in FAMILIES:
        product=products[family];pieces=[];offset=0
        for ordinal,part in enumerate(product['parts']):
            assert part['ordinal']==ordinal and part['offset']==offset
            body=read(part['path'],CORPUS);pin=INPUTS[CORPUS+':'+part['path']]
            assert pin['sha256']==part['sha256'] and SHA(body)==part['uncompressed_sha256']
            assert len(body)==part['uncompressed_bytes'];pieces.append(body);offset+=len(body)
        raw=b''.join(pieces);assert len(raw)==product['original_bytes'] and SHA(raw)==product['original_sha256']
        data=json.loads(raw);assert data['crs']['properties']['name']=='urn:ogc:def:crs:OGC:1.3:CRS84'
        assert len(data['features'])==product['feature_count']==product['advertised_feature_count']
        featureids=set();invalid=[]
        for ordinal,f in enumerate(data['features']):
            ident=family+':'+f['properties']['shapeID'];assert ident not in featureids;featureids.add(ident)
            row=byid[ident];assert row['ordinal']==ordinal and row['name']==f['properties']['shapeName']
            assert catalogue['products'][row['family_index']]['key']==family
            g=shape(f['geometry']);hits=shapely.covers(g,points);inside=shapely.contains(g,points)
            if not g.is_valid:invalid.append(ident)
            if ident in OWNERS.values():target_geometries[ident]=g
            if np.any(hits):
                assert g.is_valid, ('Covering invalid source',ident)
                members.append(dict(id=ident,name=row['name'],source_index=row['source_index'],cells=int(np.sum(hits))))
            for i in np.flatnonzero(hits):
                actual[i].add(row['source_index'])
                if not inside[i]:boundary[i].add(row['source_index'])
        expected={x['source_id'] for x in byid.values() if catalogue['products'][x['family_index']]['key']==family}
        assert featureids==expected, ('Complete family roster mismatch',family)
        inventories.append(dict(family=family,features=len(featureids),invalid_geometries=invalid,represented_year=product['source_represented_year_claim'],license=product['recorded_license'],original_sha256=SHA(raw)))
    assert sum(x['features'] for x in inventories)==1589
    mismatches=[dict(x=c['x'],y=c['y'],expected=c['sids'],actual=sorted(a)) for c,a in zip(cells,actual) if a!=set(c['sids'])]
    assert not mismatches, ('Source membership mismatch',mismatches[:10])
    refpath='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz'
    refraw=read(refpath);pins=jread('data/sources.json');assert SHA(refraw)==pins['hashes']['ne_10m_admin_0_countries']
    refs=json.loads(refraw)['features'];unique([dict(id=f['properties']['ADM0_A3']) for f in refs],'id')
    for c in cells:c['reference_countries']=[];c['reference_boundary']=[];c['current_members']=[];c['current_holes']=[];c['source_holes']=[]
    for f in refs:
        code=f['properties']['ADM0_A3'];g=shape(f['geometry']);hits=shapely.covers(g,points);inside=shapely.contains(g,points)
        if np.any(hits):assert g.is_valid
        for i in np.flatnonzero(hits):
            cells[i]['reference_countries'].append(code)
            if not inside[i]:cells[i]['reference_boundary'].append(code)
    target_summary=[]
    for owner,ident in OWNERS.items():
        current=shape(currentbyid[ident]['geometry']);source=target_geometries[ident]
        assert current.is_valid and source.is_valid
        hits=shapely.covers(current,points)
        for i in np.flatnonzero(hits):cells[i]['current_members'].append(owner)
        holes={}
        for label,g in [('current',current),('source',source)]:
            rings=[ring for poly in ([g] if g.geom_type=='Polygon' else g.geoms) for ring in poly.interiors];holes[label]=len(rings)
            for ring in rings:
                for i in np.flatnonzero(shapely.covers(Polygon(ring),points)):cells[i][label+'_holes'].append(owner)
        target_summary.append(dict(owner=owner,id=ident,name=byowner[owner]['name'],province_id=byowner[owner]['province_id'],holes=holes,current_geometry_sha256=SHA(json.dumps(currentbyid[ident]['geometry'],separators=(',',':')).encode()),current_covers_candidate_cells=int(np.sum(hits))))
    counts=collections.Counter()
    for i,c in enumerate(cells):
        c['source_boundary_sids']=sorted(boundary[i]);c['foreign_source_sids']=[sid for sid in c['sids'] if not bysid[sid]['source_id'].startswith('gb:MMR:')]
        c['foreign_reference_countries']=[code for code in c['reference_countries'] if code!='MMR']
        reasons=[]
        if len(c['owners'])!=1:reasons.append('source-owner-conflict')
        if c['physical']=='source-relative':reasons.append('physical-interpretation')
        if c['foreign_source_sids']:reasons.append('foreign-source-coverage')
        if c['foreign_reference_countries']:reasons.append('foreign-reference-coverage')
        if set(c['owners']).intersection(c['current_holes']):reasons.append('current-interior-hole')
        if set(c['owners']).intersection(c['source_holes']):reasons.append('source-interior-hole')
        if c['source_boundary_sids'] or c['reference_boundary']:reasons.append('boundary-point')
        c['qualification_flags']=reasons
        counts[tuple(c['owners']),tuple(reasons)]+=1
    result=dict(version=1,kind='exploratory-east-source-qualification',base_commit=BASE,runtime=dict(shapely=shapely.__version__,geos=shapely.geos_version_string,seconds=time.monotonic()-started),candidate_cells=len(cells),complete_families=inventories,covering_sources=members,source_membership_mismatches=mismatches,targets=target_summary,decisions=scoped,counts=[dict(owners=k[0],flags=k[1],cells=v) for k,v in sorted(counts.items())],cells=cells,inputs=list(INPUTS.values()),limits=['Read-only exploratory source qualification; no native patch, repaired cells or territorial approval.','Current owner-zero applicability is established separately by lead current cumulative-patch subtraction.','Physical class labels authenticate queue masks; no new original GSHHG reproduction is performed.','Country-reference membership is a display convention, not sovereignty adjudication.','Complete seven-family check does not claim a fresh worldwide source scan.','Unflagged cells still need accepted producer admission and selected-native conservation.'])
    # Exclusive creation avoids replacing retained evidence, including symlink targets.
    with output.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(output=str(output),sha256=SHA(output.read_bytes()),cells=len(cells),flag_counts=result['counts'],seconds=result['runtime']['seconds'],input_raw_plus_decoded_bytes=sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values()))))

if __name__=='__main__':
    if sys.argv[1:] == ['--preflight']:
        prepare();print(json.dumps(dict(preflight='passed',inputs=len(INPUTS),input_raw_plus_decoded_bytes=sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values()),gis_executed=False)))
    else:
        assert len(sys.argv)==2, 'Output path required'
        run(Path(sys.argv[1]))
