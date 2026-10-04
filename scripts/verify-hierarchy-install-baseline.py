"""Guard an offline hierarchy generation with every declared immutable data input."""
import argparse
import gzip
import json
from pathlib import Path
from evidence.immutable import Baseline, canonical_json, sha256

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--inventory', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
raw = args.inventory.read_bytes()
inventory = json.loads(gzip.decompress(raw))
if inventory['version'] != 1 or args.receipt.exists():
    raise ValueError('Version-one inventory and fresh receipt required')
files = inventory['files']
if len({row['path'] for row in files}) != len(files):
    raise ValueError('Duplicate inventory input')
# Review partitions stay below the gate limits; this never raises byte limits.
partitions, current, size = [], [], 0
for row in files:
    if current and (len(current) == 400 or size + row['bytes'] > 128 * 1024 * 1024):
        partitions.append(current)
        current, size = [], 0
    current.append(row)
    size += row['bytes']
if current:
    partitions.append(current)
for partition in partitions:
    baseline = Baseline(root, inventory['baseline_commit'], partition)
    for row in partition:
        local = root / row['path']
        if not local.is_file() or local.is_symlink() or local.read_bytes() != baseline.read(row['path']):
            raise ValueError('Checkout input differs from immutable baseline: ' + row['path'])
result = {'version': 1, 'verified': True, 'baseline_commit': inventory['baseline_commit'],
          'inventory_sha256': sha256(raw), 'files_verified': len(files),
          'partitions': [{'files': len(part), 'bytes': sum(row['bytes'] for row in part)} for part in partitions],
          'limits': ['Compressed archive bytes are preserved; release replay separately verifies every extracted identity-proof member.'],
          'historical_claims_transferred': False}
args.receipt.write_bytes(canonical_json(result))
print(json.dumps(result))
