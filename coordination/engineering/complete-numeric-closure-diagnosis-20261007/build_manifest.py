"""Concrete issue1300 ordinary evidence ledger; no scientific operations."""
import hashlib
import json
from pathlib import Path
import subprocess
import reader

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PREFIX=str(HERE.relative_to(ROOT))+'/'
BASE='0198938719a5666b6726fb6a1e45779926eefeb2'
SCIENCE='3ef1b938a4813adcc62be632df29837c8122a1bb'
WORKER='01a10fea-fe9b-7722-a974-0269a733a330'
MANIFEST=PREFIX+'evidence-quality.json'
PIN_PATHS={
    'original_operator_sha256':'coordination/engineering/global-physical-comparison-20261006/comparison.py',
    'physical_scientific_report':'coordination/engineering/global-physical-comparison-20261006/results/report.json',
    'audited_successor_report':'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json'}

def descriptor(path):
    raw=reader.safe_path(ROOT,path).read_bytes()
    pin=dict(path=path,bytes=len(raw),sha256=reader.digest(raw),hash_kind='file-bytes',role='evidence')
    # The source index authenticates gzip-magic retained .bin aliases explicitly.
    relative=path.removeprefix(PREFIX)
    index=json.loads(reader.safe_path(HERE,'input-index.json').read_bytes())
    inherited=next((x for x in index['files'] if x['path']==relative),None)
    if inherited and 'uncompressed_sha256' in inherited:
        pin.update(uncompressed_bytes=inherited['uncompressed_bytes'],uncompressed_sha256=inherited['uncompressed_sha256'])
    elif path.endswith('.gz'):
        import gzip,io
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as handle:decoded=handle.read(reader.LIMIT+1)
        if len(decoded)>reader.LIMIT:raise ValueError('Actual ordinary decoded bound exceeded')
        pin.update(uncompressed_bytes=len(decoded),uncompressed_sha256=reader.digest(decoded))
    if pin['bytes']>reader.LIMIT:raise ValueError('Actual ordinary encoded bound exceeded')
    return pin

def main():
    report=json.loads(reader.safe_path(HERE,'r1/report.json').read_bytes())
    replay=json.loads(reader.safe_path(HERE,'v/reproducibility.json').read_bytes())
    if replay['outcome']!='passed' or replay['run_one_sha256']!=replay['run_two_sha256']:
        raise ValueError('Missing actual complete two-run result')
    baseline=[];pins={}
    for name,path in PIN_PATHS.items():
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',BASE+':'+path])
        pin=dict(path=path,bytes=len(raw),sha256=reader.digest(raw),hash_kind='file-bytes')
        baseline.append(pin);pins[name]=pin['sha256']
    files=[]
    for path in sorted(HERE.rglob('*')):
        rel=path.relative_to(HERE)
        if any(x in ('.cache','__pycache__') for x in rel.parts) or not path.is_file():continue
        if path.is_symlink():raise ValueError('Nonordinary final evidence')
        if path.name!='evidence-quality.json':files.append(str(path.relative_to(ROOT)))
    outputs=[descriptor(path) for path in files]
    budget=sum(x['bytes'] for x in [*baseline,*outputs])
    if budget>268435456 or len(baseline)+len(outputs)>512:
        raise ValueError(f'Actual complete ordinary budget exceeds policy: {budget}/{len(baseline)+len(outputs)}')
    sources=[]
    for identity,role,url in (
        ('complete-original104-physical-evidence','Whole original104 component/query/hierarchy/coordinate/unknown observations and exact original helper/code provenance.',
         'coordination/engineering/global-physical-comparison-20261006/results/report.json'),
        ('complete-current-lineage-context','Whole audited original/current component/fragment/contact/residue pointsets and full current feature/context binding.',
         'coordination/engineering/worldwide-successor-1215-20261006/run-one/report.json'),
        ('complete-delivered-prerequisite-routing','Whole actual merged95,173 routing rows, all26276numeric+68897complement and complete family/batch allocation.',
         'coordination/engineering/global-actionability-routing-20261007/results/report.json')):
        sources.append(dict(id=identity,role=role,url='https://github.com/ChengshuLi/WorldAtlas/blob/'+BASE+'/'+url,
            vintage='Original execution/source vintages preserved in complete input-index and both actual reports; immutable repository delivery01989387 is not a new physical observation.',
            retrieved_at='2026-10-07; complete retained body windows and actual commands/times in both scientific execution capsules.',
            retention='restoration-only',verification='unverified',temporal_status='unknown',
            license=dict(status='unknown',terms='Existing repository-derived evidence reused through exact original whole Git bodies; all underlying source credits/terms/uncertainties are retained, not newly approved or overridden.'),
            restoration='All179 complete candidate aliases are ordinary outputs. input-index.json binds every encoded/decoded body, immutable original commit/path/mode/OID, and full containing-file relations; scope is an alias to the entire25-part delivered routing stream, not a source substitute.',
            limit='Original physical/date/source-fitness, geographic/legal/ownership authority and processing cause remain unapproved; byte authentication and local exact point diagnostics do not certify repair or complete partition recovery.'))
    metric_fields=[('complete-current','/complete_current_components',report['complete_current_components']),
        ('complete-numeric','/complete_numeric_components',report['complete_numeric_components']),
        ('complete-complement','/complete_complement',report['complete_complement']),
        ('complete-families','/complete_families',report['complete_families']),
        ('complete-batches','/complete_batches',report['complete_batches']),
        ('complete-pointset-objects','/geometry_objects',report['geometry_objects']),
        ('original-matching','/counts/replayed',report['counts']['replayed']),
        ('original-replay-mismatch-unknown','/counts/original-replay-mismatch',report['counts']['original-replay-mismatch']),
        ('matching-local-contradictions','/counts/local-construction-contradiction-demonstrated',report['counts']['local-construction-contradiction-demonstrated']),
        ('matching-retained-unresolved','/counts/retained-unresolved-numerical-or-context-prerequisite',report['counts']['retained-unresolved-numerical-or-context-prerequisite'])]
    index=json.loads(reader.safe_path(HERE,'input-index.json').read_bytes())
    scope=next(x for x in index['files'] if x['path']=='scope.json.gz')
    methods=[dict(id='complete-ordinary-retention',kind='generator',helper_version='worldatlas-evidence-preparation-v1',
        description='Complete179 ordinary input/code closure, exact original71 whole-body restoration, full26276/68897 routing/current bijection and3503/253 allocation, existing bounded deterministic gzip with all pointsets and unknowns retained. Two actual frozen complete numerical runs are kept byte-identical as separate ordinary scientific trees.',
        software='Python3.12.14; unchanged authenticated original immutable/inputs/transport codecs; exact whole execution/import/runtime capsules and separate final retention/readback code.',
        units='whole bytes/SHA256, component/family/batch/geometry identities and counts; no geographic area/distance measurement'),
        dict(id='literal104-exact-witness-diagnosis',kind='measurement',
        description='Original unchanged alternating104 binary64 operators replay every original positive piece in original order. Full fresh mappings must equal original mappings before original-attributed exact residue evidence. Unchanged bounded Fraction helper preserves full invalid/nonpolygon/topology/cap unknowns and uses separately derived exact-rational triangle centroids without binary64 conversion; point witnesses never certify a corrected full partition.',
        software='Python3.12.14/NumPy2.3.5/Shapely2.1.2/GEOS3.13.1/PyProj3.7.2; exact frozen3ef project closure; unchanged original104 comparison and exact_predicates.py whole-byte provenance.',
        units='literal OGC:CRS84 source-coordinate binary64 geometry diagnostics and exact-rational point states; no new m²/metres/ellipsoidal/source-authority result')]
    validation=[dict(method_id=method,kind=kind,outcome='passed',evidence_path=PREFIX+'v/'+file) for method,kind,file in (
        ('complete-ordinary-retention','positive-control','preparation-positive-final.json'),
        ('complete-ordinary-retention','negative-control','preparation-negative-final.json'),
        ('complete-ordinary-retention','reproducibility','reproducibility.json'),
        ('literal104-exact-witness-diagnosis','positive-control','measurement-positive-final.json'),
        ('literal104-exact-witness-diagnosis','negative-control','measurement-negative-final.json'))]
    manifest=dict(version=1,issue=1300,lane='engineering',worker_id=WORKER,subject_ids=[],
        subject_ids_sha256=hashlib.sha256(b'[]').hexdigest(),baseline=dict(commit=BASE,files=baseline,pins=pins,pin_files=PIN_PATHS),
        sources=sources,outputs=outputs,methods=methods,validation=validation,
        metrics=[dict(id=name,value=value,unit='whole retained entities or candidates',vintage='archived',evaluation_commit=SCIENCE,
                      input_sha256=scope['sha256']) for name,pointer,value in metric_fields],
        metric_bindings=[dict(metric_id=name,path=PREFIX+'r1/report.json',json_pointer=pointer) for name,pointer,value in metric_fields],
        summaries=[],conclusions=[dict(status='unresolved',source_ids=[x['id'] for x in sources],
            text='Complete frozen numeric-first diagnosis is delivered. Matching local exact contradictions, original-replay mismatches, invalid/unsupported pointsets and all original source/context/hierarchy unknowns remain distinct and fully retained. Final verifier correction preserves the actual45a complete custody/semantic proof, adds an immutable4956 all-row guarded-branch audit and14 directed actual partial-prefix/invalid/invented-witness controls. No corrected partition, physical water/land, ownership, source accuracy, historical/legal authority, deployment or repair approval is certified; parent1202 remains active.')],
        stages=dict(research='complete',implementation='implemented',geographic_approval='not-requested'),
        commands=['PYTHONDONTWRITEBYTECODE=1 python -u -B '+PREFIX+'diagnose.py --repo REPO --code-commit '+SCIENCE+' --output ABSOLUTE_ABSENT_OWNED_CACHE_DIRECTORY (execute twice independently at frozen3ef; outputs exclusive)',
                  'Final readback authenticates both whole actual trees and complete rows/pointsets/members without a third operator or exact membership-query cohort; bounded case controls are separately labelled.'],
        change_receipts=[dict(path=path,status='added') for path in sorted([*files,MANIFEST])])
    (HERE/'evidence-quality.json').write_bytes(reader.canonical(manifest))
    print(json.dumps(dict(status='built',descriptors=len(baseline)+len(outputs),encoded_budget_bytes=budget,
                         changed_files=len(files)+1,manifest_sha256=reader.digest(reader.canonical(manifest))),sort_keys=True))

if __name__=='__main__':main()
