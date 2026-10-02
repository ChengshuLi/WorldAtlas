"""Remove duplicate source layers and partition shared display coverage.

This is a documented map-rendering convention, not a sovereignty adjudication.
All cuts follow an existing source edge or the Natural Earth reference border.
"""
import hashlib, json, pathlib
from shapely import STRtree, make_valid, union_all
from shapely.geometry import shape, mapping, Polygon
ROOT=pathlib.Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; CACHE=ROOT/'.cache'
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
def polygonal(g):
    if g.is_empty:return Polygon()
    if g.geom_type in ('Polygon','MultiPolygon'):return g
    return union_all([polygonal(p) for p in getattr(g,'geoms',[])])
parts=read(DATA/'world-index.json')['parts']; collections={p:read(DATA/p) for p in parts}
features=[f for c in collections.values() for f in c['features']]
if features and all(f['properties']['metadata'].get('topology_version')==1 for f in features):
    print('Topology already reconciled. Regenerate source geography to rebuild.');raise SystemExit
original={f['id']:f for f in features}
write(CACHE/'topology-input.geojson',{'type':'FeatureCollection','features':features})
ref=read(CACHE/'ne_10m_admin_0_countries.json')['features'];masks={}; by_code={}
for f in ref:
    p=f['properties'];g=polygonal(make_valid(shape(f['geometry'])));by_code[p['ADM0_A3']]=g
    for key in (p['ADMIN'],p['ADM0_A3'],p['ISO_A3_EH']):
        if key and key!='-99':masks[key]=g
aliases={'XKX':'KOS','Somalia':'SOM','Russian Federation':'RUS'}

def iso(f):
    s=f['properties']['metadata']['source_id']
    return s.split(':')[1] if s.startswith('gb:') else f['id'].split('-')[0].replace('+00?','')
def mask(f):
    code=iso(f);return masks.get(aliases.get(code,code),masks.get(f['properties']['reference_owner'],Polygon()))

retired=[];kept=[]
for f in features:
    code=iso(f);g=shape(f['geometry']); reason=None
    # Country collections include overseas/SAR subdivisions that also have a
    # dedicated layer. Keep a single chosen collection for each territory.
    destinations={'CHN':['HKG','MAC','TWN'],'USA':['PRI','GUM','VIR']}.get(code,[])
    for territory in destinations:
        if g.intersection(by_code[territory]).area/g.area>.5:
            reason=f'Duplicate {territory} coverage in {code} collection; dedicated territory layer retained';break
    if code=='KOS' and any(iso(x)=='XKX' for x in features):reason='Duplicate Kosovo fallback caused by KOS/XKX code alias; gbOpen collection retained'
    if reason:retired.append({'id':f['id'],'name':f['properties']['name'],'reason':reason})
    else:kept.append(f)
features=kept;geoms=[shape(f['geometry']) for f in features];source_geoms=geoms.copy();tree=STRtree(geoms)
priorities=[(g.area,f['id']) for g,f in zip(geoms,features)]
reference=[mask(f) for f in features];changes={};pairs=0;max_loss=0
for i,original_geometry in enumerate(source_geoms):
    for j in tree.query(original_geometry,predicate='intersects'):
        j=int(j)
        if j<=i or geoms[i].is_empty or geoms[j].is_empty:continue
        a,b=geoms[i],geoms[j];shared=polygonal(a.intersection(b))
        if shared.area<=1e-10:continue
        pairs+=1
        # Split only the intersection; never clip non-overlapping coastlines.
        own_a=polygonal(shared.intersection(reference[i]))
        own_b=polygonal(shared.intersection(reference[j]))
        exclusive_a=polygonal(own_a.difference(own_b))
        exclusive_b=polygonal(own_b.difference(own_a))
        rest=polygonal(shared.difference(union_all([exclusive_a,exclusive_b])))
        if priorities[i]<priorities[j]: exclusive_a=union_all([exclusive_a,rest])
        else:exclusive_b=union_all([exclusive_b,rest])
        next_a=polygonal(make_valid(a.difference(exclusive_b)))
        next_b=polygonal(make_valid(b.difference(exclusive_a)))
        # The two output polygons must cover exactly the same union as before.
        loss=abs((a.area+b.area-shared.area)-(next_a.area+next_b.area-next_a.intersection(next_b).area))
        assert loss<1e-8,(features[i]['id'],features[j]['id'],loss)
        max_loss=max(max_loss,loss)
        geoms[i],geoms[j]=next_a,next_b
        for index in (i,j):changes[index]=changes.get(index,0)+1
    if i%5000==0:print(f'Reconciled {i}/{len(features)} locations; {pairs} shared interiors',flush=True)

active=[]
for i,(f,g) in enumerate(zip(features,geoms)):
    if g.is_empty or g.area<=1e-14:
        retired.append({'id':f['id'],'name':f['properties']['name'],'reason':'Entire display footprint already represented by retained source polygons'});continue
    assert g.is_valid and g.geom_type in ('Polygon','MultiPolygon'),f['id']
    m=f['properties']['metadata'];m['topology_version']=1
    if i in changes:
        m['topology_reconciled']=True;m['topology_conflicts']=changes[i]
        m['topology_note']='Shared display coverage reconciled against Natural Earth reference borders, then finer source geometry. Original source boundaries may differ.'
        m['original_geometry_sha256']=hashlib.sha256(json.dumps(f['geometry'],sort_keys=True).encode()).hexdigest()
        m['representative_point']=list(g.representative_point().coords)[0]
    if iso(f)=='HKG':m['search_aliases']=['Hong Kong','Hongkong','Xianggang','香港']
    f['geometry']=mapping(g);active.append(f)
# Validate the FINAL geometry, including intersections created at triple junctions.
final=[shape(f['geometry']) for f in active]
# Recheck every final pair. Resolve remaining shared coverage by the documented
# finer-polygon tie rule; any numerical clearance must preserve the union within tolerance.
residual_repairs=[]
for attempt in range(3):
    final_tree=STRtree(final);remaining=[]
    for i,g in enumerate(final):
        for j in final_tree.query(g,predicate='intersects'):
            j=int(j)
            if j>i and final[i].intersection(final[j]).area>1e-10:remaining.append((i,j))
    if not remaining:break
    for i,j in remaining:
        shared=final[i].intersection(final[j])
        loser,winner=(j,i) if (final[i].area,active[i]['id'])<(final[j].area,active[j]['id']) else (i,j)
        old=final[loser];final[loser]=polygonal(make_valid(old.difference(final[winner])))
        if final[loser].intersection(final[winner]).area>1e-10:
            final[loser]=polygonal(make_valid(old.difference(final[winner].buffer(1e-10))))
        assert abs(old.union(final[winner]).area-final[loser].union(final[winner]).area)<1e-7
        active[loser]['geometry']=mapping(final[loser]);active[loser]['properties']['metadata']['residual_overlap_repair']=True
        residual_repairs.append({'id':active[loser]['id'],'area_degrees2':old.area-final[loser].area})
else:raise AssertionError(remaining)
active_ids={f['id'] for f in active}
for part,c in collections.items():c['features']=[f for f in c['features'] if f['id'] in active_ids];write(DATA/part,c)
units=read(DATA/'hierarchy.json');lookup={u['id']:u for u in units};used=set()
for f in active:
    p=f['properties']['parent_id']
    while p:used.add(p);p=lookup[p]['parent_id']
units=[u for u in units if u['id'] in used];write(DATA/'hierarchy.json',units)
report={'residual_repairs':residual_repairs,'version':1,'input_locations':len(original),'active_locations':len(active),'retired':retired,'resolved_pairs':pairs,'adjusted_locations':len(changes),'remaining_overlap_pairs':len(remaining),'overlap_tolerance_square_degrees':1e-10,'max_pair_coverage_area_error':max_loss,'policy':'Dedicated territory collection replaces duplicate parent-country coverage. Shared interiors follow Natural Earth ADM0 reference borders where unambiguous; remaining shared coverage uses finer original polygon, then stable ID. This is a display partition, not a sovereignty determination. Non-overlapping coverage is preserved after explicit duplicate retirement.'}
write(DATA/'topology-report.json',report)
h=read(DATA/'hierarchy-report.json');h['locations']=len(active);h['counts']={level:sum(u['level']==level for u in units) for level in h['counts']};h['whole_territory_units']=[u for u in h['whole_territory_units'] if u['id'] in used];h['low_overlap_matches']=[m for m in h.get('low_overlap_matches',[]) if m['location_id'] in active_ids];write(DATA/'hierarchy-report.json',h)
print(json.dumps({k:v for k,v in report.items() if k not in ('retired','policy')}));print('Retired',len(retired))
