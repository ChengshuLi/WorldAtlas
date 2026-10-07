"""Required full query and nine-map replay; no new point-diagnostic campaign."""
from shapely.geometry import shape
from source import require


def execute(identity, loaded, records, validity, shifted):
    modules = loaded['modules']
    trace, kernel = modules['trace'], modules['kernel']
    feature = loaded['state']['candidates'][identity]
    row = loaded['physical'][identity][0]
    result = {'component_id': identity, 'original_query_count': len(row['query_relations']),
              'original_physical_unknowns': row.get('unresolved', []),
              'physical_authority': 'unapproved', 'repair_approval': False,
              'original_contradiction_claim_allowed': False}
    candidate = shape(feature['geometry'])
    if candidate.is_empty or not candidate.is_valid:
        return dict(result, status='unknown-invalid-candidate', actual_query_replays=[],
                    original_query_accounting='complete original physical row retained')
    try:
        queries, fresh_levels = trace.fresh_queries(candidate, row, records, validity, shifted)
        require(len(queries) == len(row['query_relations']), 'Incomplete ordered actual query replay')
        result['actual_query_replays'] = queries
        original_levels, unknowns = trace.original_levels(candidate, row, records, shifted)
        measured = modules['comparison'].alternating_support(candidate, original_levels)
        mappings = {key: kernel.ordinary_mapping(measured[key]) for key in kernel.RELATIONS}
        hierarchy = {key: kernel.ordinary_mapping(value) for key, value in
                     measured['hierarchy_disagreements'].items()}
        equal, hierarchy_equal, matched = trace.mapping_equality(mappings, hierarchy, row)
        result.update(status='original-mappings-matched' if matched else 'unknown-original-replay-mismatch',
                      complete_six_mappings=mappings, complete_three_hierarchy_mappings=hierarchy,
                      mapping_equality=equal, hierarchy_mapping_equality=hierarchy_equal,
                      original_positive_pieces={str(k): [kernel.ordinary_mapping(g) for g in original_levels[k]]
                                                for k in (1, 2, 3, 4)},
                      fresh_positive_pieces={str(k): [kernel.ordinary_mapping(g) for g in fresh_levels[k]]
                                             for k in (1, 2, 3, 4)},
                      retained_query_unknowns=unknowns,
                      original_contradiction_claim_allowed=False)
        return result
    except Exception as error:
        return dict(result, status='unknown-operation-failed', exception_type=type(error).__name__,
                    exception_message=str(error), original_query_accounting='complete original physical row retained')
