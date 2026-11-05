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
        with open(runs,'rb') as f:
            for y in range(height):
                guard(); n=int(o[y+1]-o[y]);
                if n>width: raise ValueError('component row exceeds width')
                raw=f.read(n*12)
                if len(raw)!=n*12: raise ValueError('truncated component row')
                a=np.frombuffer(raw,dtype='<u4').reshape(-1,3)
                if n and (np.any(a[:,0]>=a[:,1]) or np.any(a[:,1]>width) or np.any(a[1:,0]<a[:-1,1]) or np.any(a[:,2]==2**32-1)): raise ValueError('invalid component row')
                if n:
                    ids,ix=np.unique(a[:,2],return_index=True)
                    con.executemany('INSERT OR IGNORE INTO roots VALUES (?,?,?)',((int(root),y,int(a[j,0])) for root,j in zip(ids,ix)))
                if y%1024==0: con.commit()
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

def choose_hints(db_path,reps,width,height,step,north,codes,batch=8192,guard=lambda:None):
    """Select category of nearest sampled representative by WGS84 distance.

    The caller MUST verify 5-field (tile_y,tile_x,row,col,code) records against the current seed RLE and hash-pinned tile index first. Per category, spherical-nearest sampled witness is used as a fast heuristic;
    this need not be WGS84-nearest, because later search verifies every result.
    """
    codes=list(codes);r=np.asarray(reps)
    if not codes or len(set(codes))!=len(codes) or any(type(c)!=int or not 1<=c<=255 for c in codes): raise ValueError('invalid categories')
    codes.sort()
    if not np.issubdtype(r.dtype,np.integer) or np.any(r<0): raise ValueError('invalid representatives')
    if not math.isfinite(step) or step<=0 or abs(width*step-360)>1e-8 or not -90<=north<=90 or north-height*step < -90-1e-8 or r.ndim!=2 or r.shape[1]!=5 or not len(r): raise ValueError('bad grid/reps')
    if np.any(r[:,2]>=height) or np.any(r[:,3]>=width) or set(map(int,r[:,4]))!=set(codes) or type(batch)!=int or not 1<=batch<=8192: raise ValueError('bad representatives')
    trees={};coords={}
    for c in codes:
        p=r[r[:,4]==c];lat=north-(p[:,2].astype(float)+.5)*step;lon=-180+(p[:,3].astype(float)+.5)*step
        coords[c]=(lat,lon);trees[c]=cKDTree(_xyz(lat,lon))
    geod=Geod(ellps='WGS84');con=sqlite3.connect('file:'+quote(str(Path(db_path).resolve()),safe='/')+'?mode=ro',uri=True)
    try:
        cur=con.execute('SELECT id,y,x FROM roots ORDER BY id')
        while True:
            guard();chunk=cur.fetchmany(batch)
            if not chunk: break
            a=np.asarray(chunk,dtype=np.uint32);lat=north-(a[:,1].astype(float)+.5)*step;lon=-180+(a[:,2].astype(float)+.5)*step
            xyz=_xyz(lat,lon);d=[]
            for c in codes:
                _,ix=trees[c].query(xyz,k=1,workers=1);plat,plon=coords[c]
                dist=(np.asarray([geod.inv(float(lon[0]),float(lat[0]),float(plon[ix[0]]),float(plat[ix[0]]))[2]]) if len(lon)==1 else np.asarray(geod.inv(lon,lat,plon[ix],plat[ix])[2]));
                if np.any(~np.isfinite(dist)) or np.any(dist<0): raise ValueError('invalid distance')
                d.append(dist)
            # sorted codes and argmin yield deterministic lowest code on exact tie
            chosen=np.asarray(codes,dtype=np.uint8)[np.argmin(np.stack(d,axis=1),axis=1)]
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
    if not isinstance(groups,list) or not groups or len(groups)>64: raise ValueError('invalid groups')
    ids=set();all_roots=set();roots=[]
    for g in groups:
        if not isinstance(g,dict) or not isinstance(g.get('group_id'),str) or not g['group_id'] or g['group_id'] in ids or g.get('role') not in ('mainland','sentinel'): raise ValueError('invalid group')
        ids.add(g['group_id']);root=g.get('component_id_current_generation_only');targets=g.get('target_entity_ids')
        if type(root)!=int or not 0<=root<2**32-1 or root in all_roots or not isinstance(targets,list) or (g['role']=='mainland')!=bool(targets): raise ValueError('invalid or conflicting root')
        all_roots.add(root)
        if g['role']=='mainland':roots.append(root)
    if not roots: raise ValueError('no mainland roots')
    return sorted(roots)
