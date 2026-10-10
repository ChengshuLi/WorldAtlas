"""Exact diagnostic source fit. No attribution, repair, normalization or snap."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types

HERE = 'research/geography/turkmenistan32-source-fit-20261010/'

def git(repo, commit, path):
    return subprocess.check_output(['git', '-C', repo, 'show', commit + ':' + path])

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo', required=True)
    p.add_argument('--commit', required=True)
    p.add_argument('--run', required=True)
    a = p.parse_args()
    repo = str(Path(a.repo).resolve())
    code = git(repo, a.commit, HERE + 'probe.py')
    if code != Path(__file__).read_bytes():
        raise ValueError('Actually executing probe differs from immutable code')
    raw = git(repo, a.commit, 'scripts/evidence/immutable.py')
    module = types.ModuleType('pinned_immutable')
    module.__file__ = repo + '/scripts/evidence/immutable.py'
    exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    plan_raw = git(repo, a.commit, HERE + 'probe-plan.json')
    plan = json.loads(plan_raw)
    pins = plan['files'] + [module.descriptor(HERE+'probe-plan.json', plan_raw)]
    baseline = module.Baseline(repo, a.commit, pins, max_phase_bytes=64*1024*1024)
    baseline.pinned_bytes(HERE+'probe.py')
    baseline.pinned_bytes('scripts/evidence/immutable.py')
    output = module.NewVintage(baseline, HERE, a.run, ['fit.json', 'fragments.json'])
    if hashlib.sha256(Path(sys.executable).resolve().read_bytes()).hexdigest() != plan['runtime']['python_executable_sha256']:
        raise ValueError('Python executable changed')
    import numpy
    import shapely
    from shapely.geometry import shape, mapping
    if (shapely.__version__, shapely.geos_version_string, numpy.__version__) != ('2.1.2', '3.13.1', '2.3.5'):
        raise ValueError('Runtime versions changed')
    def load(path):
        raw = baseline.pinned_bytes(path)
        if path.endswith('.gz'):
            with gzip.GzipFile(fileobj=__import__('io').BytesIO(raw)) as stream:
                decoded = stream.read(module.MAX_FILE_BYTES+1)
            baseline.admit('decoded:' + path, len(decoded))
            raw = decoded
        return json.loads(raw)
    scope = load(HERE+'scope.json')
    investigations = load(plan['investigations_path'])
    row = next(r for r in investigations if r['component'] == plan['component_id'])
    bindings = row['original_fragment_bindings']
    if 'physical-component:'+module.sha256(module.canonical_json(bindings)) != row['component']:
        raise ValueError('Original full component identity mismatch')
    candidate_features = load(plan['candidate_path'])['features']
    found = {f['id']: f for f in candidate_features if f['id'] in {r['id'] for r in bindings}}
    if len(found) != len(bindings):
        raise ValueError('Missing exact candidate fragment')
    for b in bindings:
        if module.sha256(module.canonical_json(found[b['id']])) != b['feature_sha256']:
            raise ValueError('Original fragment feature changed')
    source = load(plan['source_path'])['features']
    source_ids = [f['properties']['shapeID'] for f in source]
    if len(source_ids) != len(set(source_ids)) or len(source_ids) != 59:
        raise ValueError('Complete retained source roster changed')
    targets = load('data/geography/part-23.json')['features']
    selected = {f['id']: f for f in targets if f['id'] in scope['contacts']}
    if set(selected) != set(scope['contacts']):
        raise ValueError('Current source-contact identities incomplete')
    for identity, f in selected.items():
        m = f['properties']['metadata']
        if m['original_id'] != identity.split(':')[-1] or m['source_id'] != 'gb:TKM:ADM2':
            raise ValueError('Source identity join failed')
        if f['properties']['parent_id'] != 'framework:province:ahai:4b56bb7706fe':
            raise ValueError('Parent changed')
    def geom(f):
        g = shape(f['geometry'])
        if g.is_empty or not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon'):
            raise ValueError('Invalid unchanged input geometry')
        if not all(math.isfinite(v) for v in g.bounds):
            raise ValueError('Nonfinite geometry')
        return g
    sources = [(f['properties']['shapeID'], geom(f)) for f in source]
    current = [(i,geom(f)) for i,f in selected.items()]
    results=[]
    for identity,f in sorted(found.items()):
        g=geom(f)
        def evaluate(rows):
            result=[]
            for i,s in rows:
                intersection=s.intersection(g)
                difference=g.difference(s)
                result.append({'id':i,'covers_fragment':s.covers(g),'interiors_disjoint':s.relate_pattern(g,'F********'),
                  'intersection_empty':intersection.is_empty,'intersection_planar_degrees2':intersection.area,
                  'fragment_minus_source_empty':difference.is_empty})
            return result
        results.append({'fragment_id':identity,'bounds':list(g.bounds),'source_fit':evaluate(sources),'six_recorded_current_contacts_fit':evaluate(current)})
    source_current=[]
    for i,g in current:
        s=next(s for sid,s in sources if sid==i.split(':')[-1])
        source_current.append({'id':i,'current_parent':selected[i]['properties']['parent_id'],
          'current_owner':selected[i]['properties']['reference_owner'],'equals_topologically':s.equals(g),
          'source_minus_current_empty':s.difference(g).is_empty,'current_minus_source_empty':g.difference(s).is_empty})
    report={'component_id':row['component'],'component_count_tested':1,'family_count':32,'original_batch_count':441,
            'fragment_count':len(found),'retained_fragment_area_m2':row['measured_fragment_area_sum_m2'],
            'source_product_feature_count':len(source),'source_current':source_current,'fragments':results,
            'baseline_commit':a.commit,'runtime':{'python':sys.version,'shapely':shapely.__version__,'geos':shapely.geos_version_string,'numpy':numpy.__version__},
            'consumed_inputs':baseline.consumed,'limits':['Exact fit diagnostic only; no administrative authority or water classification.',
            'Six current source contacts are checked; this first probe is not a complete current-neighbor or native-grid acceptance.',
            'Retained area is inherited, not recomputed. Planar degrees squared are GEOS diagnostic units, not land area.',
            'No buffer, snapping, normalization, tolerance, MakeValid or full-resolution source substitution.']}
    output.publish({'fit.json':report,'fragments.json':{'type':'FeatureCollection','features':list(found.values())}})
    print(json.dumps({'run':str(output.root),'component':row['component'],'fragments':len(found)}))

if __name__ == '__main__':
    main()
