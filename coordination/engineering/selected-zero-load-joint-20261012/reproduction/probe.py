"""One archival execution of the real joint wrapper and original strict consumer."""
import gzip, hashlib, importlib.util, json, os, pathlib, subprocess, sys, tempfile, time
ROOT = pathlib.Path.cwd()
OUTPUT = pathlib.Path(os.environ['PROOF_DIR'])
BASE = '9473d184683ee8ff8546300f2313779c3cba1d2b'
CANDIDATE = '791576647adc41241ce9b438f1bb0034088eed4e'
TRUSTED = subprocess.check_output(['git','rev-parse','HEAD']).decode().strip()
REFERENCE = 'dd7db1d22823427b21afeeecab932d36d8728f76'

def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()

def retained(relative, expected_sha):
    body = subprocess.check_output(['git','show',REFERENCE+':'+relative])
    assert hashlib.sha256(body).hexdigest() == expected_sha, relative
    return json.loads(body)

sys.path.insert(0, str(ROOT / 'scripts'))
wrapper = load('joint_1784_actual_wrapper', 'scripts/run-geographic-check.py')
detector = load('joint_1784_original_predicates', 'scripts/check-geographic-regression.py')
# Only archival destination lifetime differs: actual tempfile creation, Node
# entry, immutable guards, data qualification and strict readback run unchanged.
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
assert result['mode'] == 'authenticated-checkpoint-append-v1', result
native = result['native']; continuous = result['continuous_result']
assert native['status'] == 'no-new-native-loss' and native['lost_or_reassigned_cells'] == 0
assert continuous['status'] == 'no-new-regression' and continuous['regressions'] == 0
reference_continuous = retained('coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/corrected-continuous-002/continuous.json', 'c155745caec52604d73dca515ea3a22446014162ce1830b566925c125391b07f')
reference_native = retained('coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/corrected-gates-001/native.json', '63f5153f40d1d072898ef12d8fab77c362edbe235f982709d8550cb8b3695209')
assert continuous['original_strict_polygon_result'] == reference_continuous['original_strict_polygon_result']
for key in ['status', 'lost_or_reassigned_cells', 'intervals', 'baseline_selection', 'candidate_selection']:
    assert native[key] == reference_native[key], key
publication = continuous['issued_publication']
assert publication['operands']['sha256'] == 'f3dade45a89f7b432168e4e75ebd852e6ce9864389e2ef2f8f9579d8336774b2'
assert publication['operands']['decoded_sha256'] == '949622e24a0431c707ebc1b9cfaaee21db768bc165aad17ba9e04534b4bb048e'
assert len(retained_directories) == 1
facts = json.loads((retained_directories[0] / 'complete/facts.json').read_bytes())
retained_facts = json.loads(subprocess.check_output(['git','show','a0ca24a30653f8e04baf23e6a788b140fc4b1cc0:coordination/engineering/continuous-single-vintage-20261012/retained-proof-001/complete/facts.json']))
assert facts['inverse'] == retained_facts['inverse']
assert facts['plan'] == retained_facts['plan']
counts = {}
for coverage in (OUTPUT/'coverage').glob('*.json'):
    for script in json.loads(coverage.read_bytes())['result']:
        if not script['url'].startswith(ROOT.as_uri() + '/'):
            continue
        for function in script['functions']:
            name = function['functionName']
            counts[name] = counts.get(name, 0) + function['ranges'][0]['count']
lifecycle = ['selectedBootstrap', 'qualifyCheckpoint', 'qualifyTransition', 'compareSelectedCheckpointNative', 'checkpointContinuousOperands', 'releaseCheckpoint']
for name in lifecycle:
    assert counts.get(name) == 1, (name, counts.get(name))
for name in ['loadSelection', 'selectedCoordinateShard']:
    assert counts.get(name) == 0, (name, counts.get(name))
summary = {'kind':'actual-joint-selected-retained-equivalence', 'execution_commit':TRUSTED,
           'baseline_commit':BASE, 'candidate_commit':CANDIDATE, 'reference_commit':REFERENCE,
           'complete_joint_seconds':complete_seconds, 'actual_v8_call_counts':{name:counts.get(name) for name in lifecycle + ['loadSelection','selectedCoordinateShard']}, 'native_status':native['status'],
           'continuous_status':continuous['status'], 'whole_original_strict_polygon_result_equal':True,
           'native_loss_intervals_and_selections_equal':True,
           'native_checked_rows':native['affected_rows'], 'historical_native_checked_rows':reference_native['affected_rows'],
           'whole_encoded_operands_equal':True, 'whole_decoded_operands_equal':True,
           'whole_plan_equal':True, 'whole_inverse_equal':True,
           'complete_owners':continuous['complete_owners'], 'required_owners':len(continuous['required_ids']),
           'changed_owners':len(continuous['original_strict_polygon_result']['changed_location_ids']),
           'archive_directory':retained_directories[0].name,
           'limits':['Historical local comparator, not a controlled or hosted timing benchmark.',
                     'Known accepted checkpoint selectors only; newer unregistered baselines take explicit cold fallback.',
                     'Archival tempfile lifetime retained for actual whole-byte comparison; scientific code path is unmodified.']}
(OUTPUT / 'joint-result.json').write_bytes(canonical(result))
(OUTPUT / 'comparison.json').write_bytes(canonical(summary))
print(json.dumps(summary), flush=True)
