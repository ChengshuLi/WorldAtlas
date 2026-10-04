"""Verify additive policy provenance without changing frozen decision bytes."""
import hashlib
import json
import pathlib

DECISION = 'data/macro-foundation/europe-asia-boundary-decisions.json'
POLICY = 'data/macro-foundation/membership-decisions.json'
CORRECTION = 'data/macro-foundation/europe-asia-policy-provenance-correction-v1.json'
ORIGINAL_COMMIT = '604021bc42c99c6e852785aeb11ab576a04f5e83'
ORIGINAL_SHA = 'f9bfacaf140b6a8a3be6353d2d66f832d40d8e75dd2af0ca5bde4fece8f3bcf6'
POLICY_SHA = '999f3ca84a0eb4b60f300e422503894b31c4474228d6e52259438ada0979a846'
RECORDED_SHA = 'dbbd7870d4dcd039a84b851defdce8110da08cc96f132d7d6c9e87d4406b1803'


def verify(root, correction_path=None):
    root = pathlib.Path(root)
    raw = (root / DECISION).read_bytes()
    policy_raw = (root / POLICY).read_bytes()
    reference = json.loads(raw)['referenced_membership_policy']
    actual = hashlib.sha256(policy_raw).hexdigest()
    # Only the explicit immutable discrepancy may be corrected, not any new drift.
    if hashlib.sha256(raw).hexdigest() != ORIGINAL_SHA or actual != POLICY_SHA:
        raise ValueError('Frozen provenance inputs changed')
    correction = json.loads((pathlib.Path(correction_path) if correction_path else root / CORRECTION).read_bytes())
    expected = {
        'version': 1, 'issue': 727,
        'original': {'commit': ORIGINAL_COMMIT, 'path': DECISION, 'sha256': ORIGINAL_SHA,
                     'json_pointer': '/referenced_membership_policy',
                     'recorded_reference': {'path': POLICY, 'sha256': RECORDED_SHA}},
        'corrected_reference': {'commit': ORIGINAL_COMMIT, 'path': POLICY, 'sha256': POLICY_SHA},
        'earlier_vintage_origin': 'unknown',
        'effect': 'provenance-only; no geographic or historical changes'
    }
    if correction != expected or reference != expected['original']['recorded_reference']:
        raise ValueError('Unsupported or mismatched policy provenance correction')
    return {'status': 'corrected-binding-verified', 'policy_sha256': actual,
            'original_decision_sha256': ORIGINAL_SHA, 'correction_sha256':
            hashlib.sha256((pathlib.Path(correction_path) if correction_path else root / CORRECTION).read_bytes()).hexdigest(),
            'earlier_vintage_origin': 'unknown', 'geographic_approval': 'not-assessed'}


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[1])))
