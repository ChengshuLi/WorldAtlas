#!/usr/bin/env python3
"""Exact vector-footprint-to-JRC TIFF block intersections (no raster reads).

Uses rational arithmetic on source decimal coordinates and TIFF grid edges. It
checks complete Polygon/MultiPolygon rings against closed 512x512 block squares,
including holes and boundary-only contacts. No geometry is clipped and no raster
block is downloaded, decoded, or classified.
"""
import gzip, glob, json, pathlib, struct, hashlib
from fractions import Fraction as F
from decimal import Decimal
ROOT=pathlib.Path(__file__).resolve().parents[1]
CACHE=pathlib.Path(__file__).resolve().parent
OUT=CACHE/'jrc-exact-block-intersections.json'
COMPONENT_IDS={
'physical-component:04431dc98d19b4236a143d2c0bb388fed2e41d4768356cf5a74ae4b9194fd9bf','physical-component:0467413184087c1282e0b20ec7252d8dfe7e393e674b1902f9d2f8e5f10eeadd','physical-component:0bf1093e551def6fa258252e87e67ca4c4dd1a3847416a39164226514713e842','physical-component:181f705ac58d42ae49ea4d70c75df34928b7c26a46e8b7ccc30895eee2455276','physical-component:1d82eb920d887e65e0b7feace4b6ce606ba72f0dd4b64d8872bc6ff17594c52c','physical-component:29c61a4079291f4cf9fa96ca41c3561405cef2d2ad8afe80aa526904848969c2','physical-component:7450c83fcd14661b0c9115f0075f703ac96c64ea65ec0caa86702a1ef00db81e','physical-component:804dfb19fcd6f3fc68de442ae08f4ca553de8687df65d70b72dc1a3fae258eb9','physical-component:a133c2293fb153cd6628eb43b7518e55ea7db7f6c7f74178b854fd9641be86c5','physical-component:bee4ff4185a3775db6d8c51fdc2da0b0674b7629615933378147c6d0b4e778d4','physical-component:ca9c5207e4e4202ea32bd39636020e8f898783d03802fb3507efb816d2e525a3','physical-component:d461dff8a46f322a5c4d5aa7c7ddaaaee64f4c205227d09feeb3b93420f33fa8','physical-component:0b1a9310b0717d791b33e315035e22e83362b4b461283df57e6267d3d1d6c015','physical-component:658f2e100dd572e26c264f47481759420a413e73978799a8792e203637b3854b','physical-component:d76b0c2c3c68c11f128e13ad2a3528ae9bd624dedaed581e305431462cbfe7f9'}
CONTACT_SHAPES={'92254566B28866404519709','92254566B65149347501284','92254566B65536554507768','16282066B17537121350265','16282066B25952413622692','16282066B48594859138803','16282066B4928854450407','16282066B70669453487294','16282066B88100265425771'}
TILES={
'60E_40N':(60,40,2,20517553,'cb0202baa8a76a36c9087be3047525ff-1','2026-07-01T10:40:06Z'),
'70E_40N':(70,40,4,32461641,'ca3a75120e8cb7367b90bb2ff6e15d33-1','2026-07-01T10:41:04Z'),
'60E_50N':(60,50,5,63277308,'f065d7a2ab19495f4d9467028be8abb0-1','2026-07-01T10:40:25Z'),
'70E_50N':(70,50,6,38518800,'46aab89d1ff3d3fca1d87edc691588f2-1','2026-07-01T10:41:21Z')}
BLOCK=512; SCALE=F(4000) # pixels per degree from 0.00025 degree cells

def pts(c,out):
    if isinstance(c,(list,tuple)):
        if len(c)>=2 and isinstance(c[0],(int,float,Decimal)) and isinstance(c[1],(int,float,Decimal)):
            out.append((F(c[0]),F(c[1])))
        else:
            for v in c: pts(v,out)
def bbox_points(geom):
    p=[];pts(geom['coordinates'],p)
    return [min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)],len(p)
def load_decimal(path):
    return json.load(gzip.open(path,'rt'),parse_float=Decimal,parse_int=int)
def coord_ring(ring,west,north):
    return [((F(x)-F(west))*SCALE,(F(north)-F(y))*SCALE) for x,y in ring]
def orient(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def between(a,b,x): return min(a,b)<=x<=max(a,b)
def on_segment(p,a,b): return orient(a,b,p)==0 and between(a[0],b[0],p[0]) and between(a[1],b[1],p[1])
def segments_intersect(a,b,c,d):
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if o1==0 and on_segment(c,a,b): return True
    if o2==0 and on_segment(d,a,b): return True
    if o3==0 and on_segment(a,c,d): return True
    if o4==0 and on_segment(b,c,d): return True
    return ((o1<0<o2 or o2<0<o1) and (o3<0<o4 or o4<0<o3))
def inside_rect(p,x0,y0,x1,y1): return x0<=p[0]<=x1 and y0<=p[1]<=y1
def ring_touches_rect(ring,x0,y0,x1,y1):
    # Ring vertices or edges meet the closed block rectangle.
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if inside_rect(a,x0,y0,x1,y1) or inside_rect(b,x0,y0,x1,y1): return True
        if max(a[0],b[0])<x0 or min(a[0],b[0])>x1 or max(a[1],b[1])<y0 or min(a[1],b[1])>y1: continue
        corners=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        if any(segments_intersect(a,b,c,d) for c,d in zip(corners,corners[1:]+corners[:1])): return True
    return False
def point_in_ring(p,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if on_segment(p,a,b): return None
        if (a[1]>p[1]) != (b[1]>p[1]):
            xcross=a[0]+(p[1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if p[0]<xcross: inside=not inside
    return inside
def point_in_polygon(p,rings):
    ext=point_in_ring(p,rings[0])
    if ext is not True: return False
    for hole in rings[1:]:
        h=point_in_ring(p,hole)
        if h is True: return False
    return True
def geom_polygons(ft):
    g=ft['geometry']; typ=g['type']; c=g['coordinates']
    return [c] if typ=='Polygon' else c if typ=='MultiPolygon' else (_ for _ in ()).throw(ValueError(typ))
def min_block(v):
    q=v//BLOCK
    return int(q-1 if v.denominator==1 and v.numerator%BLOCK==0 else q)
def max_block(v): return int(v//BLOCK)
def geometry_hits_rect(polys,x0,y0,x1,y1):
    corners=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    for rings in polys:
        if any(ring_touches_rect(r,x0,y0,x1,y1) for r in rings): return True
        if any(point_in_polygon(p,rings) for p in corners): return True
    return False

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
# Full source geometries, without clipping. Hash every shard that contributed a selected pointset.
features=[]; pointset_hashes={}; source_refs={}
for p in sorted((ROOT/'inputs/component-pointsets').glob('*.json.gz')):
    d=load_decimal(p); selected=[f for f in d['features'] if f['id'] in COMPONENT_IDS]
    if selected:
        pointset_hashes[str(p.relative_to(ROOT))]=sha(p)
        for f in selected:
            features.append(('candidate',f['id'],f)); source_refs[f['id']]=str(p.relative_to(ROOT))
assert len(features)==15 and {ident for _,ident,_ in features}==COMPONENT_IDS
contacts=[]; contact_hashes={}
for country in ('KGZ','TJK'):
    p=ROOT/f'inputs/sources/gb-{country}-ADM2-000.bin.gz'; d=load_decimal(p)
    selected=[f for f in d['features'] if f['properties']['shapeID'] in CONTACT_SHAPES]
    if selected: contact_hashes[str(p.relative_to(ROOT))]=sha(p)
    for f in selected:
        ident='gb:'+country+':ADM2:'+f['properties']['shapeID']
        contacts.append(('contact',ident,f)); source_refs[ident]=str(p.relative_to(ROOT))
assert len(contacts)==9
# Read only retained IFD prefix metadata and complete base TileByteCounts arrays.
for name,(west,north,rid,length,etag,lm) in TILES.items():
    raw=(CACHE/f'gsw-ifd-range-{rid}.bin').read_bytes(); assert len(raw)==81328 and raw[:4]==b'II*\0'
    ifd=struct.unpack_from('<I',raw,4)[0]; count=struct.unpack_from('<H',raw,ifd)[0]; tags={}
    for i in range(count):
        tag,typ,n,val=struct.unpack_from('<HHII',raw,ifd+2+12*i)
        if tag in (324,325): tags[tag]=list(struct.unpack_from('<'+'I'*n,raw,val))
    assert len(tags[324])==len(tags[325])==6241
    assert max(o+c for o,c in zip(tags[324],tags[325]))<=length
    TILES[name]={'west':west,'north':north,'range_id':rid,'length':length,'etag':etag,'last_modified':lm,'offsets':tags[324],'bytecounts':tags[325],'sets':{'candidate':set(),'contact':set()}}
rows=[]
for group,ident,ft in features+contacts:
    bb,npts=bbox_points(ft['geometry']); xmin,ymin,xmax,ymax=bb; per={}; per_blocks={}; overall=set()
    for name,t in TILES.items():
        west,north=t['west'],t['north']; east=west+10;south=north-10
        if xmax<F(west) or xmin>F(east) or ymax<F(south) or ymin>F(north): continue
        # Transform the complete, uncut geometry into this tile's pixel coordinate frame.
        ppolys=[[coord_ring(r,west,north) for r in rings] for rings in geom_polygons(ft)]
        allx=[p[0] for rings in ppolys for ring in rings for p in ring]; ally=[p[1] for rings in ppolys for ring in rings for p in ring]
        c0=max(0,min(78,min_block(min(allx)))); c1=max(0,min(78,max_block(max(allx))))
        r0=max(0,min(78,min_block(min(ally)))); r1=max(0,min(78,max_block(max(ally))))
        hits=set()
        for br in range(r0,r1+1):
            y0=F(br*BLOCK);y1=F(min(40000,(br+1)*BLOCK))
            for bc in range(c0,c1+1):
                x0=F(bc*BLOCK);x1=F(min(40000,(bc+1)*BLOCK))
                if geometry_hits_rect(ppolys,x0,y0,x1,y1): hits.add(br*79+bc)
        t['sets'][group].update(hits);overall.update((name,i) for i in hits);per[name]=len(hits);per_blocks[name]=sorted(hits)
    props=ft['properties']
    status_snapshot=({'water_status':props.get('water_status'),'administrative_assignment':props.get('administrative_assignment'),'cause_status':'unknown','physical_authority':'unapproved','source_fitness':'unapproved-for-all-components'} if group=='candidate' else {'role':'administrative contact context only','physical_class':'unknown','rights_or_ownership':'unknown'})
    rows.append({'kind':group,'id':ident,'source_ref':source_refs[ident],'source_properties_id':ident if group=='candidate' else props.get('shapeID'),'status_snapshot':status_snapshot,'bbox_wgs84_lonlat':[str(x) for x in bb],'coordinate_pairs':npts,'exact_closed_block_intersections_by_tile':per,'exact_closed_block_indices_by_tile':per_blocks,'unique_exact_blocks_across_tiles':len(overall)})
result={'contract_sha256':'2aa9ab4ea222fc7a00668e1306c9e4be15f15de943607979605d1d91068750b3','intersection_script_sha256':sha(pathlib.Path(__file__)),
 'method':'Exact closed polygon/ring against closed 512x512 block-square intersection using rational pixel coordinates from full input decimals; includes boundary-only touches and hole boundaries; no clipping.',
 'scope':{'complete_candidate_pointsets':15,'complete_contact_features':9,'feature_count':24},
 'input_gzip_sha256':{**pointset_hashes,**contact_hashes},
 'raster_grid':{'crs':'EPSG:4326 / WGS84','pixel_area':True,'pixel_scale_degrees':[0.00025,0.00025],'dimensions':[40000,40000],'sample':'UInt8','blocks':[512,512],'tile_naming':'suffix is north edge'},
 'tiles':{},'features':rows,'limits':['No TIFF pixel blocks were read, decoded, or classified.','This is vector geometry-to-block support only; it makes no claim about any pixel value, physical class, water, ownership, boundary authority, effective date, or positional accuracy.','The polygon/block test uses the exact decimal coordinates retained in the pinned gzip sources; source geometry accuracy remains unestablished.']}
for name,t in TILES.items():
 union=sorted(t['sets']['candidate']|t['sets']['contact']); cand=sorted(t['sets']['candidate']); cont=sorted(t['sets']['contact'])
 result['tiles'][name]={'content_length_bytes':t['length'],'etag':t['etag'],'etag_is_sha256':False,'last_modified':t['last_modified'],'candidate_unique_exact_blocks':len(cand),'contact_unique_exact_blocks':len(cont),'union_unique_exact_blocks':len(union),'union_base_encoded_bytes':sum(t['bytecounts'][i] for i in union),'union_full_decoded_block_upper_bound_bytes':len(union)*BLOCK*BLOCK,'union_row_major_block_indices':union,'union_block_index_sha256':hashlib.sha256(','.join(map(str,union)).encode()).hexdigest()}
result['totals']={'unique_exact_blocks':sum(t['union_unique_exact_blocks'] for t in result['tiles'].values()),'encoded_base_block_bytes':sum(t['union_base_encoded_bytes'] for t in result['tiles'].values()),'decoded_full_block_upper_bound_bytes':sum(t['union_full_decoded_block_upper_bound_bytes'] for t in result['tiles'].values()),'candidate_contact_union_block_sum_not_global_deduped':sum(t['candidate_unique_exact_blocks']+t['contact_unique_exact_blocks'] for t in result['tiles'].values())}
OUT.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result['totals'],indent=2));print('output_sha256',sha(OUT));print('per_tile',{n:(t['union_unique_exact_blocks'],t['union_base_encoded_bytes'],t['union_full_decoded_block_upper_bound_bytes']) for n,t in result['tiles'].items()})
