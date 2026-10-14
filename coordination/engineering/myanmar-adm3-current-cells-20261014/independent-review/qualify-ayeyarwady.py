"""Exploratory Ayeyarwady MMR qualification; adapted from reviewed Myeik covers method.

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
OWNERS = {30114: 'gb:MMR:ADM3:66882298B21473836197235', 30167: 'gb:MMR:ADM3:66882298B3445717579771', 30174: 'gb:MMR:ADM3:66882298B35313795132071', 30210: 'gb:MMR:ADM3:66882298B45976501481961', 30215: 'gb:MMR:ADM3:66882298B46433982831447', 30228: 'gb:MMR:ADM3:66882298B48553142968450', 30251: 'gb:MMR:ADM3:66882298B5626975055677', 30259: 'gb:MMR:ADM3:66882298B59134367047252', 30272: 'gb:MMR:ADM3:66882298B62212267926712', 30274: 'gb:MMR:ADM3:66882298B62732217443925', 30285: 'gb:MMR:ADM3:66882298B63844124977533', 30336: 'gb:MMR:ADM3:66882298B78974611272668', 30362: 'gb:MMR:ADM3:66882298B87314551665108', 30384: 'gb:MMR:ADM3:66882298B93394455443594', 30397: 'gb:MMR:ADM3:66882298B97791680692613', 30399: 'gb:MMR:ADM3:66882298B98470543554215'}
PROVINCES = ['framework:province:labutta:e3180df7e500', 'framework:province:myaungmya:11e41b39a1e8', 'framework:province:pathein:d694e613f350', 'framework:province:pyapon:a99fc70716da']
FAMILIES = ['gb:MMR:ADM1', 'gb:MMR:ADM2', 'gb:MMR:ADM3', 'gb:BGD:ADM1', 'gb:CHN:ADM1', 'gb:IND:ADM1', 'gb:IND:ADM3', 'gb:LAO:ADM1', 'gb:THA:ADM1', 'gb:THA:ADM2', 'gb:LAO:ADM2']
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
        product=next(p for p in catalogue['products'] if p['key']==family)
        m=metadata[family] if product['original_metadata_file']=='data/administrative-sources.json' else jread(product['original_metadata_file'])
        assert SHA(json.dumps(m,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==product['metadata_sha256']
        assert m['boundaryISO']==family.split(':')[1] and m['boundaryType']==family.split(':')[2]
        assert int(m['admUnitCount'])==product['advertised_feature_count'] and m['sha256']==product['original_sha256']
        assert m['boundaryYearRepresented']==product['source_represented_year_claim'] and m['boundaryLicense']==product['recorded_license']
        assert m['simplifiedGeometryGeoJSON']==product['recorded_consumed_url']
    roster=shared['source-feature-roster.json'];byid=unique(roster,'source_id');bysid=unique(roster,'source_index')
    lineage=shared['lineage.json'];byowner=unique(lineage['locations'],'index');unique(lineage['locations'],'id')
    for owner,ident in OWNERS.items():
        loc=byowner[owner]
        assert loc['id']==ident and loc['source_atoms']==[ident]
        assert lineage['reverse'][ident]==[owner] and byid[ident]['owners']==[owner]
    assert set(OWNERS) == {x['index'] for x in lineage['locations'] if x['province_id'] in PROVINCES}, 'Complete parent locality roster'
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
    assert len(cells)==7069
    assert collections.Counter((len(c['owners'])==1,c['physical']) for c in cells)=={(True,'land'):5888,(True,'source-relative'):1181}
    current=jread('data/geography/part-15.json');currentbyid=unique(current['features'],'id')
    for owner,ident in OWNERS.items():
        f=currentbyid[ident];p=f['properties'];m=p['metadata']
        assert p['id']==ident and p['parent_id']==byowner[owner]['province_id']
        assert m['source_id']=='gb:MMR:ADM3' and m['original_id']==ident.split(':')[-1]
        assert p['reference_owner']=='Myanmar' and m['reference_year']=='2019' and m['source_role']=='Township'
    decisions=jread('data/geographic-decisions/asia.json')
    scoped=[d for d in decisions['location_review'] if set(d.get('ids',[])).intersection(OWNERS.values())]
    assert all('status' in d for d in scoped), 'Missing target decision status'
    changes=[d for d in decisions['location_changes'] if any(i in json.dumps(d) for i in OWNERS.values())]
    # Preserve every relevant location change for qualification, without assuming no decisions.
    scoped = dict(location_review=scoped, location_changes=changes)
    read('scripts/reconcile-topology.py');read('scripts/prepare.mjs')
    return shared,byid,bysid,byowner,cells,currentbyid,scoped

def prospective_admission(shared):
    products=unique(shared['retained-source-catalogue.json']['products'],'key')
    # Reads these immutable small context inputs now, before GIS. Repeated reads are deduplicated.
    read(LATPATH,LATCOMMIT)
    read('data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz')
    read('data/sources.json')
    source_bytes=0
    for family in FAMILIES:
        for part in products[family]['parts']:
            assert max(part['bytes'],part['uncompressed_bytes'])<=32*1024*1024, 'Source ordinary input limit'
            source_bytes+=part['bytes']+part['uncompressed_bytes']
            oid=subprocess.check_output(['git','rev-parse',CORPUS+':'+part['path']],cwd=ROOT,env=ENV,text=True).strip()
            size=int(subprocess.check_output(['git','cat-file','-s',oid],cwd=ROOT,env=ENV,text=True))
            assert size==part['bytes'], ('Original blob availability/size',part['path'])
    shared_bytes=sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values())
    # Reserve complete 32MiB output plus adapted executable/config admission room.
    reserve=32*1024*1024+1024*1024
    assert shared_bytes+source_bytes+reserve<=256*1024*1024, 'Prospective complete phase budget'
    return dict(shared_input_bytes=shared_bytes,source_input_bytes=source_bytes,reserved_output_and_code_bytes=reserve,complete_prospective_bytes=shared_bytes+source_bytes+reserve,complete_family_features=sum(products[f]['feature_count'] for f in FAMILIES))

def run(output):
    assert output.parent.is_dir() and not output.exists() and not output.is_symlink(), 'Fresh admitted output required'
    started=time.monotonic()
    shared,byid,bysid,byowner,cells,currentbyid,scoped=prepare()
    prospective_admission(shared)
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
        assert len(data['features'])==product['feature_count']
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
        inventories.append(dict(family=family,features=len(featureids),advertised_features=product['advertised_feature_count'],retained_minus_advertised=len(featureids)-product['advertised_feature_count'],invalid_geometries=invalid,represented_year=product['source_represented_year_claim'],license=product['recorded_license'],original_sha256=SHA(raw)))
    assert sum(x['features'] for x in inventories)==sum(products[f]['feature_count'] for f in FAMILIES)
    mismatches=[dict(x=c['x'],y=c['y'],expected=c['sids'],actual=sorted(a)) for c,a in zip(cells,actual) if a!=set(c['sids'])]
    # Keep contradictions as a failed result with exact witness cells.
    mismatch_points={(c['x'],c['y']) for c in mismatches}
    refpath='data/retained-geographic-sources/namibia/natural-earth-reference-countries.geojson.gz'
    refraw=read(refpath);pins=jread('data/sources.json');assert SHA(refraw)==pins['hashes']['ne_10m_admin_0_countries']
    refs=json.loads(refraw)['features'];unique([dict(id=f['properties']['ADM0_A3']) for f in refs],'id')
    for c in cells:c['reference_countries']=[];c['reference_contains']=[];c['reference_boundary']=[];c['current_members']=[];c['current_contains']=[];c['current_boundary']=[];c['current_holes']=[];c['source_holes']=[]
    for f in refs:
        code=f['properties']['ADM0_A3'];g=shape(f['geometry']);hits=shapely.covers(g,points);inside=shapely.contains(g,points)
        if np.any(hits):assert g.is_valid
        for i in np.flatnonzero(hits):
            cells[i]['reference_countries'].append(code)
            if inside[i]:cells[i]['reference_contains'].append(code)
            if not inside[i]:cells[i]['reference_boundary'].append(code)
    target_summary=[]
    for owner,ident in OWNERS.items():
        current=shape(currentbyid[ident]['geometry']);source=target_geometries[ident]
        assert current.is_valid and source.is_valid
        hits=shapely.covers(current,points);inside=shapely.contains(current,points)
        source_hits=shapely.covers(source,points);source_inside=shapely.contains(source,points)
        for i in np.flatnonzero(hits):
            cells[i]['current_members'].append(owner)
            if inside[i]:cells[i]['current_contains'].append(owner)
            else:cells[i]['current_boundary'].append(owner)
        holes={}
        for label,g in [('current',current),('source',source)]:
            rings=[ring for poly in ([g] if g.geom_type=='Polygon' else g.geoms) for ring in poly.interiors];holes[label]=len(rings)
            for ring in rings:
                for i in np.flatnonzero(shapely.covers(Polygon(ring),points)):cells[i][label+'_holes'].append(owner)
        target_summary.append(dict(owner=owner,id=ident,name=byowner[owner]['name'],province_id=byowner[owner]['province_id'],holes=holes,current_geometry_sha256=SHA(json.dumps(currentbyid[ident]['geometry'],separators=(',',':')).encode()),current_covers_candidate_cells=int(np.sum(hits)),current_contains_candidate_cells=int(np.sum(inside)),source_covers_candidate_cells=int(np.sum(source_hits)),source_contains_candidate_cells=int(np.sum(source_inside)),current_properties=currentbyid[ident]['properties']))
    counts=collections.Counter()
    for i,c in enumerate(cells):
        c['source_boundary_sids']=sorted(boundary[i]);c['foreign_source_sids']=[sid for sid in c['sids'] if not bysid[sid]['source_id'].startswith('gb:MMR:')]
        c['foreign_reference_countries']=[code for code in c['reference_countries'] if code!='MMR']
        reasons=[]
        if (c['x'],c['y']) in mismatch_points:reasons.append('source-membership-mismatch')
        if any(ident in json.dumps(scoped['location_changes']) for ident in [OWNERS[o] for o in c['owners'] if o in OWNERS]):reasons.append('location-change-review')
        if len(c['owners'])!=1:reasons.append('source-owner-conflict')
        if c['physical']=='source-relative':reasons.append('physical-interpretation')
        if c['foreign_source_sids']:reasons.append('foreign-source-coverage')
        if c['foreign_reference_countries']:reasons.append('foreign-reference-coverage')
        if set(c['owners']).intersection(c['current_holes']):reasons.append('current-interior-hole')
        if set(c['owners']).intersection(c['source_holes']):reasons.append('source-interior-hole')
        if c['source_boundary_sids'] or c['reference_boundary'] or set(c['owners']).intersection(c['current_boundary']):reasons.append('boundary-point')
        c['qualification_flags']=reasons
        counts[tuple(c['owners']),tuple(reasons)]+=1
    result=dict(version=1,kind='exploratory-ayeyarwady-source-qualification',status='failed' if mismatches else 'measured',base_commit=BASE,runtime=dict(shapely=shapely.__version__,geos=shapely.geos_version_string,seconds=time.monotonic()-started),candidate_cells=len(cells),complete_families=inventories,covering_sources=members,source_membership_mismatches=mismatches,targets=target_summary,decisions=scoped,reference_country_features=len(refs),complete_parent_localities=PROVINCES,expected_complete_family_features=sum(products[f]['feature_count'] for f in FAMILIES),counts=[dict(owners=k[0],flags=k[1],cells=v) for k,v in sorted(counts.items())],cells=cells,inputs=list(INPUTS.values()),limits=['Read-only exploratory source qualification; no native patch, repaired cells or territorial approval.','Current owner-zero applicability is established separately by lead current cumulative-patch subtraction.','Physical class labels authenticate queue masks; no new original GSHHG reproduction is performed.','Country-reference membership is a display convention, not sovereignty adjudication.','Complete eleven-family check does not claim a fresh worldwide source scan.','Unflagged cells still need accepted producer admission and selected-native conservation.'])
    # Exclusive creation avoids replacing retained evidence, including symlink targets.
    payload=json.dumps(result,indent=2)+'\n'
    assert len(payload.encode()) <= 32*1024*1024, 'Ordinary output limit'
    with output.open('x') as stream:stream.write(payload)
    print(json.dumps(dict(status=result['status'],output=str(output),sha256=SHA(output.read_bytes()),cells=len(cells),flag_counts=result['counts'],seconds=result['runtime']['seconds'],input_raw_plus_decoded_bytes=sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values()))))
    return 1 if mismatches else 0

if __name__=='__main__':
    if sys.argv[1:] == ['--preflight']:
        shared,*_=prepare();admission=prospective_admission(shared);print(json.dumps(dict(preflight='passed',inputs=len(INPUTS),input_raw_plus_decoded_bytes=sum(x['bytes']+x['decoded_bytes'] for x in INPUTS.values()),admission=admission,gis_executed=False)))
    else:
        assert len(sys.argv)==2, 'Output path required'
        sys.exit(run(Path(sys.argv[1])))
