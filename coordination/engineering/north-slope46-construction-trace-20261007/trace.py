"""Observe literal original104 locals; no replacement polygon algorithm."""
import sys
from collections import defaultdict
from shapely.geometry import mapping,shape
from shapely.affinity import translate
from shapely import prepare
import reader
import kernel

RELATIONS=kernel.RELATIONS

def trace_operator(candidate,levels):
    operator=reader.old.comparison.alternating_support
    code=operator.__code__;events=[];locals_at_return={};previous=sys.gettrace()
    def hook(frame,event,arg):
        if event=='return' and frame.f_code is code:
            locals_at_return.update({k:frame.f_locals[k]for k in ('levels','violations','land','inland_water','exterior','footprint','missing','extra','overlap')if k in frame.f_locals})
        if event=='return' and frame.f_code.co_name in ('difference','intersection','union_all'):
            # Restrict observation to calls with the literal operator in ancestry;
            # decorator wrappers can have several levels between GEOS and caller.
            parent=frame.f_back;inside=False
            while parent:
                if parent.f_code is code:inside=True;operator_line=parent.f_lineno;break
                parent=parent.f_back
            if inside and hasattr(arg,'geom_type'):
                events.append({'call':frame.f_code.co_name,'original_operator_line':operator_line,'geometry':kernel.ordinary_mapping(arg)})
        return hook
    try:
        sys.settrace(hook);result=operator(candidate,levels)
    finally:sys.settrace(previous)
    if len(locals_at_return)!=9:raise ValueError('Missing literal method trace locals')
    return result,locals_at_return,events

def fresh_queries(candidate,row,sources,validity=None,shifted_cache=None):
    shifted_cache={}if shifted_cache is None else shifted_cache
    result=[];levels=defaultdict(list)
    for ordinal,query in enumerate(row['query_relations']):
        meta,source=sources[query['source_id']];reader.query_bind(query,meta)
        offset=query['periodic_offset'];key=(meta['id'],offset)
        if key not in shifted_cache:
            shifted_cache[key]=translate(source,xoff=offset)if offset else source;prepare(shifted_cache[key])
        shifted=shifted_cache[key]
        fresh,piece=reader.old.comparison.relation(candidate,shifted,meta['id'],offset,validity)
        # Original container outcomes are independently retained context; this is
        # source/candidate relation replay, never a new global container test.
        keys=('status','source_covers_candidate','candidate_covers_source','intersects','disjoint','witness','witness_geometry')
        equal={k:reader.canonical(fresh.get(k))==reader.canonical(query.get(k))for k in keys}
        if fresh['status']=='checked' and piece is not None and not piece.is_empty:
            polygons,contacts=reader.old.dimensional_parts(piece);levels[meta['level']].extend(polygons)
        result.append({'ordinal':ordinal,'original':query,'fresh':fresh,'source_original_meta':meta,
                       'whole_original_source_geometry':kernel.ordinary_mapping(source),
                       'whole_periodic_source_geometry':kernel.ordinary_mapping(shifted),
                       'exact_relation_fields_equal':equal,'unknowns_retained':query.get('container_chain_issues',[])})
    return result,levels

def mapping_equality(mappings,hierarchy,row):
    equality={key:reader.canonical(mappings[key])==reader.canonical(row['complete_support'][key]['geometry'])for key in RELATIONS}
    hierarchy_equal={key:reader.canonical(value)==reader.canonical(row['complete_support']['hierarchy_disagreements'][key]['geometry'])for key,value in hierarchy.items()}
    return equality,hierarchy_equal,all(equality.values())and all(hierarchy_equal.values())


def execute(feature,row,sources,validity=None,shifted_cache=None):
    candidate=shape(feature['geometry'])
    record={'component_id':feature['id'],'whole_candidate_feature':feature,'original_physical_row':row,
            'physical_authority':'unapproved','repair_approval':False}
    if candidate.is_empty or not candidate.is_valid:
        return dict(record,status='unknown-invalid-candidate',query_replays=[],stage_pointsets={},mapping_equality={},point_diagnostics={})
    try:
        queries,fresh_levels=fresh_queries(candidate,row,sources,validity,shifted_cache)
        levels,retained=kernel.reconstruct_levels(candidate,row)
        record.update(query_replays=queries,ordered_original_positive_pieces={str(k):[kernel.ordinary_mapping(g)for g in levels[k]]for k in (1,2,3,4)},ordered_fresh_positive_pieces={str(k):[kernel.ordinary_mapping(g)for g in fresh_levels[k]]for k in (1,2,3,4)},retained_query_unknowns=retained)
        measured,local,events=trace_operator(candidate,levels)
        mappings={key:kernel.ordinary_mapping(measured[key])for key in RELATIONS}
        hierarchy={key:kernel.ordinary_mapping(value)for key,value in measured['hierarchy_disagreements'].items()}
        equality,hierarchy_equal,replay_equal=mapping_equality(mappings,hierarchy,row)
        stages={key:({str(k):kernel.ordinary_mapping(v)for k,v in value.items()}if isinstance(value,dict)else kernel.ordinary_mapping(value))for key,value in local.items()}
        probes={key:kernel.point_diagnostics(candidate,measured[key])for key in RELATIONS[3:]}if replay_equal else {}
        record.update(status='original-mappings-matched'if replay_equal else 'unknown-original-replay-mismatch',
            query_replays=queries,ordered_original_positive_pieces={str(k):[kernel.ordinary_mapping(g)for g in levels[k]]for k in (1,2,3,4)},
            ordered_fresh_positive_pieces={str(k):[kernel.ordinary_mapping(g)for g in fresh_levels[k]]for k in (1,2,3,4)},
            retained_query_unknowns=retained,stage_pointsets=stages,original_operation_return_events=events,
            complete_six_mappings=mappings,complete_three_hierarchy_mappings=hierarchy,mapping_equality=equality,hierarchy_mapping_equality=hierarchy_equal,
            point_diagnostics=probes,original_contradiction_claim_allowed=replay_equal)
        return record
    except Exception as error:
        return dict(record,status='unknown-operation-failed',exception_type=type(error).__name__,exception_message=str(error),original_contradiction_claim_allowed=False)
