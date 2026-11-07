"""Independently verify source derivation before selected-seed validation.

This adapter does not authenticate a request on its own: the orchestrator must
independently trust and pin the request, this code, its dependencies and sources.
It is a research integration seam, not a replacement for the frozen validator.
"""
from caucasus_effective_snapshot import derive_verified
from caucasus_seed_gate import SOURCE_PINS, digest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = ('caucasus_stage2_validation.py', 'caucasus_effective_snapshot.py', 'caucasus_seed_gate.py',
        'caucasus_source_assembly.py', 'caucasus_compact_selectors.py', 'caucasus_selector_replay.py')


def verify_code(pins):
    if not isinstance(pins, dict) or set(pins) != set(CODE):
        raise ValueError('complete code pins required')
    for name in CODE:
        if not isinstance(pins[name], str) or len(pins[name]) != 64 or digest(HERE / name) != pins[name]:
            raise ValueError('source-derivation code pin mismatch')


def validate(validator, seed_report, groups, entity_codes, metric, *,
             request_path, request_sha256, recipe, recipe_sha256, hydro, author,
             code_sha256,
             guard=lambda: None):
    if not callable(validator) or not callable(guard):
        raise ValueError('independent validator and resource guard required')
    guard()
    verify_code(code_sha256)
    effective, trace = derive_verified(request_path, request_sha256, recipe, recipe_sha256, hydro, author)
    source_pin = trace['effective_snapshot']['original_snapshot_sha256']
    if seed_report.get('decision_snapshot_sha256') != source_pin:
        raise ValueError('seed report does not reference the original snapshot')
    # The established validator rechecks every region, closure, trace and rule
    # against the independently reconstructed effective view.
    guard()
    result = validator(effective, seed_report, groups, entity_codes, metric, guard=guard)
    guard()
    if digest(request_path) != request_sha256 or digest(recipe) != recipe_sha256 or (digest(hydro), digest(author)) != tuple(SOURCE_PINS.values()):
        raise ValueError('request or source inputs changed during validation')
    verify_code(code_sha256)
    return result, {'schema': 'caucasus-source-validation-v1', 'source_derivation': trace,
                    'code_sha256': dict(code_sha256)}
