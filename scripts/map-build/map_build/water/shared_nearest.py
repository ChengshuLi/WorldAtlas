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


def binding(snapshot, entity, physical_class, codes=None):
    values = [b.get('code') for b in snapshot.get('category_bindings', [])
              if b.get('entity_id') == entity and b.get('physical_class') == physical_class]
    if (len(values) != 1 or type(values[0]) is not int or not 0 < values[0] < 2**32
            or (codes is not None and values[0] not in codes)):
        raise ValueError(f'entity {entity} lacks a unique {physical_class} binding')
    return values[0]


def tie_policy(snapshot, tie, participants=None):
    """Resolve a distance tie policy through stable entity bindings."""
    if (not isinstance(tie, dict)
            or set(tie) != {'method', 'tie_break', 'priority_entity_ids', 'tolerance_metres'}
            or tie.get('method') != 'within_minimum_distance_tolerance'
            or tie.get('tie_break') != 'first_entity_in_priority_order'):
        raise ValueError('unsupported or missing shared-basin tie rules')
    order = tie['priority_entity_ids']
    if (not isinstance(order, list) or not order or len(set(order)) != len(order)
            or (participants is not None and set(order) != set(participants))):
        raise ValueError('tie priority must list each participant exactly once')
    raw = tie['tolerance_metres']
    if isinstance(raw, bool):
        raise ValueError('invalid tie tolerance')
    try:
        tolerance = float(raw)
    except (TypeError, ValueError):
        raise ValueError('invalid tie tolerance') from None
    if not math.isfinite(tolerance) or not 0 <= tolerance <= 1:
        raise ValueError('invalid tie tolerance')
    pairs = [(entity, binding(snapshot, entity, 'land'), binding(snapshot, entity, 'water'))
             for entity in order]
    codes = [code for _, land, water in pairs for code in (land, water)]
    if len(set(codes)) != len(codes):
        raise ValueError('participant land and water bindings must be distinct')
    return pairs, tolerance


def selected_rules(snapshot, basin):
    """Read the fixed participant selection of a saved basin replay."""
    if basin.get('assignment_method') != 'shared_nearest_assigned_shore':
        raise ValueError('unsupported shared-basin assignment method')
    participants = basin.get('participant_entity_ids')
    if not isinstance(participants, list) or len(participants) < 2 or len(set(participants)) != len(participants):
        raise ValueError('shared basin requires distinct participant entities')
    return tie_policy(snapshot, basin.get('tie_rules'), participants)


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
        j=int(np.searchsorted(ends,stop,side='left'))+1
        clipped=np.minimum(ends[i:j],stop).astype(np.int64)
        lengths=np.diff(np.r_[xm,clipped])
        result[cur:cur+take]=np.repeat(vals[i:j],lengths)
        cur+=take
        x+=take
    return result


def crop_bounds(bounds, width, height, step, pad_degrees):
    x0,x1,y0,y1=bounds
    if not math.isfinite(pad_degrees) or pad_degrees <= 0: raise ValueError('pad must be positive')
    pad=math.ceil(pad_degrees/step)
    xa,xb=x0-pad,x1+pad
    if xb-xa >= width: xa,xb=0,width
    return xa,xb,max(0,y0-pad),min(height,y1+pad)


def _shore_spans(grid,y,x0,x1,width):
 rows,runs=grid;first,last=int(rows[y]),int(rows[y+1]);ends=runs[2*first:2*last:2];vals=runs[2*first+1:2*last:2]
 if not len(ends) or int(ends[0])<=0 or int(ends[-1])!=width or np.any(ends[1:]<=ends[:-1]):raise ValueError('invalid RLE row')
 out_e=[];out_v=[];x=x0
 while x<x1:
  xm=x%width; take=min(x1-x,width-xm);stop=xm+take
  i=int(np.searchsorted(ends,xm,side='right'));j=int(np.searchsorted(ends,stop,side='left'))+1
  ee=np.minimum(ends[i:j].astype(np.int64),stop)-xm+x
  out_e.extend(ee.tolist());out_v.extend(vals[i:j].tolist());x+=take
 return np.asarray(out_e,dtype=np.int64),np.asarray(out_v,dtype=np.int64)

def centers_for_crop(physical,land,bounds,width,height,step,land_codes,*,all_land_codes=None):
 """Extract exact four-neighbor coastal centers from RLE change positions.

 Dense arrays are allocated only for coastal centers. Wrapped crops retain
 original row/column order and use real physical neighbors beyond crop edges.
 """
 x0,x1,y0,y1=bounds
 if not (0<=y0<y1<=height and 0<x1-x0<=width and math.isfinite(step) and step>0):raise ValueError('invalid crop')
 selected=np.asarray(land_codes,dtype=np.uint32)
 latitudes=[];longitudes=[];categories=[];count=0
 # full-width crops cannot be extended in the original crop helper, but this
 # span reader intentionally supports repeated wrapping for the side halo.
 def pget(y):
  e,v=_shore_spans(physical,y,x0-1,x1+1,width)
  if np.any((v!=1)&(v!=17)):raise ValueError('invalid physical or land row')
  return e,v
 prev=pget(y0-1) if y0>0 else None;cur=pget(y0);nxt=pget(y0+1) if y0+1<height else None
 for y in range(y0,y1):
  le,lv=_shore_spans(land,y,x0,x1,width)
  # Break at all changes in either adjacent physical row, current physical
  # row, or land category. Side halo endpoints are clipped out.
  breaks=[np.array([x0,x1]),le,cur[0]]
  if prev is not None:breaks.append(prev[0])
  if nxt is not None:breaks.append(nxt[0])
  b=np.unique(np.concatenate(breaks));b=b[(b>=x0)&(b<=x1)];starts=b[:-1];ends=b[1:]
  mv=cur[1][np.searchsorted(cur[0],starts,side='right')]
  cats=lv[np.searchsorted(le,starts,side='right')]
  valid=(cats>0) if all_land_codes is None else np.isin(cats,all_land_codes)
  bad=(mv==17)&~valid
  if np.any(bad):raise ValueError('invalid physical or land row')
  wet=np.zeros(len(starts),dtype=bool)
  for row in (prev,nxt):
   if row is not None:wet |= row[1][np.searchsorted(row[0],starts,side='right')]==1
  chosen=(mv==17)&np.isin(cats,selected)&wet
  starts1=starts[chosen];ends1=ends[chosen]
  xx=np.concatenate([np.arange(a,b,dtype=np.int64) for a,b in zip(starts1,ends1)]) if len(starts1) else np.empty(0,dtype=np.int64)
  # Horizontal coast consists of the land cell on each wet/dry run boundary.
  ce,cv=cur; t=np.flatnonzero(cv[:-1]!=cv[1:]);boundary=ce[t]
  side=np.where(cv[t]==17,boundary-1,boundary);side=side[(side>=x0)&(side<x1)]
  if len(side):
   sc=lv[np.searchsorted(le,side,side='right')];side=side[np.isin(sc,selected)]
   xx=np.union1d(xx,side)
  count+=len(xx)
  if len(xx):
   latitudes.append(np.full(len(xx),90-(y+.5)*step));longitudes.append(((-180+(xx+.5)*step+180)%360)-180)
   categories.append(lv[np.searchsorted(le,xx,side='right')].astype(np.uint32))
  prev,cur=cur,nxt
  nxt=pget(y+2) if y+2<height and y+1<y1 else None
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

def nearest_class_bounds(lat, lon, points, pairs, indexes, *, upper_limit=None):
    """Lower bounds for all classes, one exact candidate upper bound per query.

    The spherical-nearest class need not win on WGS84. It is only a candidate:
    callers must prove its exact upper bound beats every competing lower bound
    or fall back to complete exact minima. No inverse call is needed for a
    competing class that has already been excluded by its lower bound.
    """
    count = len(points)
    lower = np.empty((count, len(pairs)), dtype=np.float64)
    targets_lon = np.empty_like(lower)
    targets_lat = np.empty_like(lower)
    query_options = {}
    search_limit = None
    if upper_limit is not None and count:
        # A coastal-band query need not find a shore on a distant continent.
        # Expand the query's exact-distance threshold using the same global
        # ellipsoid lower bound as the certificates. Missing neighbors then
        # have a finite proven lower bound, rather than being treated as absent.
        search_limit = float(np.max(upper_limit)) + .01
        if search_limit + .001 < math.pi * MIN_RADIUS:
            chord_limit = 2 * math.sin((search_limit + .001) / (2 * MIN_RADIUS))
            query_options['distance_upper_bound'] = np.nextafter(chord_limit, np.inf)
    for col, (_, code, _) in enumerate(pairs):
        data, tree = indexes[code]
        chord, ix = tree.query(points, k=1, workers=1, **query_options)
        found = np.isfinite(chord)
        angle = 2 * np.arcsin(np.clip(chord / 2, 0, 1))
        # Chord itself stays a conservative angular bound near antipodes,
        # where asin amplifies floating-point error.
        lower[:, col] = np.maximum(0, MIN_RADIUS * np.where(chord < 1.99, angle, chord) - .001)
        if search_limit is not None:
            lower[~found, col] = search_limit
        targets_lon[:, col] = 0
        targets_lat[:, col] = 0
        targets_lon[found, col] = data['lon'][ix[found]]
        targets_lat[found, col] = data['lat'][ix[found]]
    best = np.argmin(lower, axis=1)
    rows = np.arange(count)
    active = np.ones(count, dtype=bool) if upper_limit is None else lower[rows, best] <= upper_limit
    upper = np.full(count, np.inf)
    if np.any(active):
        d = geodesic_distances(lon[active], lat[active],
                               targets_lon[rows[active], best[active]],
                               targets_lat[rows[active], best[active]])
        if np.any(~np.isfinite(d)):
            raise ValueError('invalid inverse geodesic')
        upper[active] = d + .000001
    return lower, best, upper

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


def exact_minima_by_ordered_chord(points, lon, lat, data, tree):
    """Batch exact WGS84 minima, proving that every omitted center is farther.

    Neighbor prefixes grow only for queries whose conservative lower bound
    cannot prove the minimum. Wide unresolved searches still visit the entire
    shore through the scalar streaming implementation; no candidate is capped.
    """
    count = len(points)
    result = np.full(count, np.inf)
    n = int(tree.n)
    if not count or not n:
        return result
    active = np.arange(count)
    take = min(1, n)
    while len(active):
        request = min(n, take + 1)
        chords, ids = tree.query(points[active], k=request, workers=1)
        chords = np.asarray(chords).reshape(len(active), request)
        ids = np.asarray(ids).reshape(len(active), request)
        candidates = ids[:, :take].ravel()
        ds = geodesic_distances(np.repeat(lon[active], take),
                                np.repeat(lat[active], take),
                                data['lon'][candidates], data['lat'][candidates])
        if np.any(~np.isfinite(ds)):
            raise ValueError('invalid inverse geodesic')
        result[active] = np.minimum(result[active], ds.reshape(-1, take).min(axis=1))
        if take == n:
            break
        angle = 2 * np.arcsin(np.clip(chords[:, take] / 2, 0, 1))
        next_chord = chords[:, take]
        lower = np.maximum(0, MIN_RADIUS * np.where(next_chord < 1.99, angle, next_chord) - .001)
        active = active[lower <= result[active] + .000001]
        if take >= 4096:
            for q in active:
                result[q] = exact_minimum_by_ordered_chord(
                    points[q], float(lon[q]), float(lat[q]), data, tree)
            break
        take = min(n, take * 2)
    return result

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
    if not len(lat):return np.empty(0,dtype=np.uint32),{'bounded':0,'exact':0}
    # An omitted-shore proof is valid only for points inside the indexed crop.
    y=(90-lat)/step; x=(lon+180)/step; x=x+np.ceil((x0-x)/width)*width
    if np.any(y<y0-1e-8) or np.any(y>y1+1e-8) or np.any(x<x0-1e-8) or np.any(x>x1+1e-8):raise ValueError('query lies outside crop')
    points=unit(lat,lon);boundary=boundary_lower(lat,lon,bounds,width,height,step)
    available=[p for p in pairs if p[1] in indexes]
    if band is None and len(available)!=len(pairs):raise ValueError('missing participant shore')
    if not available:
        if band is None or np.any(boundary<=band+bandtol):raise ValueError('crop cannot certify; increase halo')
        return np.zeros(len(lat),dtype=np.uint32),{'bounded':len(lat),'exact':0}
    lows, best, upper = nearest_class_bounds(lat, lon, points, available, indexes,
                                                   upper_limit=None if band is None else band+bandtol)
    others=lows.copy();others[np.arange(len(lat)),best]=np.inf
    unique=(upper+tolerance<others.min(axis=1))&(upper+tolerance<boundary)
    out=np.zeros(len(lat),dtype=np.uint32)
    if band is None:fast=unique
    else:
        threshold=band+bandtol
        outside=(lows.min(axis=1)>threshold)&(boundary>threshold)
        inside=unique&(upper<=threshold)
        fast=outside|inside
    for i,(_,_,code) in enumerate(available):out[fast & (best==i) & (True if band is None else inside)]=code
    pending=np.flatnonzero(~fast)
    if len(pending):
        # A candidate upper bound is enough to exclude a distant class from
        # the minimum and its tolerance tie. Coastal queries can also exclude
        # classes beyond the band and its tie/ambiguity margins. Computing a
        # complete exact minimum for those classes used to dominate fallback
        # even when their nearest possible shore was on another continent.
        # Always retain the candidate class, including outside-band queries,
        # so the numerical-threshold and omitted-shore checks below still run.
        limit = upper[pending] + tolerance + .000001
        if band is not None:
            limit = np.minimum(limit, threshold + tolerance + .000001)
        distances = np.full((len(pending), len(available)), np.inf)
        for col, (_, lc, _) in enumerate(available):
            relevant = (lows[pending, col] <= limit) | (best[pending] == col)
            queries = pending[relevant]
            if len(queries):
                distances[relevant, col] = exact_minima_by_ordered_chord(
                    points[queries], lon[queries], lat[queries], *indexes[lc])
        minimum = distances.min(axis=1)
        if np.any(~np.isfinite(minimum)):
            raise RuntimeError('no provable candidate shore')
        inside = np.ones(len(pending), dtype=bool)
        if band is not None:
            if np.any(np.abs(minimum-threshold) <= .0000001):
                raise RuntimeError('band threshold numerically ambiguous')
            inside = minimum <= threshold
            if np.any(~inside & (boundary[pending] <= threshold)):
                raise ValueError('crop cannot certify coastal band; increase halo')
        if np.any(inside & (minimum+tolerance+.000001 >= boundary[pending])):
            raise ValueError('crop cannot certify nearest shore; increase halo')
        candidates = distances[inside]
        minima = minimum[inside]
        if np.any(np.abs((candidates-minima[:, None])-tolerance) <= .0000001):
            raise RuntimeError('tie threshold numerically ambiguous')
        # argmax selects the first eligible entity in the versioned priority.
        winners = np.argmax(candidates <= minima[:, None]+tolerance, axis=1)
        codes = np.asarray([p[2] for p in available], dtype=np.uint32)
        out[pending[inside]] = codes[winners]
    return out,{'bounded':int(fast.sum()),'exact':int(len(pending))}

def classify(lat,lon,bounds,width,height,step,pairs,tolerance,indexes):
    out,stats=classify_wgs84(lat,lon,bounds,width,height,step,pairs,tolerance,indexes)
    return out,stats['bounded'],stats['exact']
