"""Current-source inventory and WGS84 *performance hints*, never final labels.

Caller must authenticate all inputs, independently validate physical/component/seed
coverage and bind the mainland root list to the current stage-1 witness report.
"""
import math, os, sqlite3, struct
from urllib.parse import quote
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Geod

U32=struct.Struct('<I')
WGS84_A=6378137.0
WGS84_F=1/298.257223563
MIN_CURVATURE_RADIUS=WGS84_A*(1-WGS84_F*(2-WGS84_F))
BOUND_CUSHION_M=0.001
DISTANCE_BATCH=65536
GEOD=Geod(a=WGS84_A,f=WGS84_F)

def _offsets(path,height,record_bytes,run_path):
    expected=(height+1)*4
    with open(path,'rb') as f:
        if os.fstat(f.fileno()).st_size!=expected: raise ValueError('bad offset length')
        raw=f.read(expected+1)
    if len(raw)!=expected: raise ValueError('bad offset length')
    o=np.frombuffer(raw,dtype='<u4')
    size=Path(run_path).stat().st_size
    if size%record_bytes or o[0]!=0 or o[-1]!=size//record_bytes or np.any(o[1:]<o[:-1]): raise ValueError('bad offsets')
    return o

def inventory(rows,runs,seed_roots,width,height,db_path,guard=lambda:None):
    """Store first actual cell per root in fresh SQLite, excluding seeded roots."""
    if type(width)!=int or width<1 or type(height)!=int or height<1: raise ValueError('bad dimensions')
    seeds=list(seed_roots)
    if not seeds or len(seeds)!=len(set(seeds)) or any(type(x)!=int or not 0<=x<2**32-1 for x in seeds): raise ValueError('bad seed roots')
    dbpath=Path(db_path)
    fd=os.open(dbpath,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    # Caller controls the output directory and removes an incomplete DB on error.
    con=sqlite3.connect(str(dbpath)); con.execute('PRAGMA journal_mode=DELETE'); con.execute('PRAGMA synchronous=FULL')
    try:
        con.execute('CREATE TABLE roots (id INTEGER PRIMARY KEY, y INTEGER NOT NULL, x INTEGER NOT NULL)')
        o=_offsets(rows,height,12,runs)
        if np.any(o[1:].astype(np.int64)-o[:-1].astype(np.int64)>width):raise ValueError('component row exceeds width')
        seen=set();offset=0;last_row=-1;last_end=0
        with open(runs,'rb') as f:
            while True:
                guard();raw=f.read(100000*12)
                if not raw:break
                if len(raw)%12:raise ValueError('truncated component row')
                a=np.frombuffer(raw,dtype='<u4').reshape(-1,3)
                yy=np.searchsorted(o,offset+np.arange(len(a)),side='right')-1
                if (np.any(a[:,0]>=a[:,1]) or np.any(a[:,1]>width) or np.any(a[:,2]==2**32-1)
                        or np.any(yy>=height) or (yy[0]==last_row and a[0,0]<last_end)
                        or np.any((yy[1:]==yy[:-1])&(a[1:,0]<a[:-1,1]))):raise ValueError('invalid component row')
                ids,ix=np.unique(a[:,2],return_index=True)
                fresh=np.fromiter((int(root) not in seen for root in ids),dtype=bool,count=len(ids))
                ids=ids[fresh];ix=ix[fresh];seen.update(map(int,ids))
                # Every root is inserted once, rather than attempting an SQLite
                # primary-key insert for all of its later horizontal runs.
                con.executemany('INSERT INTO roots VALUES (?,?,?)',
                                ((int(root),int(yy[j]),int(a[j,0])) for root,j in zip(ids,ix)))
                offset+=len(a);last_row=int(yy[-1]);last_end=int(a[-1,1]);con.commit()
        if offset!=int(o[-1]):raise ValueError('truncated component stream')
        con.commit()
        con.execute('CREATE TABLE seed_roots (id INTEGER PRIMARY KEY)');con.executemany('INSERT INTO seed_roots VALUES (?)',((v,) for v in seeds))
        if con.execute('SELECT count(*) FROM seed_roots s LEFT JOIN roots r ON s.id=r.id WHERE r.id IS NULL').fetchone()[0]: raise ValueError('seed roots missing from physical components')
        con.executemany('DELETE FROM roots WHERE id=?',((v,) for v in seeds));con.commit()
        count=con.execute('SELECT count(*) FROM roots').fetchone()[0]
        if not count: raise ValueError('no non-seed components')
        return count
    finally: con.close()

def _xyz(lat,lon):
    a=np.deg2rad(lat);b=np.deg2rad(lon);return np.column_stack((np.cos(a)*np.cos(b),np.cos(a)*np.sin(b),np.sin(a)))

def _inverse_distances(lon1,lat1,lon2,lat2):
    if len(lon1)==1:
        return np.asarray([GEOD.inv(float(lon1[0]),float(lat1[0]),float(lon2[0]),float(lat2[0]))[2]],dtype=np.float64)
    return np.asarray(GEOD.inv(lon1,lat1,lon2,lat2)[2],dtype=np.float64)

def wgs84_nearest_distances(tree,latitudes,longitudes,query_lat,query_lon):
    """Exact WGS84 minima after a conservative unit-sphere candidate search.

    The unit-sphere tree is only a lower-bound index. Every representative
    that can beat the incumbent ellipsoidal distance is evaluated with Geod.
    """
    qlat=np.asarray(query_lat,dtype=np.float64);qlon=np.asarray(query_lon,dtype=np.float64)
    latitudes=np.asarray(latitudes,dtype=np.float64);longitudes=np.asarray(longitudes,dtype=np.float64)
    if (qlat.ndim!=1 or qlon.shape!=qlat.shape or latitudes.ndim!=1
            or longitudes.shape!=latitudes.shape or not len(latitudes)
            or np.any(~np.isfinite(qlat)) or np.any(~np.isfinite(qlon))
            or np.any(~np.isfinite(latitudes)) or np.any(~np.isfinite(longitudes))
            or np.any(np.abs(qlat)>90) or np.any(np.abs(qlon)>180)
            or np.any(np.abs(latitudes)>90) or np.any(np.abs(longitudes)>180)):
        raise ValueError('invalid geodesic nearest inputs')
    xyz=_xyz(qlat,qlon)
    _,first=tree.query(xyz,k=1,workers=1)
    first=np.asarray(first,dtype=np.int64)
    upper=_inverse_distances(qlon,qlat,longitudes[first],latitudes[first])
    if np.any(~np.isfinite(upper)) or np.any(upper<0):raise ValueError('invalid WGS84 upper bound')
    angle=np.minimum(math.pi,(upper+BOUND_CUSHION_M)/MIN_CURVATURE_RADIUS)
    radii=np.nextafter(2*np.sin(angle/2),math.inf)
    result=np.empty(len(qlat),dtype=np.float64)
    for q in range(len(result)):
        ids=tree.query_ball_point(xyz[q],float(radii[q]),workers=1)
        if int(first[q]) not in ids:ids.append(int(first[q]))
        best=math.inf
        for start in range(0,len(ids),DISTANCE_BATCH):
            ix=np.asarray(ids[start:start+DISTANCE_BATCH],dtype=np.int64)
            dist=_inverse_distances(np.full(len(ix),qlon[q]),np.full(len(ix),qlat[q]),longitudes[ix],latitudes[ix])
            if np.any(~np.isfinite(dist)) or np.any(dist<0):raise ValueError('invalid WGS84 distance')
            best=min(best,float(np.min(dist)))
        if not math.isfinite(best):raise RuntimeError('no WGS84 hint candidate')
        result[q]=best
    return result

def lowest_code_for_min_distance(distances,codes):
    """Choose the lowest numeric code among exact minimum-distance ties."""
    d=np.asarray(distances,dtype=np.float64);c=np.asarray(codes,dtype=np.uint16)
    if d.ndim!=2 or d.shape[1]!=len(c) or not len(c) or len(set(map(int,c)))!=len(c):
        raise ValueError('invalid hint distance matrix or codes')
    if np.any(~np.isfinite(d)) or np.any(d<0):raise ValueError('invalid hint distances')
    minima=d.min(axis=1,keepdims=True)
    return np.min(np.where(d==minima,c[None,:],np.iinfo(np.uint16).max),axis=1).astype(np.uint8)

def wgs84_nearest_categories(tree,latitudes,longitudes,codes,query_lat,query_lon):
    """Find the global WGS84 representative winner in one conservative search.

    The winning category is the category of the globally nearest sample, so
    computing six independent category minima is unnecessary. The nearest
    spherical sample supplies only an ellipsoidal upper witness. Every sample
    that can beat it is still checked with the same WGS84 inverse, including
    exact ties, and the lowest category code wins those ties.
    """
    lat=np.asarray(latitudes,dtype=float);lon=np.asarray(longitudes,dtype=float)
    qlat=np.asarray(query_lat,dtype=float);qlon=np.asarray(query_lon,dtype=float)
    codes=np.asarray(codes)
    if (lat.ndim!=1 or lon.shape!=lat.shape or codes.shape!=lat.shape or not len(lat)
            or not np.issubdtype(codes.dtype,np.integer) or np.any((codes<1)|(codes>255))
            or qlat.ndim!=1 or qlon.shape!=qlat.shape
            or any(np.any(~np.isfinite(a)) for a in (lat,lon,qlat,qlon))
            or np.any(np.abs(lat)>90) or np.any(np.abs(qlat)>90)
            or np.any(np.abs(lon)>180) or np.any(np.abs(qlon)>180)):
        raise ValueError('invalid geodesic nearest inputs')
    if not len(qlat):return np.empty(0,dtype=np.uint8)
    xyz=_xyz(qlat,qlon);_,first=tree.query(xyz,k=1,workers=1)
    first=np.asarray(first,dtype=np.int64)
    upper=_inverse_distances(qlon,qlat,lon[first],lat[first])
    if np.any(~np.isfinite(upper)) or np.any(upper<0):raise ValueError('invalid WGS84 upper bound')
    angle=np.minimum(math.pi,(upper+BOUND_CUSHION_M)/MIN_CURVATURE_RADIUS)
    radii=np.nextafter(2*np.sin(angle/2),math.inf)
    # Ordinary candidate batches keep large valid neighborhoods streaming;
    # neither the number of samples nor the number of candidates is limited.
    best=np.full(len(qlat),math.inf);chosen=np.full(len(qlat),256,dtype=np.uint16)
    queries=[];samples=[];pending=0
    def flush():
        nonlocal pending
        if not pending:return
        qi=np.concatenate(queries);ix=np.concatenate(samples)
        distances=_inverse_distances(qlon[qi],qlat[qi],lon[ix],lat[ix])
        if np.any(~np.isfinite(distances)) or np.any(distances<0):raise ValueError('invalid WGS84 distance')
        previous=best.copy();np.minimum.at(best,qi,distances)
        chosen[best<previous]=256
        tied=distances==best[qi]
        np.minimum.at(chosen,qi[tied],codes[ix[tied]])
        queries.clear();samples.clear();pending=0
    for q in range(len(qlat)):
        ids=tree.query_ball_point(xyz[q],float(radii[q]),workers=1)
        if int(first[q]) not in ids:ids.append(int(first[q]))
        for start in range(0,len(ids),DISTANCE_BATCH):
            ix=np.asarray(ids[start:start+DISTANCE_BATCH],dtype=np.int64)
            queries.append(np.full(len(ix),q,dtype=np.int64));samples.append(ix);pending+=len(ix)
            if pending>=DISTANCE_BATCH:flush()
    flush()
    if np.any(chosen>255) or np.any(~np.isfinite(best)):raise RuntimeError('no WGS84 hint candidate')
    return chosen.astype(np.uint8)

def choose_hints(db_path,reps,width,height,step,north,codes,batch=8192,guard=lambda:None):
    """Select category of nearest sampled representative by WGS84 distance.

    The caller MUST verify 5-field (tile_y,tile_x,row,col,code) records against
    the current seed RLE and hash-pinned tile index first. Unit-sphere indexing
    only narrows candidates; all hint distances are WGS84 ellipsoidal minima.
    Hints are not final labels and later search verifies every result.
    """
    codes=list(codes);r=np.asarray(reps)
    if not codes or len(set(codes))!=len(codes) or any(type(c)!=int or not 1<=c<=255 for c in codes): raise ValueError('invalid categories')
    codes.sort()
    if not np.issubdtype(r.dtype,np.integer) or np.any(r<0): raise ValueError('invalid representatives')
    if not math.isfinite(step) or step<=0 or abs(width*step-360)>1e-8 or not -90<=north<=90 or north-height*step < -90-1e-8 or r.ndim!=2 or r.shape[1]!=5 or not len(r): raise ValueError('bad grid/reps')
    if np.any(r[:,2]>=height) or np.any(r[:,3]>=width) or set(map(int,r[:,4]))!=set(codes) or type(batch)!=int or not 1<=batch<=8192: raise ValueError('bad representatives')
    plat=north-(r[:,2].astype(float)+.5)*step;plon=-180+(r[:,3].astype(float)+.5)*step
    tree=cKDTree(_xyz(plat,plon))
    con=sqlite3.connect('file:'+quote(str(Path(db_path).resolve()),safe='/')+'?mode=ro',uri=True)
    try:
        cur=con.execute('SELECT id,y,x FROM roots ORDER BY id')
        while True:
            guard();chunk=cur.fetchmany(batch)
            if not chunk: break
            a=np.asarray(chunk,dtype=np.uint32);lat=north-(a[:,1].astype(float)+.5)*step;lon=-180+(a[:,2].astype(float)+.5)*step
            chosen=wgs84_nearest_categories(tree,plat,plon,r[:,4],lat,lon)
            yield a[:,0],chosen
    finally: con.close()

def seed_roots_from_resolution(report, *, grid, input_sha256, snapshot_sha256,
                               component_manifest_sha256, decision_revision, entity_revision):
    """Read current root claims after caller authenticates the report and inputs.

    This validates binding and basic shape, but DOES NOT authenticate the report,
    prove witness geometry, prove mainland extent, or replace the resolver.
    """
    if not isinstance(report,dict) or report.get('schema')!='mainland-witness-resolution-v1' or report.get('status')!='selected-research-identity-claims-not-mainland-proof' or report.get('publishable') is not False: raise ValueError('invalid witness resolution')
    expected={'grid':grid,'input_sha256':input_sha256,'snapshot_sha256':snapshot_sha256,'component_manifest_sha256':component_manifest_sha256,'decision_revision':decision_revision,'entity_revision':entity_revision}
    if any(report.get(k)!=v for k,v in expected.items()): raise ValueError('stale or mismatched witness resolution')
    groups=report.get('groups')
    if not isinstance(groups,list) or not groups: raise ValueError('invalid groups')
    ids=set();all_roots=set();roots=[]
    for g in groups:
        if not isinstance(g,dict) or not isinstance(g.get('group_id'),str) or not g['group_id'] or g['group_id'] in ids or g.get('role') not in ('mainland','sentinel'): raise ValueError('invalid group')
        ids.add(g['group_id']);root=g.get('component_id_current_generation_only');targets=g.get('target_entity_ids')
        if type(root)!=int or not 0<=root<2**32-1 or root in all_roots or not isinstance(targets,list) or (g['role']=='mainland')!=bool(targets): raise ValueError('invalid or conflicting root')
        all_roots.add(root)
        if g['role']=='mainland':roots.append(root)
    if not roots: raise ValueError('no mainland roots')
    return sorted(roots)
