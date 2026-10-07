"""Bounded full-row semantic/transport tampering controls for the final reader."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
from shapely.geometry import shape
import kernel
import reader
import verify

def rejects(action):
    try:action()
    except (ValueError,KeyError):return
    raise AssertionError('Rehashed semantic mutation accepted')

def main():
    results=[]
    cases=json.loads((verify.HERE/'six-retained-control-inputs.json').read_bytes())['witnesses']
    for case in cases:
        identity=case['component_id'];original=case['complete_original_scientific_row']
        candidate=case['complete_candidate'];pin={'row':0,'fixture':'complete-retained-six-case'}
        routing=dict(current_feature_sha256=reader.digest(reader.canonical(candidate)),
            current_geometry_sha256=reader.digest(reader.canonical(candidate['geometry'])),
            family='fixture-family',operational_batch='fixture-batch',unresolved=['source-unapproved'],
            source_fitness_prerequisite='source-before-repair')
        state=dict(routing={identity:routing},candidates={identity:candidate},
                   scope={'routing_source':{'whole_components_raw_sha256':'0'*64,'actual_merge':'0198938719a5666b6726fb6a1e45779926eefeb2'}})
        actual=kernel.replay(shape(candidate['geometry']),original,reader.old.comparison.alternating_support)
        db=sqlite3.connect(':memory:');db.execute('create table objects (sha text primary key,body blob)')
        for field in ('complete_geometry_mappings','complete_hierarchy_mappings'):
            refs={}
            for name,geometry in actual[field].items():
                body=reader.canonical(geometry);digest=reader.digest(body)
                db.execute('insert or ignore into objects values (?,?)',(digest,body))
                refs[name]=dict(geometry_sha256=digest,complete_pointset_family='geometry-objects')
            actual[field]=refs
        actual.update(verify.bindings(state,identity,original,pin))
        def check(row):verify.validate_result(row,state,identity,original,pin,db)
        check(actual);results.append('whole-six-case-positive:'+identity)
        def mutation(name,change):
            altered=copy.deepcopy(actual);change(altered);rejects(lambda:check(altered));results.append(name+':'+identity)
        mutation('source-vintage-binding',lambda row:row.update(original_source_vintage={'false':'vintage'}))
        mutation('whole-current-feature-binding',lambda row:row.update(full_current_feature_sha256='f'*64))
        mutation('complete-query-context',lambda row:row.update(query_count=row['query_count']+1))
        mutation('equality-false-promotion',lambda row:row['geometry_byte_container_equality'].update(extra_reconstruction=False))
        mutation('geometry-object-missing',lambda row:row['complete_geometry_mappings']['extra_reconstruction'].update(geometry_sha256='f'*64))
        mutation('physical-authority-promotion',lambda row:row.update(physical_authority='approved'))
        mutation('unknown-loss',lambda row:row.update(original_unknowns=['false-replacement']))
        for relation,probe in actual['point_diagnostics'].items():
            if probe['status']=='diagnostic' and probe['triangles']:
                mutation('rational-centroid-tamper',lambda row:rational_mutation(row,relation))
                mutation('query-roster-omission',lambda row:row['point_diagnostics'][relation]['triangles'].pop())
                break
        if case is cases[0]:
            mismatch=copy.deepcopy(actual)
            changed={'type':'Polygon','coordinates':[[[0.0,0.0],[1.0,0.0],[0.0,1.0],[0.0,0.0]]]}
            body=reader.canonical(changed);digest=reader.digest(body)
            db.execute('insert or ignore into objects values (?,?)',(digest,body))
            mismatch['complete_geometry_mappings']['mapped_land_support']['geometry_sha256']=digest
            mismatch['geometry_byte_container_equality']['mapped_land_support']=False
            mismatch.update(status='original-replay-mismatch',point_diagnostics={},demonstrated_local_contradictions=[],
                conservative_class='retained-unresolved-original-replay-mismatch',
                next_action='engineering-original-container-or-numerical-replay-mismatch-diagnosis')
            check(mismatch);results.append('rehashed-fresh-mismatch-honest-unknown-positive')
            promoted=copy.deepcopy(mismatch);promoted['status']='replayed'
            rejects(lambda:check(promoted));results.append('rehashed-fresh-mismatch-promotion-rejected')
        db.close()
    with tempfile.TemporaryDirectory(prefix='verification-controls-',dir=verify.HERE/'.cache') as temporary:
        root=Path(temporary);(root/'report.json').write_bytes(reader.canonical({'outputs':[]}))
        verify.read_report(root);results.append('ordinary-empty-transport-fixture-positive')
        (root/'undeclared.bin').write_bytes(b'complete unexpected body')
        rejects(lambda:verify.read_report(root));results.append('unindexed-whole-output-rejected')
        (root/'undeclared.bin').unlink();(root/'report.json').unlink()
        (root/'report.json').symlink_to(verify.HERE/'six-retained-control-inputs.json')
        rejects(lambda:verify.read_report(root));results.append('report-symlink-rejected')
    print(json.dumps(dict(status='PASS',count=len(results),controls=results,
        limits=['Six bounded retained actual-case operator/helper replays, not complete world execution.',
                'Temporary fixture row refs are controls only; original source/body custody remains final whole-reader duty.']),sort_keys=True))

def rational_mutation(row,relation):
    value=row['point_diagnostics'][relation]['triangles'][0]['exact_rational_centroid'][0]
    value['numerator']=str(int(value['numerator'])+1)

if __name__=='__main__':main()
