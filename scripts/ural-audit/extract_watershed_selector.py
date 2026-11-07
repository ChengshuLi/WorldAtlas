#!/usr/bin/env python3
"""Extract the pinned Ural route selector and chord template from Neon export.

This is an explicit structured selection input. It does not claim to recover
the historical construction of the selected line.
"""
import argparse
import hashlib
import json
from pathlib import Path

SNAPSHOT_SHA = '615bc1aaa67d099ebd140dc172fd54885d66e82ef595a57a97e5a284f483f7cc'
SELECTOR_SHA = '0a1aee04c5d60fec6f039b709720f2c7e4ae7f2522d8224fdfe0d9086978ccb4'
TEMPLATE_SHA = '87c92c1490692fd79a33c48fe365c9f44ffcc4c9705c243fae343f5185939705'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, required=True)
    parser.add_argument('--selector', type=Path, required=True)
    parser.add_argument('--template', type=Path, required=True)
    args = parser.parse_args()
    raw = args.snapshot.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA:
        raise ValueError('snapshot hash mismatch')
    snap = json.loads(raw)
    items = [b for b in snap['mainland_boundaries'] if b['boundary_id'] == 'ural_kara_coast_to_caspian']
    if len(items) != 1:
        raise ValueError('Ural selector boundary is ambiguous')
    geometry = items[0]['geometry']
    gh = hashlib.sha256(json.dumps(geometry, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    if gh != items[0]['geometry_sha256'] or gh != '5a6526344cacbc1a23be174f589cec9710a0f317360ec5c8737ba6956c3f7fe2':
        raise ValueError('selected geometry hash mismatch')
    selector = [[int(x) if isinstance(x, float) and x.is_integer() else x for x in p]
                for p in geometry['coordinates'][:4954]]
    omit = set(range(4252, 4259)) | set(range(4674, 4681))
    template = [p for i, p in enumerate(selector) if i not in omit]
    for path, value, expected in ((args.selector, selector, SELECTOR_SHA),
                                  (args.template, template, TEMPLATE_SHA)):
        payload = (json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n').encode()
        if hashlib.sha256(payload).hexdigest() != expected:
            raise ValueError('selector or template hash mismatch')
        with path.open('xb') as f:
            f.write(payload)
    if hashlib.sha256(args.snapshot.read_bytes()).hexdigest() != SNAPSHOT_SHA:
        raise ValueError('snapshot changed during extraction')
    print(json.dumps({'selector_sha256': SELECTOR_SHA, 'template_sha256': TEMPLATE_SHA,
                      'note': 'Template omits interpolation vertices; raw-edge coverage must be checked separately.'}))


if __name__ == '__main__':
    main()
