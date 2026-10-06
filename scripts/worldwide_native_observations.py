"""Exact scoped native observations; whole-component interpretation remains unknown."""
import math
from collections import Counter
import numpy as np
from shapely.geometry import Point, shape
from shapely.errors import GEOSException
from geographic_grid import project

def component_probe(feature,size,latitudes):
    row={'component':feature['id'],'sample_scope':'one representative point and one native cell centre; remaining cells unchecked',
         'whole_component_physical_interpretation':'unknown','administrative_assignment':None,
         'native_multiplicity_status':'not-stored-by-first-winner-grid','cell':None,
         'native_cell_centre_strictly_inside':None,'cell_centre_lonlat':None,'representative_lonlat':None}
    try:
        geom=shape(feature['geometry'])
        if geom.is_empty or geom.geom_type not in ('Polygon','MultiPolygon') or not geom.is_valid:
            return {**row,'probe_status':'unknown-invalid-empty-or-nonpolygon-geometry'}
        point=geom.representative_point();row['representative_lonlat']=[point.x,point.y]
        if not geom.contains(point):return {**row,'probe_status':'unknown-no-strict-representative-point'}
        px,py=project(point.x,point.y,size);x,y=math.floor(px),math.floor(py)
        if not(0<=x<size and 0<=y<size):return {**row,'probe_status':'unknown-outside-native-grid'}
        centre=((x+.5)/size*360-180,float(latitudes[y]))
        return {**row,'cell':[x,y],'cell_centre_lonlat':list(centre),
                'native_cell_centre_strictly_inside':bool(geom.contains(Point(*centre))),
                'probe_status':'scoped-native-cell-ready','original_extent_lonlat':list(geom.bounds)}
    except (ValueError,TypeError,OverflowError,GEOSException) as error:
        return {**row,'probe_status':'unknown-failed-geometry-probe','failure_class':type(error).__name__}

def observe_probes(probes,grid,owner_ids):
    """Sort reads spatially to preserve bounded cache without changing output order."""
    if len(owner_ids)!=len(set(owner_ids)) or not owner_ids or owner_ids[0] is not None:
        raise ValueError('Exact ordered owner registry required')
    results={}
    for row in probes:
        if row['component']in results:raise ValueError('Duplicate component probe')
        results[row['component']]={**row,'owner_integer':None,'owner_location_id':None,
                                   'native_status':row['probe_status']}
    ready=sorted((r for r in probes if r['probe_status']=='scoped-native-cell-ready'),key=lambda r:(r['cell'][1],r['cell'][0],r['component']))
    for row in ready:
        owner=grid.pick(*row['cell'])
        if not 0<=owner<len(owner_ids):raise ValueError('Native owner outside ordered registry')
        inside=row['native_cell_centre_strictly_inside']
        status=('inside-owned-grid-source-discrepancy' if owner else 'inside-unassigned-native-cell') if inside else (
                 'outside-owned-centre-component-unchecked' if owner else 'outside-unassigned-centre-component-unchecked')
        results[row['component']].update(owner_integer=owner,owner_location_id=owner_ids[owner],native_status=status)
    ordered=[results[r['component']]for r in probes]
    if len(ordered)!=len(probes):raise ValueError('Incomplete native observation cohort')
    return ordered,dict(sorted(Counter(r['native_status']for r in ordered).items()))

def full_owner_counts(grid,owner_ids):
    """Count every encoded run; zero cells is a grid observation, not no territory."""
    if len(owner_ids)!=len(set(owner_ids)) or owner_ids[0]is not None:
        raise ValueError('Exact ordered owner registry required')
    counts=np.zeros(len(owner_ids),dtype=np.uint64);run_count=0
    for pin in grid.parts['runs']:
        words=grid._words(pin);a,b=words[::2],words[1::2]
        start=(a&grid.mask).astype(np.uint64);end=(b&grid.mask).astype(np.uint64)+1
        ids=(a.astype(np.uint64)>>grid.bits)+(b.astype(np.uint64)>>grid.bits)*2**(32-grid.bits)
        if np.any(ids==0)or np.any(ids>=len(owner_ids))or np.any(end<=start):
            raise ValueError('Invalid packed full-owner accounting')
        np.add.at(counts,ids.astype(np.intp),end-start);run_count+=len(ids)
    assigned=sum(int(x)for x in counts)
    if run_count*2!=grid.manifest['runWords']or assigned>grid.size**2:
        raise ValueError('Incomplete full-run accounting')
    return [{'id':identity,'owner_integer':i,'represented_assigned_cell_count':int(counts[i]),
             'measurement_scope':'all represented RLE cells of this pinned grid; not physical source or ownership approval',
             'native_multiplicity_status':'not-stored-by-first-winner-grid'}for i,identity in enumerate(owner_ids)if i],{
             'rows':grid.size,'runs':run_count,'assigned_cells':assigned,'unassigned_cells':grid.size**2-assigned,
             'grid_cells':grid.size**2,'contexts':len(owner_ids)-1,'multiple_cells':None,
             'multiple_cell_status':'not-stored-by-first-winner-grid'}
