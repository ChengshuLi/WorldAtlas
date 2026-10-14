"""Bound complete foreign-neighbor disjointness with unchanged exact predicates.
No overlays, coordinate changes, tolerance, or source approval are introduced.
"""
import hashlib
import json
import pathlib
import resource
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[4]
OWN = 'coordination/engineering/vnm-visible-one-20261014/'
CONTEXT = OWN + 'vintages/vnm-current-neighbors-001/result.json'
CANDIDATES = OWN + 'custody/original-components.json'
TARGETS = ['gb:VNM:ADM2:81297802B85934029741785']

def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def main():
    head, vintage = sys.argv[1:]
    if git('rev-parse', 'HEAD').decode().strip() != head:
        raise ValueError('Exact execution HEAD required')
    script = pathlib.Path(__file__).relative_to(ROOT).as_posix()
    names = [script, 'scripts/evidence/immutable.py', 'scripts/evidence/exact_predicates.py', CONTEXT, CANDIDATES]
    inputs = [{'path': p, 'bytes': len(raw), 'sha256': sha(raw), 'hash_kind': 'file-bytes'} for p in names for raw in [git('show', head + ':' + p)]]
    helper = git('show', head + ':scripts/evidence/immutable.py')
    ns = {'__name__': 'immutable', '__file__': str(ROOT / 'scripts/evidence/immutable.py')}
    exec(compile(helper, ns['__file__'], 'exec'), ns)
    base = ns['Baseline'](ROOT, head, inputs)
    destination = ns['NewVintage'](base,OWN,vintage,['result.json'])
    if base.materialized_bytes(script) != git('show', head + ':' + script):
        raise ValueError('Executing code drift')
    predicates = base.load_modules({'exact_predicates': 'scripts/evidence/exact_predicates.py'})['exact_predicates']
    def disjoint(first, second):
        a, b = predicates.prepare_geometry(first), predicates.prepare_geometry(second)
        sa = [(p,q) for poly in a for ring in poly for p,q in zip(ring,ring[1:])]
        sb = [(p,q) for poly in b for ring in poly for p,q in zip(ring,ring[1:])]
        if len(sa)*len(sb) > predicates.MAX_PAIR_CHECKS:
            raise ValueError('Existing exact pair budget exceeded')
        contacts = sum(predicates.segment_contacts(p,q,r,s) for p,q in sa for r,s in sb)
        a_states = [predicates.geometry_state(poly[0][0],b) for poly in a]
        b_states = [predicates.geometry_state(poly[0][0],a) for poly in b]
        return {'boundary_contacts': contacts, 'cross_segment_checks': len(sa)*len(sb),
                'first_shell_states': a_states, 'second_shell_states': b_states,
                'strictly_disjoint': contacts == 0 and all(s == 'outside' for s in a_states+b_states)}
    triangle = lambda x,y,k: {'type':'Polygon','coordinates':[[[x,y],[x+k,y],[x,y+k],[x,y]]]}
    controls = {'same_polygon': disjoint(triangle(0,0,1),triangle(0,0,1)),
                'contained_polygon': disjoint(triangle(1,1,1),triangle(0,0,10)),
                'separate_polygons': disjoint(triangle(0,0,1),triangle(3,3,1))}
    if controls['same_polygon']['strictly_disjoint'] or controls['contained_polygon']['strictly_disjoint'] or not controls['separate_polygons']['strictly_disjoint']:
        raise ValueError('Exact predicate controls failed')
    current = json.loads(base.pinned_bytes(CONTEXT))
    candidates = json.loads(base.pinned_bytes(CANDIDATES))
    if [c['id'] for c in candidates] != current['scopeIds'] or len(candidates) != 1:
        raise ValueError('Complete original scope mismatch')
    results = []
    started = time.monotonic()
    for candidate,row,target in zip(candidates,current['rows'],TARGETS):
        if row['component_id'] != candidate['id'] or sum(n['feature']['id']==target for n in row['candidate_neighbors']) != 1:
            raise ValueError('Candidate-target join mismatch')
        for neighbor in row['candidate_neighbors']:
            if neighbor['feature']['id'] == target:
                continue
            proof = disjoint(candidate['geometry'], neighbor['feature']['geometry'])
            results.append({'component_id':candidate['id'], 'foreign_id':neighbor['feature']['id'],
                'candidate_geometry_sha256':sha(ns['canonical_json'](candidate['geometry'])),
                'foreign_geometry_sha256':sha(ns['canonical_json'](neighbor['feature']['geometry'])), **proof})
    if len(results) != 1 or not all(r['strictly_disjoint'] for r in results):
        raise ValueError('Foreign current-neighbor exclusion not established')
    output={'execution_commit':head,'inputs':inputs,'source_neighbor_context':CONTEXT,
        'results':results,'controls':controls,'elapsed_seconds':time.monotonic()-started,
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'method':'Existing exact binary64 ring validation, every cross-boundary segment contact, and both-direction shell membership. Valid finite polygons with no boundary contact and all shell witnesses outside are strictly disjoint.',
        'limits':['Original exact binary64 values only; no physical truth, authority or source precision claim.','Target applicability, native exclusion and selected conservation remain separate.']}
    if output['peak_rss_bytes'] > 512*1024**2:
        raise ValueError('Metadata predicate process reservation exceeded')
    destination.publish({'result.json':output})
    print(json.dumps({'foreign_neighbors':len(results),'strictly_disjoint':True,'elapsed_seconds':output['elapsed_seconds'],'peak_rss_bytes':output['peak_rss_bytes']}))

if __name__ == '__main__':
    main()
