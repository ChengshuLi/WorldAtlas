"""Compare one completed retained proof, without executing any scientific input."""
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys

BASE = 'dd7db1d22823427b21afeeecab932d36d8728f76'
PRIOR = 'coordination/engineering/continuous-candidate-frame-20261012/retained-proof-001/'
ORIGINAL = 'coordination/engineering/nor-grc-congo-delivery-20261011/combined-selected/corrected-continuous-002/continuous.json'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def retained(path):
    return subprocess.check_output(['git', 'show', BASE + ':' + path], env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'})


def main():
    assert len(sys.argv) == 2
    run = pathlib.Path(sys.argv[1]).absolute()
    for directory in [run, *run.parents]:
        assert directory.is_dir() and not directory.is_symlink()
    assert not os.path.lexists(run / 'comparison.json')
    for leaf in ['stdout.log', 'stderr.log', 'admission.json', 'process-group.json',
                 'complete/publication.json', 'complete/facts.json', 'complete/operands.json.gz',
                 'complete/baseline/publication.json', 'complete/baseline/certificate.json.gz',
                 'complete/candidate/publication.json', 'complete/candidate/certificate.json.gz']:
        path = run / leaf
        assert path.is_file() and not path.is_symlink()
        for ancestor in path.parents:
            assert ancestor.is_dir() and not ancestor.is_symlink()
    publication = json.loads((run / 'complete/publication.json').read_bytes())
    encoded = (run / 'complete/operands.json.gz').read_bytes()
    decoded = gzip.decompress(encoded)
    acknowledgement = json.loads((run / 'stdout.log').read_bytes())
    assert publication == acknowledgement['publication']
    descriptor = publication['operands']
    assert len(encoded) == descriptor['bytes'] and digest(encoded) == descriptor['sha256']
    assert len(decoded) == descriptor['decoded_bytes'] and digest(decoded) == descriptor['decoded_sha256']
    old_encoded = retained(PRIOR + 'complete/operands.json.gz')
    assert encoded == old_encoded and decoded == gzip.decompress(old_encoded)
    old_publication = json.loads(retained(PRIOR + 'complete/publication.json'))
    original_body = retained(ORIGINAL)
    original = json.loads(original_body)
    assert descriptor == old_publication['operands'] == original['issued_publication']['operands']
    assert original['status'] == 'no-new-regression' and original['regressions'] == 0
    facts_body = (run / 'complete/facts.json').read_bytes()
    assert len(facts_body) == publication['facts']['bytes'] and digest(facts_body) == publication['facts']['sha256']
    facts = json.loads(facts_body)
    old_facts_body = retained(PRIOR + 'complete/facts.json')
    assert len(old_facts_body) == old_publication['facts']['bytes'] and digest(old_facts_body) == old_publication['facts']['sha256']
    old_facts = json.loads(old_facts_body)
    assert facts['plan'] == old_facts['plan'] and facts['inverse'] == old_facts['inverse']
    assert facts['plan']['source_bindings'] == original['source_binding']
    assert facts['plan']['required_ids'] == original['required_ids']
    admission = json.loads((run / 'admission.json').read_bytes())
    group = json.loads((run / 'process-group.json').read_bytes())
    assert facts['executing_commit'] == admission['execution_commit']
    assert facts['baseline_commit'] == admission['baseline_commit'] and facts['candidate_commit'] == admission['candidate_commit']
    assert group['exit_code'] == group['parent_exit_code'] == 0 and group['stopped'] is None
    assert group['survivors_at_parent_terminal'] == group['survivors_after_cleanup'] == []
    assert group['sampled_process_group_peak_rss_bytes'] < admission['job_reserved_bytes']
    events = [json.loads(line) for line in (run / 'stderr.log').read_text().splitlines() if line.startswith('{')]
    selections = [row for row in events if row.get('selected_continuous_stage', '').endswith('-selection')]
    starts = [row for row in selections if row['event'] == 'start']
    ends = [row for row in selections if row['event'] == 'end']
    expected = [('coordinate-selection', admission['baseline_commit']), ('coordinate-selection', admission['candidate_commit']), ('required-side-selection', admission['baseline_commit'])]
    assert [(row['selected_continuous_stage'], row['selected']) for row in starts] == expected
    assert [(row['selected_continuous_stage'], row['selected']) for row in ends] == expected
    owners = [row['facts']['complete_owners'] for row in facts['complete_cold_custody']]
    assert owners == [original['complete_owners'], original['complete_owners']]
    certificate_comparisons = []
    for side in ['baseline', 'candidate']:
        side_publication = json.loads((run / f'complete/{side}/publication.json').read_bytes())
        assert side_publication == facts['source_stages'][0 if side == 'baseline' else 1]
        old_side_publication = json.loads(retained(PRIOR + f'complete/{side}/publication.json'))
        bodies = [(run / f'complete/{side}/certificate.json.gz').read_bytes(),
                  retained(PRIOR + f'complete/{side}/certificate.json.gz')]
        certificates = []
        for body, issued in zip(bodies, [side_publication, old_side_publication]):
            certificate_descriptor = issued['certificate']
            unpacked = gzip.decompress(body)
            assert len(body) == certificate_descriptor['bytes'] and digest(body) == certificate_descriptor['sha256']
            assert len(unpacked) == certificate_descriptor['decoded_bytes'] and digest(unpacked) == certificate_descriptor['decoded_sha256']
            certificates.append(json.loads(unpacked))
        phases = [certificate.pop('complete_phase_bytes') for certificate in certificates]
        assert certificates[0] == certificates[1]
        assert len(certificates[0]['entries']) == owners[0]
        certificate_comparisons.append({'vintage': side, 'complete_semantic_certificate_equal': True,
                                       'excluded_fields': ['complete_phase_bytes'],
                                       'complete_owners': len(certificates[0]['entries']),
                                       'complete_sources': len(certificates[0]['inputs']),
                                       'complete_phase_bytes': phases[0],
                                       'historical_complete_phase_bytes': phases[1]})
        del bodies, certificates, body, unpacked
    previous = json.loads(retained(PRIOR + 'comparison.json'))
    comparison = {
        'kind': 'single-vintage-retained-operand-comparison',
        'execution_commit': admission['execution_commit'],
        'baseline_commit': admission['baseline_commit'], 'candidate_commit': admission['candidate_commit'],
        'retained_at': BASE,
        'retained_original': {'path': ORIGINAL, 'bytes': len(original_body), 'sha256': digest(original_body)},
        'prior_comparison_path': PRIOR + 'comparison.json',
        'whole_operands_equal': True, 'complete_plan_equal': True, 'complete_inverse_equal': True,
        'publication_matches_invocation_acknowledgement': True, 'certificate_comparisons': certificate_comparisons,
        'original_source_bindings_equal': True, 'operands': descriptor,
        'selection_load_count': len(ends), 'selection_loads': ends,
        'selection_load_elapsed_ms': sum(row['elapsed_ms'] for row in ends),
        'complete_owners': owners[0], 'required_owners': len(facts['plan']['required_ids']),
        'changed_owners': len(facts['plan']['changed_ids']),
        'node_elapsed_seconds': group['elapsed_seconds'],
        'sampled_process_group_peak_rss_bytes': group['sampled_process_group_peak_rss_bytes'],
        'historical_execution_commit': previous['execution_commit'],
        'historical_node_elapsed_seconds': previous['node_elapsed_seconds'],
        'historical_selection_load_count': previous['selection_load_count'],
        'historical_selection_load_elapsed_ms': previous['selection_load_elapsed_ms'],
        'historical_sampled_process_group_peak_rss_bytes': previous['sampled_process_group_peak_rss_bytes'],
        'original_polygon_result_reused': True, 'original_status': original['status'],
        'original_regressions': original['regressions'],
        'limits': [
            'One real-input local execution compared with retained historical runs, not a controlled same-time or hosted speedup benchmark.',
            'Both sampled process-group peaks use 50 ms observations and can miss shorter peaks.',
            'The unchanged original strict polygon result is reused only after complete encoded/decoded operand, source binding, affected plan and inverse equality; it was not rerun.'
        ]
    }
    with (run / 'comparison.json').open('x') as output:
        json.dump(comparison, output, indent=2)
        output.write('\n')
    print(json.dumps(comparison, indent=2))


if __name__ == '__main__':
    main()
