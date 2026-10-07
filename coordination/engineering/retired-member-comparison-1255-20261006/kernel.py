"""Literal full-pointset diagnostics. No historical stage or physical attribution."""
from shapely import union_all
from shapely.errors import GEOSException
from shapely.geometry import shape,mapping


def pointset(g):
    return {'geometry':mapping(g),'geometry_type':g.geom_type,'is_empty':g.is_empty,
            'is_valid':g.is_valid,'planar_area_coordinate_units_squared':g.area,
            'planar_length_coordinate_units':g.length}


def member_union(records):
    invalid=[]; geoms=[]
    for r in records:
        try:
            g=shape(r['geometry'])
            if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon'):
                invalid.append({'id':r['id'],'status':'invalid-empty-or-nonpolygon-original-member'})
            else: geoms.append(g)
        except (GEOSException,ValueError,TypeError,KeyError) as e:
            invalid.append({'id':r['id'],'status':'failed-original-member-read','failure_class':type(e).__name__})
    if invalid: return {'status':'unknown-invalid-original-member','invalid_members':invalid},None
    try:
        u=union_all(geoms)
        if not u.is_valid: return {'status':'unknown-invalid-member-union','union':pointset(u)},None
        return {'status':'literal-original-member-union','union':pointset(u)},u
    except GEOSException as e:
        return {'status':'unknown-failed-member-union','failure_class':type(e).__name__},None


def compare(component,union):
    row={'component':component['id'],'status':'unknown-unmeasured','physical_status':'unverified',
         'administrative_assignment':None,'cause_status':'unknown','historical_stage_identity':'unverified'}
    if union is None:
        row['status']='unknown-original-member-union'; return row
    try:
        g=shape(component['geometry'])
        if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon'):
            row['status']='unknown-invalid-empty-or-nonpolygon-component'; return row
        ix=g.intersection(union); diff=g.difference(union)
        row['intersection']=pointset(ix); row['difference']=pointset(diff)
        if not ix.is_valid or not diff.is_valid:
            row['status']='unknown-invalid-operation-output'; return row
        rebuilt=union_all([ix,diff])
        row['partition_equals_original']=rebuilt.equals(g)
        row['original_planar_area_coordinate_units_squared']=g.area
        row['intersection_plus_difference_area']=ix.area+diff.area
        row['area_arithmetic_delta']=(ix.area+diff.area)-g.area
        # Exact topological equality is a diagnostic, not a tolerance-based repair.
        # Never classify unexplained numerical disagreement as physical absence.
        if not row['partition_equals_original']:
            row['status']='unknown-numerical-partition-disagreement'; return row
        row['member_union_covers_component']=union.covers(g)
        if ix.is_empty: row['status']='no-original-member-intersection-in-literal-domain'
        elif ix.area==0: row['status']='zero-area-original-member-contact'
        elif union.covers(g): row['status']='original-member-union-covers-component'
        else: row['status']='positive-area-partial-original-member-coverage'
        return row
    except GEOSException as e:
        row['status']='unknown-failed-component-operation';row['failure_class']=type(e).__name__;return row
