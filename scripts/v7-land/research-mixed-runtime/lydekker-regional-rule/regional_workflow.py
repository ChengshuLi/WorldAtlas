"""Read-only composition of pinned line, component scan and source replay.

The caller must authenticate source resolvers, snapshot, manifest, named anchor
witnesses and the pinned mixed_claims/run_pair modules before invoking this.
This does not publish or select a geography decision.
"""
import math
from component_scan import scan, collect_runs, component_at
from regional_rule import _require, verified_line
from replay_adapter import resolve_with_mixed_replay
from geonames_anchors import discover as discover_geonames_anchors
from satellite_geodesic import apply_satellites, MIN_MERIDIONAL_RADIUS


# The source witness establishes which entire physical component must lie on
# the revised line's Oceania side. It is a validation, not a cell override.
BOO_POINT = (129.32551,-1.16341)
APPROVED_LINE_ID = 'lydekker-anu-figure81-regional-boo-east-v2'
APPROVED_GEOMETRY = '87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655'


def require_boo_east(bounds,region,row_spec,run_spec,grid):
    lon,lat=BOO_POINT
    if not (bounds[0]<=lon<=bounds[2] and bounds[1]<=lat<=bounds[3]):
        return
    root=component_at(row_spec,run_spec,grid,lon,lat)
    component=region.get(root)
    _require(isinstance(component,dict) and component['in_scope']==component['total'] and
             component['east']==component['total'] and component['west']==0 and
             component['boundary']==0 and component['outside_latitude']==0,
             'revised line must put the whole Boo witness component on the Oceania side')
    return root


def buffered_bounds(bounds, distance_m):
    """Conservative geographic search window, with a 1 km numerical guard."""
    _require(isinstance(bounds,(list,tuple)) and len(bounds)==4 and
             all(type(x) in (int,float) and math.isfinite(x) for x in bounds) and
             type(distance_m) in (int,float) and math.isfinite(distance_m) and distance_m>0, 'invalid buffer input')
    w,s,e,n=bounds
    _require(-180<=w<e<=180 and -90<=s<n<=90,'invalid region bounds')
    theta=(distance_m+1000)/MIN_MERIDIONAL_RADIUS
    lat=math.degrees(theta)
    max_abs_lat=max(abs(s),abs(n))+lat
    _require(max_abs_lat<89, 'polar buffer unsupported')
    lon=math.degrees(theta/math.cos(math.radians(max_abs_lat)))
    expanded=[w-lon,s-lat,e+lon,n+lat]
    _require(-180<=expanded[0]<expanded[2]<=180 and -90<=expanded[1]<expanded[3]<=90, 'wrapped or global buffer unsupported')
    return expanded


def research(row_spec, run_spec, grid, bounds, line_record, compiled, snapshot,
             reports, mainland_roots, mixed_claims, run_pair, anchors, *,
             line_pin, max_satellite_cells, max_gap_m, tie_m=1e-5, pending_claims=(), anchor_source=None):
    """Compose validated inputs; return only generation-scoped proposals."""
    _require(isinstance(grid,dict) and type(grid.get('width')) is int and
             grid['width']>1 and grid.get('west') == -180 and
             grid.get('step') == 360/grid['width'], 'WGS84 global grid required')
    _require(isinstance(line_pin,dict), 'approved line pin required')
    _require(line_pin == {'line_id':APPROVED_LINE_ID,'geometry_sha256':APPROVED_GEOMETRY},
             'unapproved Lydekker line pin')
    line=verified_line(line_record,line_pin)
    region=scan(row_spec,run_spec,grid,bounds,line)
    boo_root=require_boo_east(bounds,region,row_spec,run_spec,grid)
    buffer=scan(row_spec,run_spec,grid,buffered_bounds(bounds,max_gap_m+tie_m),line)
    _require(set(region).issubset(buffer) and
             all(region[r]['total']==buffer[r]['total'] for r in region), 'inconsistent component windows')
    initial=resolve_with_mixed_replay(region,compiled,snapshot,reports,mainland_roots,mixed_claims,pending_claims)
    buffered_initial=resolve_with_mixed_replay(buffer,compiled,snapshot,reports,mainland_roots,mixed_claims,pending_claims)
    _require((anchors is None) != (anchor_source is None), 'provide exactly one anchor source or authenticated anchor set')
    anchor_statistics=None
    if anchor_source is not None:
        discovered=discover_geonames_anchors(anchor_source,row_spec,run_spec,grid,buffer,
                                              buffered_initial['proposals'],max_satellite_cells=max_satellite_cells)
        anchors=discovered['anchors']
        anchor_statistics=discovered['statistics']
    # Outside-window source anchors may compete but must never be returned as
    # regional changes. Use only independently established buffered targets.
    external_anchors=set(anchors)-set(region)
    _require(external_anchors.issubset(buffer), 'anchor outside competitor buffer')
    initial['proposals'].update({r:buffered_initial['proposals'][r] for r in external_anchors
                                 if r in buffered_initial['proposals']})
    initial['buffer_anchor_claims']={r:buffered_initial['replayed_claims'][r] for r in external_anchors
                                     if r in buffered_initial['replayed_claims']}
    runs=collect_runs(row_spec,run_spec,grid,{r:v['total'] for r,v in buffer.items()})
    components=dict(buffer); components.update(region)
    result=apply_satellites(initial,components,runs,anchors,run_pair,
                            width=grid['width'],north=grid['north'],
                            max_satellite_cells=max_satellite_cells,max_gap_m=max_gap_m,
                            tie_m=tie_m,candidate_roots=set(region))
    if boo_root is not None:
        _require(result['proposals'].get(boo_root,{}).get('code')==22 and boo_root not in result['review'],
                 'Boo result conflicts with requested Oceania side')
    result['proposals']={r:p for r,p in result['proposals'].items() if r in region}
    result['anchor_discovery']=anchor_statistics
    result['anchor_source']={k:anchor_source[k] for k in ('source_id','source_version','sha256','country')} if anchor_source else None
    result['source_anchors']=anchors
    result['regional_roots']=len(region)
    result['buffer_roots']=len(buffer)
    result['line_id']=line_record['line_id']
    result['geometry_sha256']=line_record['geometry_sha256']
    result['component_input_sha256']={'rows':row_spec['sha256'],'runs':run_spec['sha256']}
    result['grid']=dict(grid)
    result['regional_bounds']=list(bounds)
    result['decision_revision']=compiled['revision']
    result['satellite_policy']={'max_satellite_cells':max_satellite_cells,'max_gap_m':max_gap_m,'tie_m':tie_m,
                                'metric':'WGS84 ellipsoidal component-center minimum'}
    result['status']='research-only-not-a-build'
    return result
