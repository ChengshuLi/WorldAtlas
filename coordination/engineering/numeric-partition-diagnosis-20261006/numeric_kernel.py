"""Bounded complete-pointset diagnosis; no coordinate alteration or tolerance."""
from shapely import union_all,get_dimensions
from shapely.geometry import shape,mapping
from shapely.errors import GEOSException,GeometryTypeError


def pointset(g):
    return {'geometry':mapping(g),'geometry_type':g.geom_type,'is_empty':g.is_empty,
            'is_valid':g.is_valid,'geometry_type_dimension':int(get_dimensions(g)),
            'nonempty_pointset_dimension':None if g.is_empty else int(get_dimensions(g)),
            'planar_area_coordinate_units_squared':g.area,'planar_length_coordinate_units':g.length}


def coverage(predicates,original,union,intersection,difference):
    result={'status':'unknown-predicate-or-overlay-disagreement',
            'method':'complete-input-predicate-and-complete-overlay-relation-consensus',
            'physical_status':'unverified','administrative_assignment':None,
            'historical_stage_identity':'unverified','cause_status':'unknown'}
    relation=predicates['original_relate_union']
    # For a nonempty pointset, no interior/boundary point outside the source
    # is the complete-input covered-by relation. This is a runtime predicate
    # observation, not an exact-arithmetic or historical-intermediate claim.
    matrix_covered=relation[2]=='F' and relation[5]=='F'
    matrix_disjoint=all(relation[i]=='F' for i in [0,1,3,4])
    agree=(predicates['union_covers_original']==predicates['original_covered_by_union']==matrix_covered and
           predicates['original_disjoint_union']==matrix_disjoint and
           predicates['original_intersects_union']==(not matrix_disjoint))
    result['direct_predicate_consensus']=agree
    if not agree:return result
    subset=((intersection.is_empty or original.covers(intersection)) and
            (difference.is_empty or original.covers(difference)) and
            (intersection.is_empty or union.covers(intersection)))
    result['overlay_complete_input_subset_checks']=subset
    if matrix_covered:
        supported=subset and difference.is_empty and intersection.equals(original)
        if supported:result['status']='literal-original-pointset-fully-covered-by-member-union'
    elif matrix_disjoint:
        supported=intersection.is_empty and difference.equals(original)
        if supported:result['status']='literal-original-pointset-disjoint-from-member-union'
    elif relation[0]=='2' and relation[2]=='2':
        supported=(subset and not intersection.is_empty and intersection.area>0 and
                   not difference.is_empty and difference.area>0 and difference.relate(union)[0]=='F')
        if supported:result['status']='literal-positive-area-overlap-and-outside-member-union'
    elif relation[0]=='F' and relation[2]=='2':
        supported=(subset and not intersection.is_empty and intersection.area==0 and
                   int(get_dimensions(intersection))<=1 and difference.equals(original))
        if supported:result['status']='literal-zero-area-source-contact'
    else:supported=False
    result['supported_complete_relation_checks']=supported
    return result


def diagnose(component_geometry,union_geometry,intersection_geometry,difference_geometry):
    row={'status':'unknown-unmeasured','physical_status':'unverified',
         'administrative_assignment':None,'cause_status':'unknown',
         'historical_stage_identity':'unverified','coverage_observation':{'status':'unknown-unmeasured'}}
    stage='read-complete-operands'
    try:
        original=shape(component_geometry);union=shape(union_geometry)
        intersection=shape(intersection_geometry);difference=shape(difference_geometry)
        if any(not g.is_valid for g in [original,union,intersection,difference]) or original.is_empty or union.is_empty or original.geom_type not in ['Polygon','MultiPolygon'] or union.geom_type not in ['Polygon','MultiPolygon']:
            row['status']='unknown-invalid-complete-operand';return row
        row['original_runtime_geometry']={k:v for k,v in pointset(original).items()if k!='geometry'}
        row['union_runtime_geometry']={k:v for k,v in pointset(union).items()if k!='geometry'}
        stage='reconstruct-stored-partition';partition=union_all([intersection,difference]);row['reconstructed_partition']=pointset(partition)
        stage='retain-original-minus-partition';lost=original.difference(partition);row['original_minus_partition']=pointset(lost)
        stage='retain-partition-minus-original';added=partition.difference(original);row['partition_minus_original']=pointset(added)
        stage='complete-input-and-reconstruction-predicates'
        predicates={'partition_equals_original':partition.equals(original),
                    'original_equals_partition':original.equals(partition),
                    'original_covers_partition':original.covers(partition),
                    'partition_covers_original':partition.covers(original),
                    'original_relate_partition':original.relate(partition),
                    'original_relate_union':original.relate(union),
                    'union_covers_original':union.covers(original),
                    'original_covered_by_union':original.covered_by(union),
                    'original_intersects_union':original.intersects(union),
                    'original_disjoint_union':original.disjoint(union)}
        row['predicates']=predicates
        stage='whole-shape-literal-coverage-consensus';row['coverage_observation']=coverage(predicates,original,union,intersection,difference)
        row['coordinate_area_arithmetic']={'original':original.area,'partition':partition.area,'original_minus_partition':lost.area,'partition_minus_original':added.area,'partition_minus_original_area_difference':partition.area-original.area}
        row['status']='complete-literal-reconstruction-diagnosis'
        if lost.is_empty and added.is_empty:reason='empty-overlay-remainders-despite-recorded-partition-disagreement'
        elif (not lost.is_empty and lost.area>0) or (not added.is_empty and added.area>0):reason='positive-coordinate-area-overlay-remainder'
        else:reason='nonempty-zero-coordinate-area-overlay-remainder'
        row['observed_reason']=reason
        row['causal_conclusion']='unresolved; these are complete runtime pointset/predicate observations'
        return row
    except (GEOSException,GeometryTypeError,ValueError,TypeError,KeyError,AttributeError)as error:
        row['status']='unknown-failed-diagnostic-operation';row['failed_stage']=stage;row['failure_class']=type(error).__name__
        row['coverage_observation']={'status':'unknown-failed-diagnostic-operation'};return row
