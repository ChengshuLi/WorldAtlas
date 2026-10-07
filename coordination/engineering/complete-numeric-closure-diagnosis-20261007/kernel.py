"""Literal original operator plus bounded exact point diagnostics; never a repair."""
from collections import defaultdict
import json
from shapely.geometry import Point, mapping, shape
import exact_predicates as exact

RELATIONS = ('mapped_land_support', 'mapped_inland_water_support',
             'outside_mapped_L1_context', 'missing_reconstruction',
             'extra_reconstruction', 'contradictory_land_water_support')

def ordinary_mapping(geometry):
    # JSON changes containers only; every binary64 coordinate is preserved.
    return json.loads(json.dumps(mapping(geometry), allow_nan=False))

def polygon_members(geometry):
    if geometry.geom_type=='Polygon':
        return [geometry] if not geometry.is_empty else []
    if geometry.geom_type in ('MultiPolygon','GeometryCollection'):
        return [member for part in geometry.geoms for member in polygon_members(part)]
    return []

def reconstruct_levels(candidate, row):
    """Preserve original query ordering and use every retained positive piece."""
    levels=defaultdict(list)
    retained=[]
    for ordinal, query in enumerate(row['query_relations']):
        level=query.get('source_level')
        if level not in (1,2,3,4):
            retained.append(dict(ordinal=ordinal,disposition='unknown-level',query=query))
            continue
        if query.get('status')!='checked':
            retained.append(dict(ordinal=ordinal,disposition='original-query-unknown',query=query))
            continue
        if query.get('source_covers_candidate') is True and query.get('witness')=='complete-candidate-reconstruction':
            pieces=polygon_members(candidate)
        elif 'witness_geometry' in query:
            geometry=shape(query['witness_geometry'])
            pieces=polygon_members(geometry) if not geometry.is_empty and geometry.area>0 else []
            if not pieces:
                retained.append(dict(ordinal=ordinal,disposition='empty-nonpolygon-or-nonpositive-context',query=query))
        else:
            pieces=[]
            retained.append(dict(ordinal=ordinal,disposition='no-materialized-positive-piece',query=query))
        levels[level].extend(pieces)
    return levels,retained

def point_diagnostics(candidate, residue):
    result={'helper_version':exact.VERSION,'original_point_domain':'IEEE754-binary64-as-exact-rational',
            'derived_point_domain':'exact-rational-centroid-of-original-binary64-triangle',
            'whole_component_certification':False,'partition_repair_approval':False,
            'vertices':[],'triangles':[],'nontriangle_polygons':[]}
    try:
        gp=exact.prepare_geometry(ordinary_mapping(candidate))
        rp=exact.prepare_geometry(ordinary_mapping(residue))
        segments=sum(len(ring)-1 for polygon in gp for ring in polygon)
        residue_segments=sum(len(ring)-1 for polygon in rp for ring in polygon)
        query_cost=max(segments,residue_segments)
        batch_size=min(exact.MAX_POINTS,exact.MAX_POINT_SEGMENT_CHECKS//max(1,query_cost))
        if batch_size<1:
            exact.reject('point-segment-budget-exceeded','unsupported')
        queries=[]
        for pi, polygon in enumerate(rp):
            for ri, ring in enumerate(polygon):
                for vi,p in enumerate(ring[:-1]):
                    queries.append(('vertex',pi,ri,vi,p))
            if len(polygon)==1 and len(polygon[0])==4:
                p=tuple(sum(v[i] for v in polygon[0][:-1])/3 for i in (0,1))
                if exact.orientation(*polygon[0][:-1])==0:
                    exact.reject('zero-exact-triangle-area')
                queries.append(('triangle',pi,None,None,p))
            else:
                result['nontriangle_polygons'].append(dict(polygon=pi,interior_witness='not-certified'))
        batches=[]
        for start in range(0,len(queries),batch_size):
            selected=queries[start:start+batch_size]
            if len(selected)>exact.MAX_POINTS or len(selected)*query_cost>exact.MAX_POINT_SEGMENT_CHECKS:
                raise ValueError('Deterministic query batch exceeded unchanged helper bounds')
            batches.append(dict(start=start,count=len(selected),maximum_segments=query_cost,
                                point_segment_work_bound=len(selected)*query_cost))
            for kind,pi,ri,vi,p in selected:
                candidate_state=exact.geometry_state(p,gp)
                residue_state=exact.geometry_state(p,rp)
                if kind=='vertex':
                    floating=Point(float(p[0]),float(p[1]))
                    result['vertices'].append(dict(polygon=pi,ring=ri,vertex=vi,
                        exact_candidate_state=candidate_state,exact_residue_state=residue_state,
                        binary64_point=[float(p[0]),float(p[1])],
                        floating_candidate_covers=bool(candidate.covers(floating)),
                        floating_candidate_contains=bool(candidate.contains(floating)),
                        floating_residue_covers=bool(residue.covers(floating))))
                else:
                    own_state=exact.geometry_state(p,[rp[pi]])
                    result['triangles'].append(dict(polygon=pi,
                        exact_rational_centroid=[exact.rational(x) for x in p],
                        exact_candidate_state=candidate_state,exact_residue_state=residue_state,
                        exact_triangle_state=own_state,
                        interior_witness_certified=own_state=='inside' and residue_state=='inside',
                        floating_observation='not-computed-for-derived-rational-point'))
        result.update(status='diagnostic',query_batches=batches,complete_query_count=len(queries))
    except exact.DiagnosticError as error:
        result.update(status=error.status,reason=error.reason)
    except Exception as error:
        result.update(status='unknown-operation-failed',exception_type=type(error).__name__,exception_message=str(error))
    return result

def replay(candidate,row,operator):
    levels,retained=reconstruct_levels(candidate,row)
    result={'retained_query_context':retained,'query_count':len(row['query_relations']),
            'complete_level_piece_counts':{str(k):len(levels[k]) for k in (1,2,3,4)},
            'original_unknowns':row.get('unresolved',[]),
            'physical_authority':'unapproved','partition_recovery':'not-certified'}
    try:
        measured=operator(candidate,levels)
        geometries={key:ordinary_mapping(measured[key]) for key in RELATIONS}
        hierarchy={key:ordinary_mapping(value) for key,value in measured['hierarchy_disagreements'].items()}
        equals={key:geometries[key]==row['complete_support'][key]['geometry'] for key in RELATIONS}
        old_hierarchy=row['complete_support']['hierarchy_disagreements']
        hierarchy_equals={key:geometry==old_hierarchy[key]['geometry'] for key,geometry in hierarchy.items()}
        probes={key:point_diagnostics(candidate,measured[key]) for key in RELATIONS[3:]}
        for key,value in measured['hierarchy_disagreements'].items():
            probes[key]=point_diagnostics(candidate,value)
        contradictions=[]
        for relation,diagnosis in probes.items():
            for witness in diagnosis['triangles']:
                state=witness['exact_candidate_state']
                if witness['interior_witness_certified'] and ((relation=='extra_reconstruction' and state=='inside') or (relation=='missing_reconstruction' and state=='outside')):
                    contradictions.append(dict(relation=relation,polygon=witness['polygon'],candidate_state=state,
                        evidence='certified-exact-rational-residue-triangle-interior'))
        result.update(status='replayed',complete_geometry_mappings=geometries,
            complete_hierarchy_mappings=hierarchy,geometry_byte_container_equality=equals,
            hierarchy_geometry_equality=hierarchy_equals,point_diagnostics=probes,
            demonstrated_local_contradictions=contradictions,
            conservative_class='local-construction-contradiction-demonstrated' if contradictions else 'retained-unresolved-numerical-or-context-prerequisite',
            next_action='engineering-source-preserving-numerical-operation-correction' if contradictions else 'engineering-or-source-diagnosis-of-retained-unknowns')
    except Exception as error:
        result.update(status='unknown-replay-failed',exception_type=type(error).__name__,exception_message=str(error),
            conservative_class='retained-unresolved-replay-failure',next_action='engineering-original-operation-failure-diagnosis')
    return result
