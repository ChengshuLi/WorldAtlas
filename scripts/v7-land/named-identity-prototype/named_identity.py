"""Research-only corroboration: a raw named-island label contains a point.

The polygon is evidence about a point's name, NEVER a physical boundary or a
whole-component selector. The caller must pin source bytes, decision metadata,
implementation and dependencies, and independently review the physical island.
"""
import hashlib,json,math,re
HEX=re.compile(r'^[0-9a-f]{64}$')
def need(ok,msg):
    if not ok:raise ValueError(msg)
def text(v):return isinstance(v,str) and bool(v.strip())
def source_crs(data):
    if 'crs' not in data:return 'RFC7946'
    crs=data['crs'];allowed={'urn:ogc:def:crs:OGC:1.3:CRS84','urn:ogc:def:crs:OGC::CRS84','OGC:CRS84'}
    need(isinstance(crs,dict) and set(crs)=={'type','properties'} and crs['type']=='name' and isinstance(crs['properties'],dict) and set(crs['properties'])=={'name'} and crs['properties']['name'] in allowed,'unsupported or ambiguous source CRS')
    return 'OGC:CRS84'

def geom_hash(g):return hashlib.sha256(json.dumps(g,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def validate_coordinates(geom):
    typ=geom.get('type');need(typ in ('Polygon','MultiPolygon'),'polygon or multipolygon required')
    polygons=[geom.get('coordinates')] if typ=='Polygon' else geom.get('coordinates');need(isinstance(polygons,list) and polygons,'empty polygon')
    for poly in polygons:
        need(isinstance(poly,list) and poly,'empty polygon ring list')
        for ring in poly:
            need(isinstance(ring,list) and len(ring)>=4 and ring[0]==ring[-1],'invalid or open polygon ring')
            prev=None
            for point in ring:
                need(isinstance(point,list) and len(point)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in point),'2D finite coordinates required')
                x,y=point;need(-180<=x<=180 and -90<=y<=90,'polygon coordinate outside WGS84')
                if prev is not None:need(abs(x-prev)<=180,'antimeridian-crossing label unsupported')
                prev=x

def check(source,point_geometry,island_identity,spec):
    from osgeo import ogr,gdal
    ogr.UseExceptions();need(ogr.GetGEOSVersionMajor()>0,'GEOS support required')
    required={'method','identity_feature_id','identity_id_property','identity_name_property','identity_class_property','identity_class_value','identity_geometry_sha256'}
    need(isinstance(spec,dict) and set(spec)==required and spec.get('method')=='raw_named_polygon_contains_point_v1' and all(text(spec[k]) for k in required),'invalid identity selector')
    need(HEX.fullmatch(spec['identity_geometry_sha256']) and text(island_identity),'invalid identity pin')
    need(isinstance(source,dict) and source.get('type')=='FeatureCollection' and isinstance(source.get('features'),list),'identity source must be FeatureCollection');crs=source_crs(source)
    key=spec['identity_id_property'];fid=spec['identity_feature_id'];matches=[f for f in source['features'] if isinstance(f,dict) and isinstance(f.get('properties'),dict) and key in f['properties'] and type(f['properties'][key]) in (int,str) and str(f['properties'][key])==fid]
    need(len(matches)==1,'identity feature must be unique');feature=matches[0];need('crs' not in feature,'nested feature CRS unsupported');props=feature['properties'];name=props.get(spec['identity_name_property']);cls=props.get(spec['identity_class_property'])
    need(text(name) and name.casefold()==island_identity.casefold() and cls==spec['identity_class_value'],'identity feature name or class mismatch')
    geometry=feature.get('geometry');need(isinstance(geometry,dict) and 'crs' not in geometry,'nested geometry CRS unsupported');need(geom_hash(geometry)==spec['identity_geometry_sha256'],'identity geometry hash mismatch');validate_coordinates(geometry)
    need(isinstance(point_geometry,dict) and point_geometry.get('type')=='Point' and isinstance(point_geometry.get('coordinates'),list) and len(point_geometry['coordinates'])==2 and all(type(x) in (int,float) and math.isfinite(x) for x in point_geometry['coordinates']),'2D finite point required')
    x,y=point_geometry['coordinates'];need(-180<=x<180 and -90<=y<=90,'point outside WGS84')
    polygon=ogr.CreateGeometryFromJson(json.dumps(geometry,allow_nan=False));point=ogr.CreateGeometryFromJson(json.dumps(point_geometry,allow_nan=False))
    need(polygon is not None and point is not None and polygon.GetCoordinateDimension()==2 and polygon.IsValid(),'invalid identity polygon')
    need(polygon.Contains(point),'point must be strictly inside identity polygon')
    return {'method':spec['method'],'identity_feature_id':fid,'identity_feature_name':name,'identity_feature_class':cls,'identity_geometry_sha256':spec['identity_geometry_sha256'],'strict_contains':True,'identity_source_crs':crs,'gdal_version':gdal.VersionInfo('--version'),'geos_version':'.'.join(map(str,(ogr.GetGEOSVersionMajor(),ogr.GetGEOSVersionMinor(),ogr.GetGEOSVersionMicro()))),'limitation':'Generalized identity label only; not a physical boundary, exclusive island roster, or proof about the whole physical component.'}

def worker():
    """Internal isolated entry point. No decision, map or source is written."""
    import sys
    request=sys.stdin.buffer.read(65537);need(len(request)<=65536,'worker request too large');r=json.loads(request)
    path=r['identity_path'];expected=r['identity_sha256']
    with open(path,'rb') as f:raw=f.read(8*1024*1024+1)
    need(len(raw)<=8*1024*1024 and hashlib.sha256(raw).hexdigest()==expected,'identity source pin mismatch')
    result=check(json.loads(raw),r['point_geometry'],r['island_identity'],r['spec'])
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    need(h.hexdigest()==expected,'identity source changed during worker run')
    print(json.dumps({'schema':'named-identity-worker-v1','result':result,},sort_keys=True))
if __name__=='__main__':
    try:worker()
    except Exception as e:
        import sys
        print(type(e).__name__+': '+str(e),file=sys.stderr);raise SystemExit(1)
