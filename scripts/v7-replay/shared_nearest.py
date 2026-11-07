"""Shared SeaVoX basin assignment from physical water and final land only.

No previous water labels are inputs. Distances are WGS84 geodesic
center-to-center to physical coastal land cells, in metres. Each participant is indexed independently; missing shores or
an insufficient crop fail closed. This module is a candidate, not a release.
"""
from __future__ import annotations
import math
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Geod

A=6378137.0
F=1/298.257223563
MIN_RADIUS=A*(1-F*(2-F))
GEOD=Geod(a=A,f=F)

def unit(lat,lon):
    lat=np.deg2rad(lat);lon=np.deg2rad(lon);c=np.cos(lat)
    return np.column_stack((c*np.cos(lon),c*np.sin(lon),np.sin(lat)))


def geodesic_distances(lon,lat,target_lon,target_lat):
    lon,lat,target_lon,target_lat=np.broadcast_arrays(*[np.asarray(v,dtype=np.float64) for v in (lon,lat,target_lon,target_lat)])
    if lon.ndim!=1:raise ValueError('distance inputs must be one-dimensional')
    if not len(lon):return np.empty(0,dtype=np.float64)
    if len(lon)==1:
        return np.asarray([GEOD.inv(float(lon[0]),float(lat[0]),float(target_lon[0]),float(target_lat[0]))[2]])
    return np.asarray(GEOD.inv(lon,lat,target_lon,target_lat)[2],dtype=np.float64)


def binding(snapshot, entity, physical_class, codes):
    values = [b.get('code') for b in snapshot.get('category_bindings', [])
              if b.get('entity_id') == entity and b.get('physical_class') == physical_class]
    if len(values) != 1 or type(values[0]) is not int or values[0] not in codes:
        raise ValueError(f'entity {entity} lacks a unique {physical_class} binding')
    return values[0]


def selected_rules(snapshot, basin):
    """Resolve the versioned priority by stable entity ID, not category order."""
    if basin.get('assignment_method') != 'shared_nearest_assigned_shore':
        raise ValueError('unsupported shared-basin assignment method')
    participants = basin.get('participant_entity_ids')
    if not isinstance(participants, list) or len(participants) < 2 or len(set(participants)) != len(participants):
        raise ValueError('shared basin requires distinct participant entities')
    tie = basin.get('tie_rules')
    if (not isinstance(tie, dict) or set(tie) != {'method','tie_break','priority_entity_ids','tolerance_metres'}
            or tie.get('method') != 'within_minimum_distance_tolerance' or tie.get('tie_break') != 'first_entity_in_priority_order'):
        raise ValueError('unsupported or missing shared-basin tie rules')
    order = tie.get('priority_entity_ids')
    if not isinstance(order, list) or len(order) != len(participants) or len(set(order)) != len(order) or set(order) != set(participants):
        raise ValueError('tie priority must list each participant exactly once')
    raw = tie.get('tolerance_metres')
    if isinstance(raw, bool): raise ValueError('invalid tie tolerance')
    try: tolerance = float(raw)
    except (TypeError, ValueError): raise ValueError('invalid tie tolerance') from None
    if not math.isfinite(tolerance) or tolerance < 0 or tolerance > 1:
        raise ValueError('invalid tie tolerance')
    pairs = [(entity, binding(snapshot, entity, 'land', range(17,23)),
              binding(snapshot, entity, 'water', range(1,7))) for entity in order]
    if len({p[1] for p in pairs}) != len(pairs) or len({p[2] for p in pairs}) != len(pairs):
        raise ValueError('participant land and water bindings must be distinct')
    return pairs, tolerance


def crop(rows, runs, y, x0, x1, width):
    if not (0 <= y < len(rows)-1 and 0 < x1-x0 <= width): raise ValueError('invalid crop')
    first,last=int(rows[y]),int(rows[y+1]); ends=runs[2*first:2*last:2]; vals=runs[2*first+1:2*last:2]
    if not len(ends) or int(ends[0]) <= 0 or int(ends[-1]) != width or np.any(ends[1:] <= ends[:-1]):
        raise ValueError(f'invalid RLE row {y}')
    if x0 == 0 and x1 == width:
        lengths=np.diff(np.concatenate((np.array([0],dtype=ends.dtype),ends)))
        return np.repeat(vals,lengths).astype(np.uint32,copy=False)
    result=np.empty(x1-x0, dtype=np.uint32); cur=0; x=x0
    while x < x1:
        xm=x%width; take=min(x1-x,width-xm); stop=xm+take
        i=int(np.searchsorted(ends,xm,side='right'))
        while xm < stop:
            e=min(int(ends[i]),stop); result[cur:cur+e-xm]=int(vals[i]); cur+=e-xm; xm=e; i+=1
        x+=take
    return result


def crop_bounds(bounds, width, height, step, pad_degrees):
    x0,x1,y0,y1=bounds
    if not math.isfinite(pad_degrees) or pad_degrees <= 0: raise ValueError('pad must be positive')
    pad=math.ceil(pad_degrees/step)
    xa,xb=x0-pad,x1+pad
    if xb-xa >= width: xa,xb=0,width
    return xa,xb,max(0,y0-pad),min(height,y1+pad)


def centers_for_crop(physical, land, bounds, width, height, step, land_codes):
    """Index each included coastal land-cell center once, with full neighbors.

    Crops may cross the antimeridian. Land cell is coastal if any orthogonal
    neighbor is physical water; next-row and side halos avoid crop artifacts.
    """
    x0,x1,y0,y1=bounds
    if not (0<=y0<y1<=height and 0<x1-x0<=width and math.isfinite(step) and step>0):raise ValueError('invalid crop')
    latitudes=[];longitudes=[];categories=[];count=0
    allowed_physical=np.zeros(23,dtype=bool);allowed_physical[[1,17]]=True
    allowed_land=np.zeros(23,dtype=bool);allowed_land[17:23]=True
    selected_land=np.zeros(23,dtype=bool);selected_land[land_codes]=True
    for y in range(y0,y1):
        mid=crop(*physical,y,x0,x1,width)
        l=crop(*land,y,x0,x1,width)
        if x1-x0<width:
            left=np.r_[crop(*physical,y,x0-1,x0,width),mid[:-1]]
            right=np.r_[mid[1:],crop(*physical,y,x1,x1+1,width)]
        else:left=np.roll(mid,1);right=np.roll(mid,-1)
        p=np.r_[left,mid,right]
        if np.any((p<0)|(p>=23)) or np.any(~allowed_physical[p]):raise ValueError('invalid physical or land row')
        land_safe=np.clip(l,0,22)
        land_invalid=(l<0)|(l>=23)
        if np.any((mid==17)&(land_invalid|~allowed_land[land_safe])):raise ValueError('invalid physical or land row')
        wet=(left==1)|(right==1)
        for ny in (y-1,y+1):
            if 0<=ny<height:
                pn=crop(*physical,ny,x0,x1,width)
                if np.any((pn<0)|(pn>=23)) or np.any(~allowed_physical[pn]):raise ValueError('invalid neighboring physical row')
                wet|=pn==1
        ix=np.flatnonzero((mid==17)&selected_land[land_safe]&wet)
        count+=len(ix)
        if len(ix):
            latitudes.append(np.full(len(ix),90-(y+.5)*step))
            longitudes.append(((-180+(x0+ix+.5)*step+180)%360)-180)
            categories.append(l[ix].astype(np.uint8))
    if not count:raise ValueError('no participant shorelines in crop')
    lat=np.concatenate(latitudes);lon=np.concatenate(longitudes);cat=np.concatenate(categories)
    return {'mids':unit(lat,lon),'lat':lat,'lon':lon,'category':cat}

def boundary_lower(lat,lon,bounds,width,height,step):
    """Conservative distance to any shoreline omitted outside the crop."""
    x0,x1,y0,y1=bounds; latr=np.deg2rad(lat); lonr=np.deg2rad(lon)
    d=np.full(len(lat),np.inf,dtype=np.float64)
    if y0>0: d=np.minimum(d,np.abs(lat-(90-y0*step))*math.pi/180*MIN_RADIUS)
    if y1<height: d=np.minimum(d,np.abs(lat-(90-y1*step))*math.pi/180*MIN_RADIUS)
    if x1-x0<width:
        for edge in (x0,x1):
            lam=math.radians(-180+edge*step)
            d=np.minimum(d,MIN_RADIUS*np.arcsin(np.clip(np.abs(np.cos(latr)*np.sin(lonr-lam)),0,1)))
    return np.maximum(0.0,d-0.001)


def make_indexes(centers, pairs):
    indexes={}
    for _,land_code,_ in pairs:
        mask=centers['category']==land_code
        if not np.any(mask):raise ValueError(f'crop has no shoreline for participant land code {land_code}')
        part={k:centers[k][mask] for k in ('mids','lat','lon','category')}
        indexes[land_code]=(part,cKDTree(part['mids']))
    return indexes

def exact_minimum_by_ordered_chord(point, lon, lat, data, tree):
    """Exact WGS84 minimum with complete-input streaming for wide searches.

    Small nearest-neighbor prefixes often prove the answer quickly. If not,
    iterate over *every* shoreline center in ordinary blocks, using only a
    conservative chord-derived WGS84 lower bound to avoid unnecessary inverse
    calls. Block size changes temporary-array shape, never input coverage.
    """
    n=int(tree.n)
    if n<=0: return math.inf
    take=min(16,n); best=math.inf
    while True:
        request=min(n,take+1)
        chords,ids=tree.query(point,k=request,workers=1)
        chords=np.atleast_1d(chords); ids=np.atleast_1d(ids)
        part=ids[:take]
        if len(part):
            ds=geodesic_distances(np.full(len(part),lon),np.full(len(part),lat),data['lon'][part],data['lat'][part])
            if np.any(~np.isfinite(ds)):raise ValueError('invalid inverse geodesic')
            best=min(best,float(np.min(ds)))
        if take==n:return best
        angle=2*math.asin(min(1.0,max(0.0,float(chords[take])/2)))
        lower=max(0.0,MIN_RADIUS*angle-.001)
        if lower>best+.000001:return best
        if take>=4096:
            # Visit every point, including all equal-chord ties. Use a generous
            # floating-point margin; exact inverse distance decides the result.
            for first in range(0,n,4096):
                last=min(first+4096,n)
                diff=data['mids'][first:last]-point
                chord=np.sqrt(np.sum(diff*diff,axis=1))
                # Chord <= central angle, even at the antipode. Avoid asin
                # sensitivity near chord 2 and keep a conservative margin.
                lower=np.maximum(0,MIN_RADIUS*chord-.01)
                keep=np.flatnonzero(lower<=best+.000001)+first
                if len(keep):
                    ds=geodesic_distances(np.full(len(keep),lon),np.full(len(keep),lat),data['lon'][keep],data['lat'][keep])
                    if np.any(~np.isfinite(ds)):raise ValueError('invalid inverse geodesic')
                    best=min(best,float(np.min(ds)))
            return best
        take=min(n,take*2)


def classify_wgs84(lat,lon,bounds,width,height,step,pairs,tolerance,indexes,*,band=None,bandtol=0):
    """Certify WGS84 nearest coastal-cell-center assignments or fail closed.

    Spherical unit vectors only narrow the search using a conservative WGS84
    lower bound. All returned classifications use ellipsoidal distances.
    """
    lat=np.asarray(lat,dtype=np.float64);lon=np.asarray(lon,dtype=np.float64)
    if lat.ndim!=1 or lon.shape!=lat.shape or np.any(~np.isfinite(lat)) or np.any(~np.isfinite(lon)) or np.any(np.abs(lat)>90) or np.any(np.abs(lon)>180):raise ValueError('invalid query coordinates')
    if not math.isfinite(tolerance) or tolerance<0 or (band is not None and (not math.isfinite(band) or band<0 or not math.isfinite(bandtol) or bandtol<0)):raise ValueError('invalid distances')
    x0,x1,y0,y1=bounds
    if any(type(z) is not int for z in (x0,x1,y0,y1,width,height)) or not (0<width and 0<height and 0<x1-x0<=width and 0<=y0<y1<=height and math.isfinite(step) and step>0):raise ValueError('invalid crop or grid')
    if abs(step*width-360)>1e-8:raise ValueError('step does not match world width')
    if not len(lat):return np.empty(0,dtype=np.uint8),{'bounded':0,'exact':0}
    # An omitted-shore proof is valid only for points inside the indexed crop.
    y=(90-lat)/step; x=(lon+180)/step; x=x+np.ceil((x0-x)/width)*width
    if np.any(y<y0-1e-8) or np.any(y>y1+1e-8) or np.any(x<x0-1e-8) or np.any(x>x1+1e-8):raise ValueError('query lies outside crop')
    points=unit(lat,lon);boundary=boundary_lower(lat,lon,bounds,width,height,step)
    available=[p for p in pairs if p[1] in indexes]
    if band is None and len(available)!=len(pairs):raise ValueError('missing participant shore')
    if not available:
        if band is None or np.any(boundary<=band+bandtol):raise ValueError('crop cannot certify; increase halo')
        return np.zeros(len(lat),dtype=np.uint8),{'bounded':len(lat),'exact':0}
    lows=[];highs=[]
    for _,lc,_ in available:
        data,tree=indexes[lc];chord,ix=tree.query(points,k=1,workers=1)
        angle=2*np.arcsin(np.clip(chord/2,0,1))
        lows.append(np.maximum(0,MIN_RADIUS*angle-.001))
        d=geodesic_distances(lon,lat,data['lon'][ix],data['lat'][ix])
        if np.any(~np.isfinite(d)):raise ValueError('invalid inverse geodesic')
        highs.append(d+.000001)
    lows=np.column_stack(lows);highs=np.column_stack(highs)
    best=np.argmin(highs,axis=1);upper=highs[np.arange(len(lat)),best]
    others=lows.copy();others[np.arange(len(lat)),best]=np.inf
    unique=(upper+tolerance<others.min(axis=1))&(upper+tolerance<boundary)
    out=np.zeros(len(lat),dtype=np.uint8)
    if band is None:fast=unique
    else:
        threshold=band+bandtol
        outside=(lows.min(axis=1)>threshold)&(boundary>threshold)
        inside=unique&(upper<=threshold)
        fast=outside|inside
    for i,(_,_,code) in enumerate(available):out[fast & (best==i) & (True if band is None else inside)]=code
    pending=np.flatnonzero(~fast)
    for q in pending:
        distances=[]
        for _,lc,_ in available:
            data,tree=indexes[lc]
            distances.append(exact_minimum_by_ordered_chord(points[q],float(lon[q]),float(lat[q]),data,tree))
        minimum=min(distances)
        if not math.isfinite(minimum):raise RuntimeError('no provable candidate shore')
        if band is not None and minimum>threshold:
            if boundary[q]<=threshold:raise ValueError('crop cannot certify coastal band; increase halo')
            if abs(minimum-threshold)<=.0000001:raise RuntimeError('band threshold numerically ambiguous')
            continue
        if band is not None and abs(minimum-threshold)<=.0000001:raise RuntimeError('band threshold numerically ambiguous')
        if minimum+tolerance+.000001>=boundary[q]:raise ValueError('crop cannot certify nearest shore; increase halo')
        for i,d in enumerate(distances):
            if math.isfinite(d) and abs((d-minimum)-tolerance)<=.0000001:raise RuntimeError('tie threshold numerically ambiguous')
            if d<=minimum+tolerance:
                out[q]=available[i][2];break
    return out,{'bounded':int(fast.sum()),'exact':int(len(pending))}

def classify(lat,lon,bounds,width,height,step,pairs,tolerance,indexes):
    out,stats=classify_wgs84(lat,lon,bounds,width,height,step,pairs,tolerance,indexes)
    return out,stats['bounded'],stats['exact']
