"""Read-only geographic comparison with explicit executing-code and data identities."""
import argparse
import base64
import hashlib
import importlib.util
import json
import os
import pathlib
import re
import subprocess
import tempfile
import gzip
import time
import signal
import sys
from contextlib import contextmanager

@contextmanager
def stage_timing(name):
    started = time.monotonic()
    try:
        yield
    finally:
        print(json.dumps({'geography_stage': name, 'elapsed_ms': round((time.monotonic() - started) * 1000)}), file=sys.stderr, flush=True)


def prefetch_declared_inputs(repo, baseline, candidate, timeout=120):
    # Optional transport preparation only. The original checker still consumes
    # every required input and establishes all scientific/identity guarantees.
    env = dict(os.environ)
    for name in ['NODE_OPTIONS', 'NODE_PATH']:
        env.pop(name, None)
    try:
        if os.name != 'posix':
            raise ValueError('Prefetch requires owned process-group cleanup')
        child = subprocess.Popen([env.get('NODE', 'node'), str(repo / 'scripts/geography-prefetch.mjs'),
                                  str(repo), baseline, candidate], env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, start_new_session=True)
        try:
            stdout, _ = child.communicate(timeout=timeout)
        finally:
            # Kill the owned group even if Node exited after a Git failure. A
            # launcher timeout must not leave a Git descendant writing while
            # the ordinary checker resumes. Failure to reap blocks continuation.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except OSError as error:
                raise RuntimeError('Cannot terminate owned prefetch process group') from error
            try:
                child.communicate(timeout=5)
            except subprocess.TimeoutExpired as error:
                raise RuntimeError('Prefetch process group did not terminate') from error
        if len(stdout) > 1024 * 1024:
            raise ValueError('Prefetch summary exceeds bound')
        summary = json.loads(stdout)
        if not isinstance(summary, dict) or summary.get('complete_scientific_closure') is not False:
            raise ValueError('Prefetch cannot assert scientific closure')
        if child.returncode != 0:
            summary['status'] = 'scoped-prefetch-unavailable'
            summary['partial_import_possible'] = True
        print(json.dumps({'geography_prefetch': summary}), file=sys.stderr, flush=True)
    except (subprocess.TimeoutExpired, OSError, ValueError):
        print(json.dumps({'geography_prefetch': {'status': 'scoped-prefetch-unavailable',
              'complete_scientific_closure': False, 'partial_import_possible': True}}), file=sys.stderr, flush=True)


MAX_BYTES = 32 * 1024 * 1024
TRUSTED_PATHS = ['scripts/run-geographic-check.py', 'scripts/check-geographic-regression.py',
                 'scripts/check-effective-geographic-regression.mjs', 'scripts/selected-checkpoint-native.mjs', 'src/ownership-codec.js',
                 'scripts/evidence/immutable.py', 'scripts/evidence/geometry.py',
                 'scripts/ellipsoidal_area.py', 'requirements.txt',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-checkpoint-continuous.mjs',
                 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs',
                 'scripts/geographic_checkpoint_products.py',
                 'scripts/accepted-selected-checkpoint.mjs',
                 'scripts/check-handoff-scope.mjs',
                 'scripts/evidence-policy.mjs',
                 'scripts/evidence-quality.mjs',
                 'scripts/geographic-report-artifact.mjs',
                 'scripts/github-quota.mjs',
                 'scripts/github-snapshots.mjs',
                 'scripts/integration-proof.mjs',
                 'scripts/issue-claim-contract.mjs',
                 'scripts/job-deadline.mjs',
                 'scripts/research-import-gate.mjs',
                 'scripts/worker-result.mjs',
                 'src/regional-import-gate.js']
PIN_PATHS = ['data/hierarchy.json', 'data/canonical-grid/manifest.json',
             'data/geographic-releases/index.json', 'data/geographic-releases/current-manifest.json']

def immutable_sha(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{40}', value):
        raise ValueError('Require exact immutable baseline and candidate commits')
    return value


def safe_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value or any(p in ['', '.', '..'] for p in value.split('/')):
        raise ValueError('Unsafe geography input path')
    return value


def git(repo, *args):
    return subprocess.check_output(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo), *args], stderr=subprocess.PIPE)


def entry(repo, commit, name):
    name = safe_path(name)
    row = git(repo, 'ls-tree', '-z', commit, '--', name).decode().rstrip('\0')
    if not row.startswith(('100644 ', '100755 ')) or row[row.find('\t'):] != '\t' + name:
        raise ValueError('Geography input must be an ordinary Git file: ' + name)
    blob = row.split()[2]
    return {'path': name, 'mode': row.split()[0], 'git_blob_oid': blob}


def read(repo, commit, name):
    blob = entry(repo, commit, name)['git_blob_oid']
    if int(git(repo, 'cat-file', '-s', blob)) > MAX_BYTES:
        raise ValueError('Geography input exceeds bounded file size: ' + name)
    return git(repo, 'cat-file', 'blob', blob)


def inventory(repo, commit):
    index = json.loads(read(repo, commit, 'data/world-index.json'))
    parts = index.get('parts')
    if not isinstance(parts, list) or not 1 <= len(parts) <= 512 or len(set(parts)) != len(parts):
        raise ValueError('Invalid or incomplete live geography part inventory')
    names = ['data/world-index.json', *PIN_PATHS, *['data/' + safe_path(p) for p in parts]]
    pointer = json.loads(read(repo, commit, PIN_PATHS[-1]))
    if not isinstance(pointer, dict) or not re.fullmatch('[a-f0-9]{64}', pointer.get('sha256', '')):
        raise ValueError('Invalid geographic release pointer')
    pointed = safe_path(pointer.get('path'))
    if not pointed.startswith('data/'):
        pointed = 'data/geographic-releases/' + pointed
    if hashlib.sha256(read(repo, commit, pointed)).hexdigest() != pointer['sha256']:
        raise ValueError('Geographic release pointer hash mismatch')
    names.append(pointed)
    return [entry(repo, commit, name) for name in sorted(set(names))]


def verify_trusted_checkout(repo, baseline):
    if git(repo, 'rev-parse', 'HEAD').decode().strip() != baseline:
        raise ValueError('Checker checkout must be the exact trusted baseline commit')
    # Verify the complete local scripts namespace, including package absence.
    # A byte-correct geometry.py is insufficient if an untracked evidence.py,
    # package initializer, extension module or cached bytecode can shadow it.
    expected = {}
    for row in git(repo, 'ls-tree', '-r', '-z', baseline, '--', 'scripts', 'src').decode().split('\0'):
        if not row:
            continue
        fields, name = row.split('\t', 1)
        if fields.split()[0] not in ['100644', '100755']:
            raise ValueError('Trusted scripts must be ordinary committed files')
        expected[name] = fields.split()[2]
    actual = {}
    for namespace in ['scripts', 'src']:
        if (repo / namespace).is_symlink():
            raise ValueError('Trusted scripts namespace cannot contain symlinks')
        for target in (repo / namespace).rglob('*'):
            if target.is_symlink():
                raise ValueError('Trusted scripts namespace cannot contain symlinks')
            if target.is_file():
                actual[str(target.relative_to(repo))] = target
    if set(actual) != set(expected):
        raise ValueError('Untracked or missing file in trusted scripts namespace')
    for name, target in actual.items():
        if target.read_bytes() != git(repo, 'cat-file', 'blob', expected[name]):
            raise ValueError('Checker differs from immutable trusted baseline: ' + name)
    for name in ['requirements.txt', 'package.json', '.github/evidence-policy.json', *[p for p in TRUSTED_PATHS if p.startswith('coordination/')]]:
        target = repo / name
        if any(path.is_symlink() for path in [target, *target.parents]) or not target.is_file() or target.read_bytes() != read(repo, baseline, name):
            raise ValueError('Trusted dependency metadata or evidence policy differs from baseline')
        expected[name] = entry(repo, baseline, name)['git_blob_oid']
    return hashlib.sha256((json.dumps(expected, sort_keys=True, separators=(',', ':')) + '\n').encode()).hexdigest()


def compare_effective_primitives(detector, before, after, additions, base_hashes=None):
    """Literal BASE OR complete ADDITION sets; never persist a dissolved polygon.

    Original prepare/compare operates on each unchanged complete primitive.
    Multiple primitives with one stable owner are one ownership set, so their
    internal intersections are not competing-location overlap. Coverage-loss
    findings are never filtered. The original geometry routines stay literal.
    """
    if not any(additions.values()):
        return detector.compare(before, after)
    owners, primitives = {}, {}
    for vintage, features in [('baseline', before), ('candidate', after)]:
        values = {}
        for identity, feature in features.items():
            key = json.dumps([identity, 'base'], ensure_ascii=False, separators=(',', ':'))
            owners[key] = identity
            values[key] = {**feature, 'id': key}
        seen = set()
        for row in additions[vintage]:
            identity, component = row['target_id'], row['component_id']
            if identity not in features:
                continue  # Whole additions outside the certified affected set.
            if component in seen or row['base_geometry_sha256'] != (base_hashes[vintage][identity] if base_hashes is not None else detector.geometry_hash(features[identity])):
                raise ValueError('Foreign/duplicate/stale complete effective primitive')
            seen.add(component)
            key = json.dumps([identity, component], ensure_ascii=False, separators=(',', ':'))
            if key in values:
                raise ValueError('Effective primitive identity collision')
            owners[key] = identity
            values[key] = {'type': 'Feature', 'id': key, 'properties': {'id': key}, 'geometry': row['geometry']}
        primitives[vintage] = values
    result = detector.compare(primitives['baseline'], primitives['candidate'])
    changed = sorted({owners[key] for key in result['changed_location_ids']})
    findings = []
    for feature in result['findings']['features']:
        props = feature['properties']
        identities = sorted({owners[key] for key in props['location_ids']})
        if props['kind'] == 'new-pair-overlap' and len(identities) == 1:
            continue
        props['location_ids'] = identities
        props['changed_location_ids'] = sorted(set(identities) & set(changed))
        for vintage in ['before', 'after']:
            for row in props[vintage]:
                row['primitive_id'] = row['location_id']
                row['location_id'] = owners[row['location_id']]
        findings.append(feature)
    for feature in result['coverage_gained']['features']:
        props = feature['properties']
        props['location_ids'] = sorted({owners[key] for key in props['location_ids']})
        props['changed_location_ids'] = sorted(set(props['location_ids']) & set(changed))
        for vintage in ['before', 'after']:
            for row in props[vintage]:
                row['primitive_id'] = row['location_id']
                row['location_id'] = owners[row['location_id']]
    for error in result['geometry_errors']:
        error['primitive_id'] = error['location_id']
        error['location_id'] = owners[error['location_id']]
    result['changed_primitive_ids'] = result['changed_location_ids']
    result['changed_location_ids'] = changed
    result['affected_neighbor_ids'] = sorted({owners[key] for key in result['affected_neighbor_ids']} - set(changed))
    result['findings']['features'] = findings
    if result['regressions'] is not None:
        result['regressions'] = len(findings)
        result['status'] = 'regressions-found' if findings else 'no-new-regression'
    result['effective_set_domain'] = 'literal-base-or-complete-additions:v2'
    return result


def selected_continuous(repo, baseline, candidate, detector, *, trusted=None):
    import sys
    env = dict(os.environ)
    for name in ['NODE_OPTIONS', 'NODE_PATH']:
        env.pop(name, None)
    executable = os.environ.get('NODE', 'node')
    entrypoint = repo / 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-continuous-entry.mjs'
    with tempfile.TemporaryDirectory(prefix='trusted-selected-footprints-') as temporary:
        destination = pathlib.Path(temporary).resolve() / 'complete'
        with stage_timing('selected-continuous-node-operands'):
            raw = subprocess.check_output([executable, '--expose-gc', str(entrypoint), 'continuous', str(repo), trusted or baseline,
                                          baseline, candidate, str(destination), sys.executable], env=env)
        if len(raw) > MAX_BYTES:
            raise ValueError('Cold selected acknowledgement exceeds output cap')
        return consume_selected_continuous(repo, baseline, candidate, detector, destination, json.loads(raw), trusted=trusted)


def checkpoint_products_module(repo):
    # Called only after the trusted checkout namespace has been authenticated.
    spec = importlib.util.spec_from_file_location('trusted_checkpoint_products', repo / 'scripts/geographic_checkpoint_products.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def selected_consumer_allowance(repo):
    # Node has terminated. Admit the actual parent phase with current resources,
    # installed runtime/code, and the complete retained report/output reserve.
    env = {key: value for key, value in os.environ.items() if key not in ['NODE_OPTIONS', 'NODE_PATH']}
    executable = os.environ.get('NODE', 'node')
    runtime_bytes = pathlib.Path(sys.executable).resolve().stat().st_size
    code_bytes = sum((repo / name).stat().st_size for name in TRUSTED_PATHS)
    # Re-observe current resources after the Node operand child has exited.
    # Reuse the trusted reader's OS/cgroup-aware admission instead of an
    # unrelated fixed historical phase ceiling. No candidate code is loaded.
    allowance_raw = subprocess.check_output([
        executable, '--input-type=module', '-e',
        'const {processingAllowance}=await import(process.argv[1]);process.stdout.write(JSON.stringify(processingAllowance()));',
        (repo / 'scripts/check-effective-geographic-regression.mjs').resolve().as_uri()],
        env=env, timeout=30)
    if len(allowance_raw) > 4096:
        raise ValueError('Oversized current reader allowance')
    allowance = json.loads(allowance_raw)
    phase_limit = allowance.get('phaseBytes')
    if type(phase_limit) is not int or not 0 < phase_limit <= 9007199254740991:
        raise ValueError('Invalid current polygon consumer allowance')
    remaining = phase_limit - runtime_bytes - code_bytes - 2 * MAX_BYTES
    if remaining <= 0:
        raise ValueError('Complete selected consumer has no current product allowance')
    return remaining


def consume_selected_continuous(repo, baseline, candidate, detector, destination, issued, *, trusted=None):
    if not isinstance(issued, dict) or issued.get('candidate_code_executed') is not False or issued.get('kind') != 'trusted-selected-continuous-comparison-v1':
        raise ValueError('Unsupported selected continuous acknowledgement')
    if issued.get('status') == 'selected-sources-unchanged':
        return issued
    import sys
    env = {key: value for key, value in os.environ.items() if key not in ['NODE_OPTIONS', 'NODE_PATH']}
    executable = os.environ.get('NODE', 'node')
    publication = issued.get('publication')
    if not isinstance(publication, dict) or publication.get('complete') is not True:
        raise ValueError('Selected continuous source operands lack complete issued publication')
    names = ['publication.json', publication['facts']['path'], publication['operands']['path']]
    pins = [None, publication['facts'], publication['operands']]
    total = 0
    for name, pin in zip(names, pins):
        if safe_path(name) != pathlib.Path(name).name:
            raise ValueError('Foreign selected output path')
        target = destination / name
        stat = target.lstat()
        if target.is_symlink() or not target.is_file() or stat.st_mode & 0o777 != 0o644 or stat.st_size > MAX_BYTES:
            raise ValueError('Nonordinary whole selected output')
        if pin is not None and (stat.st_size != pin['bytes'] or pin.get('decoded_bytes', 0) > MAX_BYTES):
            raise ValueError('Whole selected output size exceeds original bound')
        total += stat.st_size + (pin.get('decoded_bytes', 0) if pin else 0)
    if total > selected_consumer_allowance(repo):
        raise ValueError('Complete selected polygon consumer phase exceeds current allowance')
    bodies = []
    for name, pin in zip(names, pins):
        body = (destination / name).read_bytes()
        if pin is not None and (len(body) != pin['bytes'] or hashlib.sha256(body).hexdigest() != pin['sha256']):
            raise ValueError('Whole selected output differs from issued trusted child')
        bodies.append(body)
    if json.loads(bodies[0]) != publication:
        raise ValueError('Cold selected publication differs from live issued acknowledgement')
    facts = json.loads(bodies[1])
    if facts.get('executing_commit') != (trusted or baseline) or facts.get('baseline_commit') != baseline or facts.get('candidate_commit') != candidate or facts.get('candidate_code_executed') is not False:
        raise ValueError('Foreign selected execution/input vintage')
    pin = publication['operands']
    decoded = gzip.decompress(bodies[2])
    if len(decoded) != pin['decoded_bytes'] or hashlib.sha256(decoded).hexdigest() != pin['decoded_sha256']:
        raise ValueError('Whole selected operand decoded inverse differs')
    operands = json.loads(decoded)
    plan = operands.get('plan')
    if operands.get('kind') != 'complete-selected-continuous-operands-v1' or not isinstance(plan, dict):
        raise ValueError('Unsupported complete selected operand domain')
    ids = plan['required_ids']
    if ids != sorted(set(ids)) or sorted(operands['baseline']) != ids or sorted(operands['candidate']) != ids or plan['changed_ids'] != issued['changed_ids']:
        raise ValueError('Selected affected operand closure omitted/reordered owners')
    additions = operands.get('effective_additions', {'baseline': [], 'candidate': []})
    if sorted(additions) != ['baseline', 'candidate'] or any(not isinstance(v, list) for v in additions.values()):
        raise ValueError('Incomplete effective primitive operand domain')
    base_hashes = {'baseline': {}, 'candidate': {}}
    for row in facts['inverse']:
        vintage, identity = row['vintage'], row['id']
        if vintage not in base_hashes or identity in base_hashes[vintage] or not re.fullmatch('[a-f0-9]{64}', row['geometry_sha256']):
            raise ValueError('Foreign/duplicate complete source geometry inverse')
        base_hashes[vintage][identity] = row['geometry_sha256']
    if any(sorted(v) != ids for v in base_hashes.values()):
        raise ValueError('Complete source geometry inverse scope differs')
    with stage_timing('selected-continuous-python-compare'):
        result = compare_effective_primitives(detector, operands['baseline'], operands['candidate'], additions, base_hashes)
    if result['changed_location_ids'] != plan['changed_ids']:
        raise ValueError('Original polygon operator changed-ID closure differs from complete certificate')
    return {'version': 1, 'kind': 'trusted-selected-continuous-comparison-v1',
            'candidate_code_executed': False, 'issued_publication': publication,
            'source_binding': plan['source_bindings'], 'complete_owners': issued['complete_owners'],
            'required_ids': ids, 'original_strict_polygon_result': result,
            'status': result['status'], 'regressions': result['regressions'],
            'limits': ['Complete coordinate-derived exclusion and full affected source pointsets; original coverage/overlap predicates are unchanged.',
                       'No physical water/admin/history approval, repair assignment, release activation or deployment.']}


def selected_joint(repo, baseline, candidate, detector, *, trusted=None, checkpoint_destination=None):
    products = checkpoint_products_module(repo) if checkpoint_destination is not None else None
    if products is not None:
        products.admit_checkpoint_destination(checkpoint_destination)
    env = {key: value for key, value in os.environ.items() if key not in ['NODE_OPTIONS', 'NODE_PATH']}
    entrypoint = repo / 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-joint-entry.mjs'
    with tempfile.TemporaryDirectory(prefix='trusted-selected-joint-') as temporary:
        destination = pathlib.Path(temporary).resolve() / 'complete'
        raw = subprocess.check_output([os.environ.get('NODE', 'node'), '--expose-gc', str(entrypoint),
                                       str(repo), trusted or baseline, baseline, candidate, str(destination), sys.executable], env=env)
        if len(raw) > MAX_BYTES:
            raise ValueError('Joint selected acknowledgement exceeds output cap')
        issued = json.loads(raw)
        if issued.get('kind') != 'trusted-selected-joint-comparison-v1' or issued.get('candidate_code_executed') is not False:
            raise ValueError('Unsupported joint selected acknowledgement')
        if issued.get('mode') == 'legacy-cold-required':
            decision = issued.get('reuse_unavailable')
            if not isinstance(decision, dict) or decision.get('cold') not in ['candidate', 'baseline-and-candidate'] or not decision.get('reason'):
                raise ValueError('Joint fallback omitted its unavailable custody decision')
            return issued
        if issued.get('mode') != 'authenticated-checkpoint-append-v1' or not isinstance(issued.get('native'), dict):
            raise ValueError('Joint selected comparison did not complete native validation')
        native = issued['native']
        if native.get('candidate_code_executed') is not False or native.get('status') not in ['native-regressions-found', 'no-new-native-loss']:
            raise ValueError('Joint native comparison result is incomplete')
        if native['status'] == 'native-regressions-found':
            return issued
        issued['continuous_result'] = consume_selected_continuous(repo, baseline, candidate, detector,
                                                                  destination, issued.get('continuous'), trusted=trusted)
        original = issued['continuous_result'].get('original_strict_polygon_result', {})
        if (checkpoint_destination is not None and original.get('status') in ['no-footprint-change', 'no-new-regression']
                and original.get('regressions') in [None, 0]):
            issued['checkpoint'] = products.retain_checkpoint_products(destination, checkpoint_destination, issued,
                allowance=min(products.PHASE, selected_consumer_allowance(repo)))
        return issued



def run_applicability_collector(command, env, timeout=120):
    # Metadata acquisition may launch Git. A timeout must reap that owned group
    # before ordinary prefetch/full checks can resume in the same object store.
    if os.name != 'posix':
        raise OSError('Owned applicability process groups unavailable')
    child = subprocess.Popen(command, env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    try:
        stdout, stderr = child.communicate(timeout=timeout)
    finally:
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            raise RuntimeError('Cannot terminate owned applicability process group') from error
        try:
            child.communicate(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise RuntimeError('Applicability process group did not terminate') from error
    return subprocess.CompletedProcess(command, child.returncode, stdout, stderr)


def applicability_decline(reason, collector_reason=None):
    # Emit only fixed reason/operation categories, never child stderr, raw error
    # text, locators, environment values or candidate-supplied metadata.
    diagnostic = {'status': 'full-check-required', 'reason': reason}
    if isinstance(collector_reason, str):
        category, _, operation = collector_reason.partition(':')
        if category in {'immutable-object-unavailable', 'missing-strict-historical-commit',
                        'outside-source-publication-scope', 'source-scope-merge-base-unavailable',
                        'routing-strict-origin-acquisition-failed', 'routing-strict-graph-growth-limit',
                        'routing-strict-fetch-imported-blobs', 'invalid-routing-metadata',
                        'unsupported-reader-profile', 'identity-entry-limit', 'metadata-byte-limit'}:
            diagnostic['collector_reason'] = category
        if category == 'immutable-object-unavailable' and operation.split(':')[0] in {
                'merge-base', 'ls-tree', 'cat-file', 'diff-tree', 'rev-parse'}:
            diagnostic['operation'] = operation.split(':')[0]
    print(json.dumps({'geography_applicability': diagnostic}), file=sys.stderr, flush=True)
    return None


def unchanged_selected_inputs(repo, baseline, candidate):
    """Bounded applicability only; incomplete identity discovery keeps full checks."""
    if baseline == candidate:
        # A self-comparison must still execute its applicable scientific checks.
        return None
    env = dict(os.environ, GIT_NO_LAZY_FETCH='1', GIT_TERMINAL_PROMPT='0')
    for name in ['NODE_OPTIONS', 'NODE_PATH']:
        env.pop(name, None)
    try:
        result = run_applicability_collector([
            env.get('NODE', 'node'), str(repo / 'scripts/check-unchanged-selected-geography.mjs'),
            str(repo), baseline, candidate], env)
        if result.returncode:
            return applicability_decline('collector-process-failed')
        if len(result.stdout) > 2 * 1024 * 1024:
            return applicability_decline('collector-output-limit')
        proof = json.loads(result.stdout)
        if (not isinstance(proof, dict) or proof.get('version') != 1
                or proof.get('baseline_commit') != baseline
                or proof.get('candidate_commit') != candidate
                or proof.get('trusted_reader_policy_commit') != baseline
                or proof.get('candidate_code_executed') is not False):
            return applicability_decline('collector-binding-invalid')
        if proof.get('status') != 'unchanged-selected-inputs':
            return applicability_decline('collector-declined', proof.get('reason'))
        return proof
    except subprocess.TimeoutExpired:
        return applicability_decline('collector-timeout')
    except OSError:
        return applicability_decline('collector-unavailable')
    except ValueError:
        return applicability_decline('collector-output-invalid')


def inspect(repo, baseline, candidate, *, code_commit=None, prefetch=False, checkpoint_destination=None):
    immutable_sha(baseline)
    immutable_sha(candidate)
    code_commit = code_commit or baseline
    if code_commit not in [baseline, candidate]:
        raise ValueError('Checker code must be the exact baseline or candidate commit')
    software = code_commit != baseline
    with stage_timing('trusted-checkout-inspect'):
        trusted_inventory = verify_trusted_checkout(repo, code_commit)
    before, after = inventory(repo, baseline), inventory(repo, candidate)
    report = {'version': 1, 'method_id': 'worldatlas-trusted-geography-check-v1',
              'baseline_commit': baseline, 'candidate_commit': candidate,
              'trusted_code_commit': code_commit, 'trusted_code_inventory_sha256': trusted_inventory,
              'candidate_code_executed': software,
              'baseline_input_inventory': before, 'candidate_input_inventory': after,
              'published': False, 'source_approval': False}
    if software:
        report['execution_limits'] = [
            'Candidate checker code executed against distinct baseline and candidate data; no checkpoint reuse or new checkpoint authority.',
            'Nested child receipts retain their legacy candidate_code_executed=false marker verbatim. That marker is not evidence that candidate checker code was absent; this report binds actual executing code.']
    if not software and before == after and baseline != candidate:
        with stage_timing('unchanged-selected-inputs'):
            applicability = unchanged_selected_inputs(repo, baseline, candidate)
        if applicability is not None:
            return {**report, 'status': 'not-applicable', 'regressions': None,
                    'unchanged_selected_inputs': applicability,
                    'limits': ['Complete selected consumed-input and method identities are unchanged; applicability only, not fresh scientific validation or global gap clearance.',
                               'Independent source quality, evidence, review and current combined-tree consumer gates remain required.']}
    import sys
    sys.path.insert(0, str(repo / 'scripts'))
    spec = importlib.util.spec_from_file_location('trusted_geographic_detector', repo / 'scripts/check-geographic-regression.py')
    detector = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(detector)
    selected = any(git(repo, 'ls-tree', '-z', version, '--', 'data/ownership-selection.json')
                   for version in [baseline, candidate])
    joint = None
    if selected and not software:
        with stage_timing('selected-joint'):
            joint = selected_joint(repo, baseline, candidate, detector, checkpoint_destination=checkpoint_destination)
    if selected:
        import sys
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        if joint is not None and joint['mode'] == 'authenticated-checkpoint-append-v1':
            native = joint['native']
        else:
            # Eager whole-bank transport helps the legacy cold consumers, but
            # needlessly downloads sources/native assets for a qualified warm
            # checkpoint. Software always takes this genuine cold path; other
            # callers require the joint entry's explicit unavailable decision.
            if prefetch:
                with stage_timing('selected-prefetch'):
                    prefetch_declared_inputs(repo, baseline, candidate)
            with stage_timing('selected-native'):
                native_raw = subprocess.check_output([
                    os.environ.get('NODE', 'node'), str(repo / 'scripts/check-effective-geographic-regression.mjs'),
                    str(repo), baseline, candidate, sys.executable], stderr=subprocess.PIPE, env=env)
            if len(native_raw) > MAX_BYTES:
                raise ValueError('Selected native report exceeds bounded output')
            native = json.loads(native_raw)
        report['selected_native_report'] = native
        if native['status'] == 'native-regressions-found':
            return {**report, 'status': 'native-regressions-found',
                    'regressions': len(native['intervals']),
                    'limits': ['Existing owner loss/reassignment has no automatic water or political exception. The raw polygon gate is preserved.']}
    if selected:
        with stage_timing('selected-continuous'):
            continuous = joint['continuous_result'] if joint is not None and joint['mode'] == 'authenticated-checkpoint-append-v1' else selected_continuous(repo, baseline, candidate, detector, trusted=code_commit)
        report['selected_continuous_report'] = continuous
        if joint is not None and joint.get('checkpoint') is not None:
            report['checkpoint'] = joint['checkpoint']
        if continuous.get('regressions') not in [None, 0] or str(continuous.get('status', '')).startswith('blocked-'):
            return {**report, 'status': continuous['status'], 'regressions': continuous['regressions'],
                    'differential_report': continuous['original_strict_polygon_result'],
                    'limits': ['Selected complete footprint loss/overlap is enforced with original predicates; no automatic source exception.']}
    if before == after:
        return {**report, 'status': 'not-applicable', 'regressions': None,
                'limits': ['Live geography input blobs are unchanged; this is applicability evidence, not fresh polygon validation or a global gap clearance.']}
    # Execute only the verified code checkout; data commits remain immutable inputs.
    with stage_timing('raw-polygon'):
        result = detector.inspect(repo, baseline, candidate)
    return {**report, 'status': result['status'], 'regressions': result['regressions'],
            'differential_report': result,
            'limits': ['No automatic repair. Water-loss acceptance requires retained original physical sources, full-shape support and separate exact-head independent review.',
                       'Existing release, identity, regional certificate and historical import checks remain required.']}


def apply_adjudications(repo, candidate, report):
    # No proposed local envelope is accepted. Only baseline Node code can read
    # actual GitHub authority, using a read-only workflow token and exact head.
    if report['status'] != 'regressions-found':
        return report
    report['adjudication'] = {'status': 'blocked'}
    try:
        number, head = os.environ.get('GEOGRAPHY_PR_NUMBER'), os.environ.get('GEOGRAPHY_REVIEWED_HEAD')
        if not isinstance(number, str) or not re.fullmatch('[1-9][0-9]*', number):
            raise ValueError('Missing trusted PR context for source-backed adjudication')
        immutable_sha(head)
        env = dict(os.environ)
        for name in ['NODE_OPTIONS', 'NODE_PATH']:
            env.pop(name, None)
        # stdout contains bounded base64 original dossier bytes, never executable
        # candidate code. The child enforces 48 MiB transport; timeout is finite.
        result = subprocess.run(['node', str(repo / 'scripts/check-geographic-adjudications.mjs'),
                                 '--pr', number, '--head', head], cwd=repo, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        if result.returncode or len(result.stdout) > 48 * 1024 * 1024:
            raise ValueError('Trusted GitHub source-decision validation failed; rerun after exact-head independent review')
        envelope = json.loads(result.stdout)
        from geographic_adjudication import adjudicate
        report['adjudication'] = adjudicate(report, envelope, lambda name: read(repo, candidate, name))
    except Exception as error:  # Preserve raw findings on every failed adjudication.
        report['adjudication'] = {'status': 'blocked', 'reason': str(error)[:1024]}
        if getattr(error, 'unsupported_geometry', None) is not None:
            report['adjudication']['unsupported_geometry'] = error.unsupported_geometry
    return report


def fetch_candidate(repo, candidate):
    immutable_sha(candidate)
    # Read token stays in process environment, not arguments, logs or Git config.
    token = os.environ.get('GH_TOKEN')
    if token:
        for key in list(os.environ):
            if key.startswith('GIT_CONFIG_KEY_') or key.startswith('GIT_CONFIG_VALUE_'):
                del os.environ[key]
        os.environ['GIT_CONFIG_COUNT'] = '1'
        os.environ['GIT_CONFIG_KEY_0'] = 'http.https://github.com/.extraheader'
        os.environ['GIT_CONFIG_VALUE_0'] = 'AUTHORIZATION: basic ' + base64.b64encode(('x-access-token:' + token).encode()).decode()
    git(repo, 'fetch', '--quiet', '--no-tags', '--no-write-fetch-head', '--filter=blob:none', 'origin', candidate)


def verify_pr_candidate(repo, baseline, candidate, head):
    """Authenticate the proposed merge before any scientific inputs are read."""
    for value in [baseline, candidate, head]:
        immutable_sha(value)
    # Read the actual commit object, not rev-list: shallow checkout boundaries
    # do not erase its real parent identities.
    raw = git(repo, 'cat-file', '-p', candidate).decode()
    header = raw.split('\n\n', 1)[0].splitlines()
    parents = [line[7:] for line in header if line.startswith('parent ')]
    if parents != [baseline, head]:
        raise ValueError('Proposed geographic candidate must bind exact event base and reviewed head')


def main():
    import sys
    if not sys.flags.isolated or not sys.dont_write_bytecode:
        raise ValueError('Invoke the trusted checker with python -I -B')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1])
    parser.add_argument('--baseline', default=os.environ.get('GEOGRAPHY_BASELINE'))
    parser.add_argument('--candidate', default=os.environ.get('GEOGRAPHY_CANDIDATE'))
    parser.add_argument('--code-commit', default=os.environ.get('GEOGRAPHY_CODE_COMMIT'))
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--out', type=pathlib.Path, required=True)
    args = parser.parse_args()
    immutable_sha(args.baseline)
    immutable_sha(args.candidate)
    args.code_commit = args.code_commit or args.baseline
    if args.code_commit not in [args.baseline, args.candidate]:
        raise ValueError('Checker code must be the exact baseline or candidate commit')
    software = args.code_commit != args.baseline
    if software and any(os.environ.get(name) for name in ['GH_TOKEN', 'GITHUB_TOKEN', 'WORLDATLAS_CHECKOUT_TOKEN']):
        raise ValueError('Candidate checker must run without GitHub credentials')
    # Refuse collisions and symlink/dangling ancestors before any code or data
    # reads; the final exclusive open still handles a later destination race.
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    if args.out.exists():
        raise ValueError('Report destination already exists')
    if not args.out.absolute().parent.is_dir():
        raise ValueError('Report parent must be an existing ordinary directory')
    repo = args.repo.resolve()
    if software:
        # Workflow checkout removes authentication; fail closed if a caller left
        # credential configuration that anonymous immutable acquisition could use.
        if any(os.environ.get(name) for name in ['GIT_CONFIG_COUNT', 'GIT_ASKPASS', 'SSH_ASKPASS', 'GIT_SSH_COMMAND']):
            raise ValueError('Candidate checker cannot inherit Git authentication configuration')
        configured = subprocess.run(['git', '-C', str(repo), 'config', '--get-regexp',
                                     r'(^credential\.|\.extraheader$|^core\.askpass$|^url\.)'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if configured.returncode != 1:
            raise ValueError('Candidate checker requires credential-free Git configuration')
        remotes = git(repo, 'remote').decode().splitlines()
        for remote in remotes:
            if git(repo, 'remote', 'get-url', remote).decode().strip() not in [
                    'https://github.com/ChengshuLi/WorldAtlas', 'https://github.com/ChengshuLi/WorldAtlas.git']:
                raise ValueError('Candidate acquisition requires the anonymous public repository remote')
    with stage_timing('trusted-checkout-initial'):
        verify_trusted_checkout(repo, args.code_commit)
    if args.fetch:
        with stage_timing('candidate-fetch'):
            fetch_candidate(repo, args.candidate)
    comparison = os.environ.get('GEOGRAPHY_COMPARISON')
    if comparison is not None:
        if comparison != 'pull-request-merge-v1':
            raise ValueError('Unsupported geographic comparison')
        verify_pr_candidate(repo, args.baseline, args.candidate, os.environ.get('GEOGRAPHY_REVIEWED_HEAD'))
    result = inspect(repo, args.baseline, args.candidate, code_commit=args.code_commit, prefetch=args.fetch,
        checkpoint_destination=None if software else args.out.absolute().parent)
    if not software:
        result = apply_adjudications(repo, args.candidate, result)
    passed = result['status'] in ['not-applicable', 'no-footprint-change', 'no-new-regression'] or (
        result.get('adjudication', {}).get('status') == 'all-findings-supported-and-reviewed')
    result['gate_status'] = 'passed' if passed else 'blocked'
    raw = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if len(raw) > MAX_BYTES:
        raise ValueError('Geography check output exceeds bounded report size')
    if any(p.is_symlink() for p in [args.out, *args.out.absolute().parents]):
        raise ValueError('Symlink report path forbidden')
    with args.out.open('xb') as stream:
        stream.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
            stream.write('report_sha256=' + digest + '\n')
    print(json.dumps({'status': result['status'], 'regressions': result['regressions'],
                      'report_bytes': len(raw), 'report_sha256': hashlib.sha256(raw).hexdigest(),
                      **({'candidate_commit': args.candidate} if comparison else {})}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
