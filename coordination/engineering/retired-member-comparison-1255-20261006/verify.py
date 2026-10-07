"""Whole-byte, full-roster and complete numerical-pointset verifier for issue1255."""
import argparse,collections,gzip,json,pathlib,sys
from shapely import union_all
from shapely.geometry import shape
P=pathlib.Path(__file__).resolve().parent;R=P.parents[2];sys.path.insert(0,str(R/'scripts'))
from evidence.immutable import canonical_json as canon
from reader import SHA


def read_pin(root,pin):
    p=root/pin['path']
    if p.is_symlink()or not p.is_file():raise ValueError('Missing ordinary scientific output')
    b=p.read_bytes()
    if len(b)!=pin['bytes']or SHA(b)!=pin['sha256']or len(b)>32*1024*1024:raise ValueError('Changed scientific output bytes')
    raw=gzip.decompress(b)if 'decoded_sha256'in pin else b
    if len(raw)>32*1024*1024:raise ValueError('Oversized decoded ordinary scientific output')
    if 'decoded_sha256'in pin and(len(raw)!=pin['decoded_bytes']or SHA(raw)!=pin['decoded_sha256']):raise ValueError('Changed decoded scientific output')
    return json.loads(raw)


def verify(run):
    scope=json.loads(gzip.decompress((P/'scope.json.gz').read_bytes()));report=json.loads((run/'report.json').read_bytes());idx=read_pin(run,report['object_index']);objects={}
    for pin in idx['shards']:
        rows=read_pin(run,pin)
        if len(rows)!=pin['records']:raise ValueError('Object shard count differs')
        for row in rows:
            if row['id']in objects or SHA(canon(row['geometry']))!=row['id']:raise ValueError('Duplicate/changed full object')
            objects[row['id']]=row['geometry']
    for h,entry in idx['objects'].items():
        if entry['codec']=='canonical-json-exact-byte-fragments':
            parts=[];offset=0
            for pin in entry['parts']:
                if pin['offset']!=offset:raise ValueError('Missing/reordered complete object fragment')
                b=(run/pin['path']).read_bytes();raw=gzip.decompress(b)
                if len(b)!=pin['bytes']or SHA(b)!=pin['sha256']or len(raw)!=pin['decoded_bytes']or SHA(raw)!=pin['decoded_sha256']or len(raw)>32*1024*1024:raise ValueError('Changed object fragment')
                parts.append(raw);offset+=len(raw)
            body=b''.join(parts)
            if len(body)!=entry['canonical_bytes']or SHA(body)!=h:raise ValueError('Whole object reconstruction differs')
            if h in objects:raise ValueError('Duplicate object')
            objects[h]=json.loads(body)
        elif entry['codec']!='canonical-json-object-in-indexed-shard':raise ValueError('Unsupported pointset object codec')
    if set(objects)!=set(idx['objects']):raise ValueError('Incomplete whole object index')
    for h,g in objects.items():
        if len(canon(g))!=idx['objects'][h]['canonical_bytes']or SHA(canon(g))!=h:raise ValueError('Full canonical object mismatch')
    def pointset(p):
        ref=p['geometry_reference']
        if ref['object_index']!='objects.json' or ref['canonical_geometry_sha256']not in objects:raise ValueError('Missing full pointset reference')
        g=shape(objects[ref['canonical_geometry_sha256']])
        if (g.geom_type,g.is_empty,g.is_valid,g.area,g.length)!=(p['geometry_type'],p['is_empty'],p['is_valid'],p['planar_area_coordinate_units_squared'],p['planar_length_coordinate_units']):raise ValueError('Pointset metadata differs from complete geometry')
        return g
    families={}
    for pin in report['family_outputs']:
        rows=read_pin(run,pin)
        if len(rows)!=pin['records']:raise ValueError('Family shard count differs')
        for f in rows:
            fid=f['family']['id']
            if fid in families:raise ValueError('Duplicate family scientific row')
            families[fid]=f
            d=f['literal_member_union']
            if 'union'in d:pointset(d['union'])
    if sorted(families)!=scope['family_ids']:raise ValueError('Whole scientific family roster differs')
    rows={};counts=collections.Counter();per_family=collections.defaultdict(collections.Counter)
    for pin in report['component_outputs']:
        values=read_pin(run,pin)
        if len(values)!=pin['records']:raise ValueError('Component shard count differs')
        for row in values:
            i=row['component'];fid=row['family']
            if i in rows or fid not in families or i not in families[fid]['family']['component_ids']:raise ValueError('Duplicate/lost/reassigned component')
            if row['complete_member_ids']!=families[fid]['complete_original_member_ids']or row['source_union_reference']!=families[fid]['literal_member_union']:raise ValueError('Whole member/union relation differs')
            if row['physical_status']!='unverified'or row['administrative_assignment']is not None or row['cause_status']!='unknown'or row['historical_stage_identity']!='unverified':raise ValueError('Unknown source/physical authority promoted')
            if 'intersection'in row:pointset(row['intersection'])
            if 'difference'in row:pointset(row['difference'])
            rows[i]=row;counts[row['status']]+=1;per_family[fid][row['status']]+=1
    if sorted(rows)!=scope['component_ids']or len(rows)!=20032 or len(families)!=2476 or dict(counts)!=report['counts']:raise ValueError('Complete scientific scope/counts differ')
    for fid,f in families.items():
        if dict(per_family[fid])!=f['counts']or len(f['family']['component_ids'])!=f['family']['component_count']:raise ValueError('Family complete status totals differ')
    # Original full feature/member pins bind the literal input geometry; this
    # verifier reads every containing ordinary frozen alias, not hash-only refs.
    from reader import Inputs,validate_pointsets
    inp=Inputs(R,report['code_commit'],str(P.relative_to(R)));index=json.loads(inp.read('input-index.json'));archive=inp.archive(index);members={r['id']:r for r in archive['locations']};featurepins={r['id']:r for r in scope['existing_current_component_and_member_pins']};features={};wanted=set(rows)
    M='79ffb2ed04702e16f009e4675a8d74ef9bd09d4f';S='7c7cdf2388e0e7200b937c2cfb440b53165d9d98';ir=inp.original(M,'coordination/engineering/worldwide-inventory-1164-20261006/run-one/report.json',index)
    for pin in ir['complete_products']['components']:
        path=next(p['path']for p in ir['source_descriptors']if p['sha256']==pin['sha256'])
        for f in inp.original(M,path,index)['features']:
            if f['id']in wanted:features[f['id']]=f
    delta=inp.original(S,'coordination/engineering/worldwide-successor-1215-20261006/run-one/components-delta.json.gz',index)
    if set(delta['removed_ids'])&wanted:raise ValueError('Removed component in scientific results')
    for f in delta['upsert_records']:
        if f['id']in wanted:features[f['id']]=f
    if set(features)!=wanted:raise ValueError('Missing full original/current pointsets')
    validate_pointsets(scope,features,members)
    for i,r in rows.items():
        if r['component_full_feature_sha256']!=featurepins[i]['canonical_feature_sha256']or r['component_geometry_sha256']!=featurepins[i]['geometry_sha256']:raise ValueError('Unknown-row full feature pins changed')
    union_cache={};measured=0
    for fid,f in families.items():
        mids=tuple(f['complete_original_member_ids']);d=f['literal_member_union']
        if d['status']!='literal-original-member-union':continue
        if mids not in union_cache:
            gs=[shape(members[i]['geometry'])for i in mids]
            if any(not g.is_valid or g.is_empty or g.geom_type not in ('Polygon','MultiPolygon')for g in gs):raise ValueError('Invalid original input promoted to union')
            union_cache[mids]=union_all(gs)
        u=union_cache[mids];stored=pointset(d['union'])
        if canon(objects[d['union']['geometry_reference']['canonical_geometry_sha256']])!=canon(__import__('shapely').geometry.mapping(u)):raise ValueError('Full literal union pointset differs')
        for i in f['family']['component_ids']:
            r=rows[i];g=shape(features[i]['geometry'])
            if SHA(canon(features[i]))!=featurepins[i]['canonical_feature_sha256']or SHA(canon(features[i]['geometry']))!=r['component_geometry_sha256']:raise ValueError('Complete original feature binding differs')
            if 'intersection'in r:
                ix=g.intersection(u);sg=objects[r['intersection']['geometry_reference']['canonical_geometry_sha256']]
                if canon(sg)!=canon(__import__('shapely').geometry.mapping(ix)):raise ValueError('Full intersection pointset differs')
            if 'difference'in r:
                diff=g.difference(u);sg=objects[r['difference']['geometry_reference']['canonical_geometry_sha256']]
                if canon(sg)!=canon(__import__('shapely').geometry.mapping(diff)):raise ValueError('Full difference pointset differs')
            if 'partition_equals_original'in r:
                same=union_all([g.intersection(u),g.difference(u)]).equals(g)
                if same!=r['partition_equals_original']:raise ValueError('Numerical consistency unknown was changed')
            measured+=1
    inp.close()
    scientific=sorted((str(p.relative_to(run)),SHA(p.read_bytes()))for p in run.rglob('*')if p.is_file()and p.name not in ('checkpoint.json',))
    return {'status':'passed-complete-whole-record-and-pointset-readback','complete_components':len(rows),'complete_families':len(families),'full_comparison_pointsets_replayed':measured,'counts':dict(counts),'scientific_product_sha256':SHA(canon(scientific)),'scientific_files':scientific,'limits':['Full numerical diagnostic readback is not a third counted producer execution or factual source approval.']}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--run',required=True);a.add_argument('--output',required=True);x=a.parse_args();v=verify(pathlib.Path(x.run));p=pathlib.Path(x.output);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(canon(v));print(json.dumps({k:v[k]for k in ['status','complete_components','complete_families','full_comparison_pointsets_replayed','scientific_product_sha256']}))
