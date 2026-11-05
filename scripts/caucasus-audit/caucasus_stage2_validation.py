"""Independently verify source derivation before selected-seed validation.

This adapter does not authenticate a request on its own: the orchestrator must
independently trust and pin the request, this code, its dependencies and sources.
It is a research integration seam, not a replacement for the frozen validator.
"""
from caucasus_effective_snapshot import derive_verified
from caucasus_seed_gate import SOURCE_PINS, digest


def validate(validator, seed_report, groups, entity_codes, metric, *,
             request_path, request_sha256, recipe, recipe_sha256, hydro, author,
             guard=lambda: None):
    if not callable(validator) or not callable(guard):
        raise ValueError('independent validator and resource guard required')
    guard()
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
    return result, {'schema': 'caucasus-source-validation-v1', 'source_derivation': trace}
