#!/usr/bin/env python3
"""Copy an explicitly declared source stage without numeric reserialization."""
import argparse, hashlib, json, pathlib, shutil


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def materialize(index_path, output, proof_path):
    if output.exists() or proof_path.exists():
        raise ValueError('Fresh output and proof paths required')
    base = index_path.parent
    index = json.loads(index_path.read_bytes())
    output.mkdir(parents=True)
    parts = []
    for relative in index['parts']:
        path = pathlib.PurePosixPath(relative)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Invalid declared part path')
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base / relative, destination)
        if sha(base / relative) != sha(destination):
            raise ValueError('Copied source part differs')
        parts.append({'path': relative, 'sha256': sha(destination)})
    for name in ['world-index.json', 'hierarchy.json']:
        shutil.copyfile(base / name, output / name)
    proof = {'version': 1, 'input_index_sha256': sha(index_path), 'declared_parts': parts,
        'hierarchy_sha256': sha(output / 'hierarchy.json'),
        'method': 'Byte-for-byte self-contained copy of declared parts; no reserialization.',
        'source_mutated': False, 'source_path_validation_weakened': False}
    proof_path.write_text(json.dumps(proof, separators=(',', ':')))
    print(json.dumps({'parts_materialized': len(parts), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['index', 'output', 'proof']:
        parser.add_argument('--' + name, type=pathlib.Path, required=True)
    args = parser.parse_args()
    materialize(args.index, args.output, args.proof)
