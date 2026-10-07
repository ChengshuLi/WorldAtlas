"""Complete26276 original-operation and exact witness diagnosis, not repair."""
import argparse
from collections import Counter,defaultdict
import datetime
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

import numpy
import pyproj
import shapely
from shapely.geometry import shape
import reader
import kernel

HERE=Path(__file__).resolve().parent
OWNED='coordination/engineering/complete-numeric-closure-diagnosis-20261007/'
CODE=('diagnose.py','reader.py','kernel.py','exact_predicates.py','input-index.json',
      'scope.json.gz','module-provenance.json','legacy/producer.py','legacy/comparison.py',
      'legacy/inputs.py','legacy/immutable.py','legacy/ellipsoidal_area.py',
      'legacy/input-config.json','legacy/transport.py','legacy/run.py')

def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.PIPE)

def output_guard(repo,output):
    if not output.is_absolute() or '..' in output.parts or not output.resolve().is_relative_to(HERE/'.cache') or output.exists():
        raise ValueError('Require absent absolute output under owned cache')
    for part in (output,*output.parents):
        if part.is_symlink():raise ValueError('Symlink output ancestor')
        if part==repo:break

def authenticate(repo,commit):
    if re.fullmatch('[a-f0-9]{40}',commit) is None:
        raise ValueError('Exact lowercase40hex execution commit required before Git')
    if git(repo,'rev-parse','HEAD').decode().strip()!=commit:
        raise ValueError('Declared execution is not actualHEAD')
    rows=[]
    for name in CODE:
        path=reader.safe_path(HERE,name);raw=path.read_bytes()
        expected=git(repo,'show',commit+':'+OWNED+name)
        if raw!=expected:raise ValueError('Changed executed code/config: '+name)
        rows.append(dict(path=OWNED+name,bytes=len(raw),sha256=reader.digest(raw)))
    for module in list(sys.modules.values()):
        selected=getattr(module,'__file__',None)
        if not selected:continue
        path=Path(selected).resolve()
        if path.is_relative_to(HERE) and path.suffix=='.py':
            name=str(path.relative_to(HERE))
            if name not in CODE:raise ValueError('Undeclared actual imported project module: '+name)
    modules=json.loads((HERE/'module-provenance.json').read_bytes())
    for row in modules:
        actual=reader.safe_path(HERE,row['path']).read_bytes()
        if reader.digest(actual)!=row['sha256'] or len(actual)!=row['bytes']:
            raise ValueError('Altered whole original helper')
        if actual!=git(repo,'show',row['original_commit']+':'+row['original_path']):
            raise ValueError('Original helper provenance differs')
    versions=dict(python=platform.python_version(),numpy=numpy.__version__,shapely=shapely.__version__,
                  geos=shapely.geos_version_string,pyproj=pyproj.__version__)
    if versions!=dict(python='3.12.14',numpy='2.3.5',shapely='2.1.2',geos='3.13.1',pyproj='3.7.2'):
        raise ValueError('Unpinned actual science runtime')
    return rows,versions

class Objects:
    def __init__(self,products):
        self.products=products;self.seen=set()
    def retain(self,geometry):
        raw=reader.canonical(geometry);identity=reader.digest(raw)
        if identity not in self.seen:
            self.products.emit('geometry-objects',dict(geometry_sha256=identity,geometry=geometry))
            self.seen.add(identity)
        return dict(geometry_sha256=identity,complete_pointset_family='geometry-objects')

def run(repo,commit,output,input_only=False):
    if re.fullmatch('[a-f0-9]{40}',commit) is None:
        raise ValueError('Exact lowercase40hex execution commit required')
    output_guard(repo,output)
    started=utc();monotonic=time.monotonic()
    code,runtime=authenticate(repo,commit)
    state=reader.load(repo)
    # Complete original rows/context/candidate bindings before any output or overlay.
    observed=set()
    for identity,row,pin in reader.physical_rows(state):
        if identity in observed:raise ValueError('Duplicate original numeric physical row')
        observed.add(identity)
    if observed!=set(state['routing']):raise ValueError('Incomplete original numeric row closure')
    if input_only:
        print(json.dumps(dict(status='PASS',kind='input-only complete custody/bijection; no original operator replay or point diagnosis',
            complete_current=95173,numeric=26276,complement=68897,families=3503,batches=253,
            input_files=len(state['receipts']),input_bytes=sum(x['bytes'] for x in state['receipts']),
            actual_code_commit=commit,actual_runtime=runtime,code=code,output_created=output.exists()),sort_keys=True))
        return
    products=reader.old.Products(output)
    objects=Objects(products);counts=Counter();families=defaultdict(list);batches=defaultdict(list)
    for number,(identity,row,pin) in enumerate(reader.physical_rows(state),1):
        candidate=shape(state['candidates'][identity]['geometry'])
        result=kernel.replay(candidate,row,reader.old.comparison.alternating_support)
        # Every full remeasured pointset is retained once, with authenticated refs.
        for field in ('complete_geometry_mappings','complete_hierarchy_mappings'):
            if field in result:
                result[field]={name:objects.retain(geometry) for name,geometry in result[field].items()}
        routing=state['routing'][identity]
        result.update(component_id=identity,original_whole_scientific_row=pin,
            full_current_feature_sha256=routing['current_feature_sha256'],
            full_current_geometry_sha256=routing['current_geometry_sha256'],
            actual_delivered_routing_row=dict(
                whole_raw_sha256=state['scope']['routing_source']['whole_components_raw_sha256'],
                actual_merge=state['scope']['routing_source']['actual_merge'],
                complete_body_restoration='declared complete25-part routing stream'),
            family=routing['family'],operational_batch=routing['operational_batch'],
            complete_original_contact_ids=row['complete_contact_ids'],
            original_physical_status=row['physical_status'],original_physical_limits=row['physical_limits'],
            original_source_vintage=row['source_vintage'],original_unresolved=row['unresolved'],
            current_routing_unknowns=routing['unresolved'],source_fitness_prerequisite=routing['source_fitness_prerequisite'])
        products.emit('diagnoses',result)
        counts[result['status']]+=1;counts[result['conservative_class']]+=1
        for field in ('geometry_byte_container_equality','hierarchy_geometry_equality'):
            for relation,equal in result.get(field,{}).items():counts[field+':'+relation+':'+str(equal)]+=1
        for relation,diagnosis in result.get('point_diagnostics',{}).items():counts['point:'+relation+':'+diagnosis['status']]+=1
        families[routing['family']].append(identity);batches[routing['operational_batch']].append(identity)
        if number%1000==0:print(json.dumps(dict(progress=number,complete_target=26276,counts=dict(counts))),flush=True)
    for kind,groups,expected in [('families',families,3503),('batches',batches,253)]:
        if len(groups)!=expected or sum(map(len,groups.values()))!=26276:
            raise ValueError('Incomplete output family/batch allocation')
        for identity,members in sorted(groups.items()):
            products.emit(kind,dict(id=identity,members=sorted(members),member_count=len(members)))
    descriptors=products.finish()
    report=dict(status='complete',execution_commit=commit,started_at=started,ended_at=utc(),
        elapsed_seconds=time.monotonic()-monotonic,runtime=runtime,code=code,
        complete_current_components=95173,complete_numeric_components=26276,complete_complement=68897,
        complete_families=3503,complete_batches=253,geometry_objects=len(objects.seen),counts=dict(counts),
        source_input_receipts=state['receipts'],original_reconstructor=state['reconstructor'],
        derived_component_only_config_sha256=state['derived_component_only_config_sha256'],
        original_config_sha256=state['original_config_sha256'],outputs=descriptors,
        limits=kernel.exact.LIMITS+['Complete original alternating104 operator replay only; no native source query or new data reconstruction.',
          'Every original source/physical/hierarchy unknown is retained. Local point contradictions do not certify a corrected complete partition.',
          'Empty/nonpolygon/invalid or topology-budget cases retain full pointsets and exact helper disposition; no EPS/repair/guard waiver.',
          'Derived exact-rational triangle centroids are never passed through binary64 point parsing or rounding for exact membership.',
          'Geographic/source accuracy, physical water, ownership, legal/historical authority, publication and repair approval remain unapproved.'])
    (output/'report.json').write_bytes(reader.canonical(report))
    print(json.dumps(dict(status='complete',components=26276,families=3503,batches=253,counts=dict(counts))),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo',required=True)
    parser.add_argument('--code-commit',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--validate-inputs-only',action='store_true')
    args=parser.parse_args()
    run(Path(args.repo).resolve(),args.code_commit,Path(args.output),args.validate_inputs_only)

if __name__=='__main__':main()
