"""Deterministic exact source-relative overlays for the bounded Japan roster."""
import gzip, hashlib, json, pathlib, zipfile, sys
from collections import Counter
from shapely.geometry import shape, mapping
from shapely.strtree import STRtree
from shapely.ops import transform
from pyproj import Transformer
from mlit_shapefile import iter_features
from restore_mlit_source import restore

ROOT=pathlib.Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]
PACKET='research/geography/japan-nine-gap-family-source-fitness-20261007'
CORPUS=REPO/'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json'
SCOPE=json.loads((ROOT/'inputs/immutable-scope-and-inputs.json').read_bytes())

def sha(b): return hashlib.sha256(b).hexdigest()
def sha_path(p):
    h=hashlib.sha256();n=0
    with pathlib.Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block);n+=len(block)
    return n,h.hexdigest()
def canon(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()+b'\n'
def geom_hash(g): return sha(canon(g))
def safe_read(path):
    b=path.read_bytes()
    if len(b)>33554432: raise ValueError('ordinary input bound exceeded')
    return b

def verify_body(raw, expected_size, expected_sha, label):
    if len(raw)!=expected_size or sha(raw)!=expected_sha:
        raise ValueError(f'{label} source bytes differ')
    return raw

def feature_roster(rows):
    d={}
    for f in rows:
        k=f['properties'].get('shapeID')
        if not isinstance(k,str) or not k or k in d:raise ValueError('duplicate/missing geoBoundaries shapeID')
        d[k]=f
    return d

def verify_gb_metadata(metadata):
    if (metadata.get('boundaryID')!='JPN-ADM2-22064153' or metadata.get('boundaryYear')!='2017' or
        metadata.get('boundaryCanonical')!='Subprefectures' or metadata.get('boundarySource')!='OpenStreetMap, Wambacher' or
        metadata.get('boundaryLicense')!='Creative Commons Attribution-ShareAlike 2.0'):
        raise ValueError('geoBoundaries source metadata identity, role, vintage or recorded license differs')
    return True

def validate_target_roster(rows):
    expected=set(SCOPE['components'])|set(SCOPE['contacts'])
    ids=[x['id'] for x in rows]
    if len(ids)!=49 or len(set(ids))!=49 or set(ids)!=expected:
        raise ValueError('omitted, duplicate, foreign or incomplete whole-target roster')
    return True

def validate_target_features(component_features, contact_features):
    rows=[{'id':f['id']} for f in component_features+contact_features]
    validate_target_roster(rows)
    route={r['component']:r for r in SCOPE['routing_rows']}
    if set(route)!=set(SCOPE['components']):raise ValueError('routing target identity roster differs')
    for f in component_features:
        r=route[f['id']]
        if geom_hash(f['geometry'])!=r['current_geometry_sha256'] or sha(canon(f))!=r['current_feature_sha256']:
            raise ValueError('whole candidate geometry/context differs from routed identity')
    expected=set(SCOPE['contacts'])
    if {f['id'] for f in contact_features}!=expected:raise ValueError('whole contact geometry roster differs')
    return True

def load_gb():
    full_raw=safe_read(ROOT/'sources/geoboundaries/full-product.geojson')
    full_pointer={a:b for a,b in (x.split(' ',1) for x in (ROOT/'sources/geoboundaries/full-product.pointer').read_text().splitlines())}
    verify_body(full_raw,int(full_pointer['size']),full_pointer['oid'].split(':',1)[1],'full geoBoundaries')
    full=json.loads(full_raw)['features']
    cat=json.loads((REPO/'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json').read_bytes())
    product=next(x for x in cat['products'] if x['key']=='gb:JPN:ADM2')
    enc=safe_read(ROOT/'sources/geoboundaries/simplified-product.geojson.gz')
    verify_body(enc,product['parts'][0]['bytes'],product['parts'][0]['sha256'],'retained Atlas simplified product encoded')
    baseline_enc=safe_read(REPO/product['parts'][0]['path'])
    verify_body(baseline_enc,product['parts'][0]['bytes'],product['parts'][0]['sha256'],'baseline Atlas simplified product encoded')
    if baseline_enc!=enc:raise ValueError('retained simplified product is not the exact baseline consumed product')
    simpl_raw=gzip.decompress(enc)
    if len(simpl_raw)!=product['original_bytes'] or sha(simpl_raw)!=product['original_sha256']:raise ValueError('Atlas simplified product body differs')
    simpl_pointer={a:b for a,b in (x.split(' ',1) for x in (ROOT/'sources/geoboundaries/simplified-product.pointer').read_text().splitlines())}
    if int(simpl_pointer['size'])!=len(simpl_raw) or simpl_pointer['oid']!='sha256:'+sha(simpl_raw):raise ValueError('simplified upstream LFS body differs')
    simpl=json.loads(simpl_raw)['features']
    metadata_raw=safe_read(ROOT/'sources/geoboundaries/metadata.json')
    metadata=json.loads(metadata_raw)
    verify_gb_metadata(metadata)
    metadata_pointer={a:b for a,b in (x.split(' ',1) for x in (ROOT/'sources/geoboundaries/metadata.pointer').read_text().splitlines())}
    verify_body(metadata_raw,int(metadata_pointer['size']),metadata_pointer['oid'].split(':',1)[1],'geoBoundaries metadata')
    full_d=feature_roster(full);simpl_d=feature_roster(simpl)
    if set(full_d)!=set(simpl_d):raise ValueError('full/simplified source rosters differ')
    return [('geoboundaries-full',full_d,sha(full_raw)),('geoboundaries-atlas-simplified',simpl_d,sha(simpl_raw))]

def metric(target, source, source_id, source_record, product):
    base={'source_product':product,'source_id':source_id,'source_record':source_record,
          'source_geometry_sha256':geom_hash(mapping(source)), 'bbox_candidate':True}
    if target.is_empty or source.is_empty:
        base.update(predicate_status='empty-geometry-unresolved',intersects=None,covers=None,intersection_area_degrees2=None,intersection_geometry_sha256=None)
        return base
    if not target.is_valid or not source.is_valid:
        base.update(predicate_status='invalid-geometry-unresolved',intersects=None,covers=None,intersection_area_degrees2=None,intersection_geometry_sha256=None)
        return base
    intersects=bool(target.intersects(source)); covers=bool(source.covers(target))
    inter=target.intersection(source)
    base.update(predicate_status='exact-predicates',intersects=intersects,source_covers_target=covers,target_covers_source=bool(target.covers(source)),equal=bool(target.equals(source)),
                intersection_area_degrees2=float(inter.area),
                intersection_geometry_sha256=geom_hash(mapping(inter)),
                target_area_degrees2=float(target.area),
                intersection_over_target_fraction=(float(inter.area/target.area) if target.area>0 else None))
    return base

def main(outpath):
    source_summaries=[]
    targets=[]
    for kind,items in [('component',SCOPE['full_candidate_features']),('contact',SCOPE['full_current_contact_features'])]:
        for f in items:
            g=shape(f['geometry'])
            if g.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('nonpolygon scoped target')
            targets.append({'kind':kind,'id':f['id'],'geometry':g,'geometry_json':f['geometry'],'geometry_sha256':geom_hash(f['geometry'])})
    validate_target_features(SCOPE['full_candidate_features'],SCOPE['full_current_contact_features'])
    targets.sort(key=lambda x:(x['kind'],x['id']))
    if len([t for t in targets if t['kind']=='component'])!=28 or len([t for t in targets if t['kind']=='contact'])!=21:raise ValueError('target roster differs')
    gb=load_gb(); products=[]; identity_bindings=[]
    for name,features,bodysha in gb:
        rows=[];geoms=[];ids=[];target_counts=[]
        for sid,f in sorted(features.items()):
            g=shape(f['geometry'])
            if g.geom_type not in ('Polygon','MultiPolygon'):raise ValueError('nonpolygon geoBoundaries source')
            if not g.is_empty: rows.append(f);geoms.append(g);ids.append(sid)
        tree=STRtree(geoms)
        counts=Counter();
        for t in targets:
            if t['kind']=='contact':
                sid=t['id'].rsplit(':',1)[-1]
                if sid not in features:raise ValueError('scoped contact shapeID missing from source product')
                f=features[sid]; source_geom=shape(f['geometry'])
                direct=metric(t['geometry'],source_geom,sid,{'shapeName':f['properties'].get('shapeName')},name)
                direct.update(target_kind='contact',target_id=t['id'],target_geometry_sha256=t['geometry_sha256'],binding='exact-contact-shapeID')
                identity_bindings.append(direct)
            selected=sorted(int(i) for i in tree.query(t['geometry']) if True)
            exact_count=0
            for i in selected:
                f=rows[i]; sid=ids[i];counts['spatial_intersection_candidates']+=1
                m=metric(t['geometry'],geoms[i],sid,{'shapeName':f['properties'].get('shapeName')},name)
                if m.get('intersects') is True:exact_count+=1
                m.update(target_kind=t['kind'],target_id=t['id'],target_geometry_sha256=t['geometry_sha256'])
                products.append(m)
            target_counts.append({'target_kind':t['kind'],'target_id':t['id'],'bbox_candidate_count':len(selected),'exact_intersection_count':exact_count})
        # Bind all source features and roster, not only intersections.
        counts.update({'source_features':len(rows),'source_feature_roster_sha256':sha(canon(ids)),'source_body_sha256':bodysha})
        counts['source_invalid_geometry_count']=sum(not g.is_valid for g in geoms)
        counts['source_empty_geometry_count']=sum(g.is_empty for g in geoms)
        # Same-ID contact bindings are exact identity evidence even if geometry does not intersect after the tree predicate.
        counts['scoped_contact_same_shapeID_count']=sum(t['kind']=='contact' and t['id'].rsplit(':',1)[-1] in features for t in targets)
        source_summaries.append({'source_product':name,'target_count':len(targets),'per_target_exact_intersections':target_counts,**counts})
    # Restore-only source exceeds the ordinary per-file custody limit. The
    # complete local archive is hashed as one body before any member is read.
    zpath,manifest=restore()
    length,archive_sha=sha_path(zpath)
    if archive_sha!=manifest['archive_sha256'] or length!=manifest['http_content_length']:raise ValueError('complete restored N03 archive differs')
    tr=Transformer.from_crs('EPSG:4326','EPSG:6668',always_xy=True)
    targets_j=[{**t,'geometry_jgd2011':transform(tr.transform,t['geometry'])} for t in targets]
    bounds=[t['geometry_jgd2011'].bounds for t in targets_j]
    z=zipfile.ZipFile(zpath)
    n03=[]; n03_errors=0; code_roster=set(); blanks=0; source_reader_receipt={}
    for f in iter_features(z,check_validity=False,query_bounds=bounds,reader_receipt=source_reader_receipt):
        code=f['properties'].get('N03_007')
        if code is None:blanks+=1
        else:code_roster.add(code)
        if f['geometry'] is None or f['geometry_errors']:
            n03_errors+=1; continue
        if f['geometry'].is_empty: continue
        n03.append(f)
    z.close()
    if source_reader_receipt.get('shp_record_count')!=116024 or source_reader_receipt.get('dbf_record_count')!=116024:raise ValueError('N03 SHP/DBF complete source count differs')
    n03_geoms=[f['geometry'] for f in n03]
    tree=STRtree(n03_geoms) if n03_geoms else None
    n03_intersections=0; invalid_pairs=0
    target_counts=[]
    for t in targets_j:
        selected=sorted(int(i) for i in tree.query(t['geometry_jgd2011']) if True)
        target_counts.append({'target_kind':t['kind'],'target_id':t['id'],'bbox_selected_source_records':len(selected)})
        for i in selected:
            src=n03[i]; sg=src['geometry']
            if not t['geometry_jgd2011'].bounds[0]<=sg.bounds[2] or not t['geometry_jgd2011'].bounds[2]>=sg.bounds[0] or not t['geometry_jgd2011'].bounds[1]<=sg.bounds[3] or not t['geometry_jgd2011'].bounds[3]>=sg.bounds[1]:raise ValueError('STRtree returned non-bbox source row')
            if not t['geometry_jgd2011'].is_valid or not sg.is_valid: invalid_pairs+=1
            # source and target have both been transformed into JGD2011 geographic
            m=metric(t['geometry_jgd2011'],sg,src['properties'].get('N03_007'),{'record_ordinal':src['record_ordinal'],'record_number':src['record_number'],'N03_001':src['properties'].get('N03_001'),'N03_002':src['properties'].get('N03_002'),'N03_003':src['properties'].get('N03_003'),'N03_004':src['properties'].get('N03_004')},'mlit-n03-2017')
            m.update(target_kind=t['kind'],target_id=t['id'],target_geometry_sha256=t['geometry_sha256'])
            # Source CRS is angular; never call this square metres.
            m['intersection_area_jgd2011_degrees2']=m.pop('intersection_area_degrees2')
            m.pop('target_area_degrees2',None);m.pop('intersection_over_target_fraction',None)
            products.append(m);n03_intersections+=1
    source_summaries.append({'source_product':'mlit-n03-2017','complete_archive_sha256':archive_sha,'complete_archive_bytes':length,'source_shape_records':source_reader_receipt['shp_record_count'],'source_dbf_records':source_reader_receipt['dbf_record_count'],'bbox_skipped_native_rows':source_reader_receipt['bbox_skipped_record_count'],'distinct_nonblank_N03_007_values_in_bbox_selection':len(code_roster),'blank_N03_007_rows_in_bbox_selection':blanks,'bbox_selected_native_rows':len(n03),'bbox_selected_native_invalid_rows':n03_errors,'target_count':len(targets_j),'per_target_bbox_candidates':target_counts,'spatial_intersection_candidates':n03_intersections,'invalid_geometry_pairs_unresolved':invalid_pairs,'crs':'EPSG:6668 JGD2011 geographic','transform':{'source':'EPSG:4326','target':'EPSG:6668','always_xy':True,'description':tr.description,'definition':tr.definition,'accuracy_m':tr.accuracy}})
    result={'schema':'japan-nine-gap-family-source-overlays-v1','comparison_performed':True,'targets':[{'kind':t['kind'],'id':t['id'],'geometry_sha256':t['geometry_sha256']} for t in targets],'source_summaries':source_summaries,'contact_shapeID_bindings':identity_bindings,'pairwise_exact_overlays':sorted(products,key=lambda x:(x['source_product'],x['target_kind'],x['target_id'],str(x['source_id']),json.dumps(x['source_record'],sort_keys=True,ensure_ascii=False))),'limitations':['These are source-relative overlays only; no source establishes physical truth, historical geometry, legal authority, positional accuracy or cause.','geoBoundaries represented year is a metadata claim, not a verified effective geometry date.','MLIT N03 is an administrative/coastline reference; JGD2011 transformation does not confer accuracy or legal status.','Areas use angular units in the stated geographic CRS. No square-metre inference.','No source geometry is repaired, dissolved or simplified by this producer. Invalid or empty geometries remain unresolved.']}
    raw=canon(result);pathlib.Path(outpath).write_bytes(raw)
    print(json.dumps({'targets':len(targets),'overlays':len(products),'source_summaries':source_summaries,'output_bytes':len(raw),'output_sha256':sha(raw)},ensure_ascii=False))

if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: producer.py ABSOLUTE_OUTPUT_PATH')
    main(sys.argv[1])
