"""Canonicalize the selected recipe read as PostgreSQL jsonb text.

Use `(provenance->'source_assembly_v1'->'recipe')::text` in the query.
Reading the value as text preserves numeric scale across JSON clients that
otherwise serialize 1.0 as 1. This helper does not access or modify Neon.
"""
import argparse
import hashlib
import json
from pathlib import Path


def canonical_recipe(text, expected_sha256):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError('duplicate recipe key')
            value[key] = item
        return value
    def invalid(value):
        raise ValueError('non-finite recipe value: ' + value)
    recipe = json.loads(text, object_pairs_hook=unique, parse_constant=invalid)
    if not isinstance(recipe, dict) or recipe.get('schema') != 'caucasus-selector-runs-research-v1':
        raise ValueError('unexpected recipe schema')
    data = json.dumps(recipe, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('recipe digest mismatch: check that Neon jsonb was read as text')
    return data


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--recipe-text', required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    data = canonical_recipe(Path(a.recipe_text).read_text(encoding='utf-8'), a.sha256)
    with open(a.output, 'xb') as out:
        out.write(data)
    print(json.dumps({'sha256': a.sha256, 'bytes': len(data)}, sort_keys=True))


if __name__ == '__main__':
    main()
