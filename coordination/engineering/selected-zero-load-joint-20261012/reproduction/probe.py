"""One archival execution of the actual joint wrapper against accepted AUS CI."""
import gzip, hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, time, zipfile
ROOT = pathlib.Path.cwd()
PACKET = ROOT/'coordination/engineering/selected-zero-load-joint-20261012'
OUTPUT = pathlib.Path(os.environ['PROOF_DIR'])
BASE = '46438af8901acbad11a9b627828a9e9184018a77'
CANDIDATE = '95a3d3dcb76bf0c61a4f8ada504f3f346df18466'
TRUSTED = subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()

def digest(body):
    return hashlib.sha256(body).hexdigest()

provenance = json.loads((PACKET/'accepted-reference/provenance.json').read_bytes())
archive = PACKET/'accepted-reference/geography.zip'
assert archive.stat().st_size == provenance['zip_bytes'] and digest(archive.read_bytes()) == provenance['zip_sha256']
with zipfile.ZipFile(archive) as zipped:
    assert zipped.namelist() == [provenance['member']]
    reference_bytes = zipped.read(provenance['member'])
assert len(reference_bytes) == provenance['member_bytes'] and digest(reference_bytes) == provenance['member_sha256']
reference = json.loads(reference_bytes)
assert reference['gate_status'] == 'passed' and reference['baseline_commit'] == BASE and reference['candidate_commit'] == CANDIDATE
reference_continuous = reference['selected_continuous_report']
reference_native = reference['selected_native_report']
sys.path.insert(0, str(ROOT / 'scripts'))
wrapper = load('joint_1784_actual_wrapper', 'scripts/run-geographic-check.py')
detector = load('joint_1784_original_predicates', 'scripts/check-geographic-regression.py')
# Only archival destination lifetime differs: actual tempfile creation, Node
# entry, immutable guards, qualification and strict readback run unchanged.
original_temporary = tempfile.TemporaryDirectory
retained_directories = []
def archive_temporary(**kwargs):
    directory = original_temporary(**kwargs, dir=OUTPUT, delete=False)
    retained_directories.append(pathlib.Path(directory.name)); return directory
wrapper.tempfile.TemporaryDirectory = archive_temporary
started = time.monotonic()
result = wrapper.selected_joint(ROOT, BASE, CANDIDATE, detector, trusted=TRUSTED)
complete_seconds = time.monotonic() - started
(OUTPUT / 'joint-result.json').write_bytes(canonical(result))
(OUTPUT / 'execution-timing.json').write_bytes(canonical({'complete_joint_seconds':complete_seconds}))
assert result['mode'] == 'authenticated-checkpoint-append-v1', result
native = result['native']; continuous = result['continuous_result']
assert native['status'] == 'no-new-native-loss' and native['lost_or_reassigned_cells'] == 0
assert continuous['status'] == 'no-new-regression' and continuous['regressions'] == 0
assert canonical(continuous['original_strict_polygon_result']) == canonical(reference_continuous['original_strict_polygon_result'])
for key in ['status', 'lost_or_reassigned_cells', 'intervals', 'baseline_selection', 'candidate_selection']:
    assert native[key] == reference_native[key], key
for key in ['complete_owners', 'required_ids', 'source_binding']:
    assert continuous[key] == reference_continuous[key], key
publication = continuous['issued_publication']
assert publication['operands'] == reference_continuous['issued_publication']['operands']
assert len(retained_directories) == 1
complete = retained_directories[0]/'complete'
derived_publication = json.loads((complete/'derived-publication.json').read_bytes())
assert derived_publication == result['continuous']['derived_checkpoint']
assert derived_publication['kind'] == 'derived-selected-checkpoint-candidate-v1' and derived_publication['accepted_checkpoint'] is False
pin = derived_publication['certificate']; encoded = (complete/pin['path']).read_bytes(); decoded = gzip.decompress(encoded)
assert len(encoded) == pin['bytes'] and digest(encoded) == pin['sha256']
assert len(decoded) == pin['decoded_bytes'] and digest(decoded) == pin['decoded_sha256']
certificate = json.loads(decoded)
assert len(certificate['entries']) == continuous['complete_owners'] == 49625
facts_pin = derived_publication['facts']; facts_bytes = (complete/facts_pin['path']).read_bytes()
assert len(facts_bytes) == facts_pin['bytes'] and digest(facts_bytes) == facts_pin['sha256']
facts = json.loads(facts_bytes)
assert facts['executing_commit'] == TRUSTED and facts['baseline_commit'] == BASE and facts['candidate_commit'] == CANDIDATE
assert facts['candidate_selection'] == native['candidate_selection'] and facts['baseline_selection'] == native['baseline_selection']
assert facts['continuous_publication'] == publication and facts['certificate'] == pin
assert facts['candidate_code_executed'] is False and 'complete_cold_custody' not in facts
native_core = {key:value for key,value in native.items() if key not in ['runtime', 'caller_runtime', 'execution_runtimes', 'execution_code_inventory']}
assert facts['native_result_sha256'] == digest(canonical(native_core))
# Preserve the already-consumed execution roots and complete archived routing
# index by their actual immutable pins, without reacquiring any scientific body.
custody_outputs = []
def archive_pin(pin, name):
    assert pin.get('whole_body_consumed') is True
    raw = subprocess.check_output(['git', 'cat-file', 'blob', pin['git_blob_oid']])
    assert len(raw) == pin['bytes'] and digest(raw) == pin['sha256']
    (OUTPUT/name).write_bytes(raw)
    custody_outputs.append({'path':name, 'bytes':len(raw), 'sha256':digest(raw), 'original_pin':pin})
    return json.loads(raw)
policy_pin, catalogue_pin = facts['executing_authority_pins']
assert policy_pin['path'].endswith('/supported-programs.json') and catalogue_pin['path'].endswith('/accepted-checkpoints.json')
archive_pin(policy_pin, 'executing-policy.json')
catalogue = archive_pin(catalogue_pin, 'executing-checkpoints.json')
roots = [root for root in catalogue['checkpoints'] if root['id'] == facts['baseline_accepted_execution']['checkpoint_id']]
assert len(roots) == 1
route = roots[0]['routes']
actual_routes = [pin for pin in facts['actual_reader_inventories']['baseline'] if pin['path'] == route['path'] and pin['git_blob_oid'] == route['git_blob_oid']]
assert len(actual_routes) == 1
archive_pin(actual_routes[0], 'accepted-baseline-routes.json')
(OUTPUT/'archived-custody-publication.json').write_bytes(canonical({'version':1, 'kind':'retained-actual-execution-authority-v1', 'files':custody_outputs}))
counts = {}
for coverage in (OUTPUT/'coverage').glob('*.json'):
    for script in json.loads(coverage.read_bytes())['result']:
        if not script['url'].startswith(ROOT.as_uri() + '/'):
            continue
        for function in script['functions']:
            name = function['functionName']; counts[name] = counts.get(name, 0) + function['ranges'][0]['count']
lifecycle = ['selectedBootstrap', 'qualifyCheckpoint', 'qualifyTransition', 'compareSelectedCheckpointNative', 'checkpointContinuousOperands', 'releaseCheckpoint']
for name in lifecycle:
    assert counts.get(name) == 1, (name, counts.get(name))
for name in ['loadSelection', 'selectedCoordinateShard']:
    assert counts.get(name) == 0, (name, counts.get(name))
summary = {'kind':'actual-joint-selected-accepted-aus-equivalence', 'execution_commit':TRUSTED,
           'baseline_commit':BASE, 'candidate_commit':CANDIDATE, 'accepted_reference':provenance,
           'complete_joint_seconds':complete_seconds,
           'actual_v8_call_counts':{name:counts.get(name) for name in lifecycle + ['loadSelection','selectedCoordinateShard']},
           'native_status':native['status'], 'continuous_status':continuous['status'],
           'whole_original_strict_polygon_result_equal':True, 'native_loss_intervals_and_selections_equal':True,
           'native_checked_rows':native['affected_rows'], 'accepted_native_checked_rows':reference_native['affected_rows'],
           'whole_encoded_and_decoded_operand_hashes_equal':True, 'whole_source_bindings_and_required_ids_equal':True,
           'complete_owners':continuous['complete_owners'], 'required_owners':len(continuous['required_ids']),
           'changed_owners':len(continuous['original_strict_polygon_result']['changed_location_ids']),
           'derived_checkpoint_publication':derived_publication, 'derived_native_report_inverse_verified':True, 'archive_directory':retained_directories[0].name,
           'limits':['Actual local joint path, including output serialization and strict Python readback; not a controlled hosted timing benchmark.',
                     'Original accepted CI operand hashes are available; historical facts/inverse bodies are unavailable and are not claimed equal.',
                     'Derived candidate certificate has distinct provisional transition lineage; no new checkpoint authority is minted by serialization.',
                     'Archival tempfile lifetime retained for whole-byte comparison; scientific predicates are unmodified.']}
(OUTPUT / 'comparison.json').write_bytes(canonical(summary))
print(json.dumps(summary), flush=True)
