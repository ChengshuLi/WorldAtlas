#!/usr/bin/env python3
"""Run two byte-complete extractions and meaningful negative integrity controls."""
import copy, datetime, hashlib, importlib.util, json, pathlib, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[2]
SCRIPT = ROOT / 'methods/extract_preserved_records.py'
sha = lambda b: hashlib.sha256(b).hexdigest()
utc = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

spec = importlib.util.spec_from_file_location('preserved_extractor', SCRIPT)
sys.dont_write_bytecode = True
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
proposal_raw = (ROOT / 'inputs/root-philippines-ten-full-family-source-fit-proposal.json').read_bytes()
proposal = json.loads(proposal_raw)
ids = sorted(proposal['contact_ids'])
components = sorted(proposal['component_ids'])
source = (ROOT / 'inputs/gb-PHL-ADM3.original').read_bytes()

def git_blob(commit, path):
    return subprocess.check_output(['git', '-C', str(REPOSITORY), 'show', f'{commit}:{path}'])

input_closure=[]
def add_input(path, raw, vintage, role, uncompressed=None):
    row={'path':path,'vintage':vintage,'role':role,'bytes':len(raw),'sha256':sha(raw)}
    if uncompressed is not None:
        row.update(uncompressed_bytes=len(uncompressed),uncompressed_sha256=sha(uncompressed))
    input_closure.append(row)

add_input('inputs/gb-PHL-ADM3.original',source,'candidate','complete retained consumed source')
add_input('inputs/root-philippines-ten-full-family-source-fit-proposal.json',proposal_raw,'candidate','unchanged accepted predecessor pointsets and family/component closure')
handoff=(ROOT/'inputs/root-philippines-ten-original-source-handoff.json').read_bytes()
add_input('inputs/root-philippines-ten-original-source-handoff.json',handoff,'candidate','original source identity and 22-subject handoff')
transport=git_blob(module.BASE,module.TRANSPORT_PATH)
add_input(module.TRANSPORT_PATH,transport,module.BASE,'whole consumed source transport',__import__('gzip').decompress(transport))
for path in ('data/world-index.json','data/administrative-sources.json',
             'coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',
             'coordination/engineering/global-actionability-routing-20261007/input-config.json',
             'coordination/engineering/global-actionability-routing-20261007/results/report.json',
             'data/geography/part-18.json','data/geography/part-19.json'):
    add_input(path,git_blob(module.BASE,path),module.BASE,'pinned scope/current-subject context')
for item in proposal['whole_input_body_closure']:
    path='coordination/engineering/global-actionability-routing-20261007/results/'+item['path']
    raw=git_blob(module.BASE,path)
    add_input(path,raw,module.BASE,'complete original routing body',__import__('gzip').decompress(raw))
physical_package=json.loads((ROOT/'records/physical-comparison-rows-22.json').read_bytes())
for path in physical_package['source_files']:
    raw=git_blob(module.BASE,path)
    add_input(path,raw,module.BASE,'complete selected physical comparison body',__import__('gzip').decompress(raw))
input_closure.sort(key=lambda row:(row['vintage'],row['path']))
frozen_at=utc()
frozen_extractor_sha=sha(SCRIPT.read_bytes())
frozen_harness_sha=sha(pathlib.Path(__file__).read_bytes())

def rejected(fn):
    try:
        fn()
    except (ValueError, AssertionError):
        return True
    return False

controls = []
def record(name, ok):
    if not ok:
        raise RuntimeError(f'Negative control did not reject mutation: {name}')
    controls.append({'control': name, 'result': 'mutated input rejected'})

def perturb_first_xy(value):
    if isinstance(value, list) and len(value) >= 2 and all(isinstance(x, (int, float)) for x in value[:2]):
        value[0] += 0.000001
        return True
    if isinstance(value, list):
        return any(perturb_first_xy(x) for x in value)
    return False

record('omitted contact subject', rejected(lambda: module.require_exact_ids(ids, ids[:-1], 'negative omission')))
record('duplicated contact subject', rejected(lambda: module.require_exact_ids(ids, ids + [ids[0]], 'negative duplicate')))
record('foreign contact subject', rejected(lambda: module.require_exact_ids(ids, ids + ['gb:PHL:ADM3:foreign'], 'negative foreign')))
record('original source byte mutation', rejected(lambda: module.require_sha(source + b'\x00', module.SOURCE_SHA, 'negative source mutation')))
record('original source expected hash mutation', rejected(lambda: module.require_sha(source, '0' * 64, 'negative expected hash')))

candidate = copy.deepcopy(proposal['full_candidates'][0])
candidate_hash = sha(module.canonical(candidate))
mutated_candidate = copy.deepcopy(candidate)
if not perturb_first_xy(mutated_candidate['geometry']['coordinates']):
    raise RuntimeError('Could not mutate candidate geometry for negative control')
record('candidate geometry to whole feature identity binding', rejected(lambda: module.require_feature_binding(mutated_candidate, candidate['id'], candidate_hash, 'negative candidate geometry')))

contact_id = ids[0]
contact = proposal['full_current_contacts'][contact_id]['full_feature']
mutated_contact = copy.deepcopy(contact)
if not perturb_first_xy(mutated_contact['geometry']['coordinates']):
    raise RuntimeError('Could not mutate current geometry for negative control')
record('current geometry to full contact identity binding', rejected(lambda: module.require_feature_binding(mutated_contact, contact_id, proposal['full_current_contacts'][contact_id]['full_feature_sha256'], 'negative current geometry')))

def inventory(directory):
    rows=[]
    for path in sorted(directory.iterdir()):
        raw=path.read_bytes()
        rows.append({'path':path.name,'bytes':len(raw),'sha256':sha(raw)})
    return rows

run_rows=[]
with tempfile.TemporaryDirectory(prefix='phl-source-fitness-run-') as temp:
    for index in (1, 2):
        output=pathlib.Path(temp)/f'run-{index}'
        output.mkdir()
        command=[sys.executable,str(SCRIPT),'--output',str(output)]
        started=utc();t0=time.monotonic()
        result=subprocess.run(command,cwd=str(REPOSITORY),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        duration=time.monotonic()-t0;finished=utc()
        run_rows.append({'run':index,'command':' '.join(command),'started_at_utc':started,'finished_at_utc':finished,
                         'duration_seconds':round(duration,3),'exit_code':result.returncode,
                         'stdout':result.stdout.decode('utf-8','replace').strip(),
                         'stderr_sha256':sha(result.stderr),'output_files':inventory(output)})
        if result.returncode != 0:
            raise RuntimeError(f'Extraction run {index} failed: {result.stderr.decode("utf-8","replace")}')
    files1={x['path']:x for x in run_rows[0]['output_files']}
    files2={x['path']:x for x in run_rows[1]['output_files']}
    if files1 != files2:
        raise RuntimeError('Two complete extraction output inventories differ')
    for row in run_rows[0]['output_files']:
        raw=(pathlib.Path(temp)/'run-1'/row['path']).read_bytes()
        (ROOT/'records'/row['path']).write_bytes(raw)

receipt={'method':'methods/extract_preserved_records.py','acceptance_harness':'methods/verify_extraction_acceptance.py',
         'runtime':sys.version,'platform':sys.platform,'imports':'Python standard library only plus Git CLI',
         'frozen_at_utc':frozen_at,'run_count':2,'runs':run_rows,'input_closure':input_closure,
         'outputs_identical_byte_for_byte':True,'negative_controls':controls,
         'code_sha256':{'extractor':frozen_extractor_sha,'harness':frozen_harness_sha},
         'scope':'Restores source, current-contact, candidate-pointset and already accepted comparison records from declared immutable inputs; no new geometry operation, source adjudication or physical comparison.',
         'outputs':run_rows[0]['output_files']}
if frozen_extractor_sha != sha(SCRIPT.read_bytes()) or frozen_harness_sha != sha(pathlib.Path(__file__).read_bytes()):
    raise RuntimeError('Code changed during the frozen two-run extraction')
(ROOT/'records/extraction-runs.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')

print(json.dumps({'result':'PASS','runs':2,'outputs_identical_byte_for_byte':True,
                  'negative_controls':len(controls),'output_files':len(files1),
                  'run_durations_seconds':[x['duration_seconds'] for x in run_rows]},sort_keys=True))
