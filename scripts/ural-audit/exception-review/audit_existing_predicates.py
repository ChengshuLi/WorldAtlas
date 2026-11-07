#!/usr/bin/env python3
"""Authenticate historical Ural diagnostics and report sparse mainland membership.

Produces diagnostic spans, never a geographic exception or map output.
"""
import argparse
import bisect
import collections
import hashlib
import json
import mmap
import struct
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


class Grid:
    def __init__(self, rows, runs, width, height):
        self.width, self.height = width, height
        self.offsets = [x[0] for x in struct.iter_unpack('<I', Path(rows).read_bytes())]
        require(len(self.offsets) == height + 1 and self.offsets[0] == 0,
                'invalid row index length or origin')
        require(all(a < b for a, b in zip(self.offsets, self.offsets[1:])),
                'empty or decreasing full-width row')
        self.file = open(runs, 'rb')
        self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
        require(len(self.data) == self.offsets[-1] * 8, 'run size mismatch')
        self.cache = {}

    def at(self, x, y):
        require(type(x) is int and type(y) is int and 0 <= x < self.width
                and 0 <= y < self.height, 'invalid query cell')
        if y not in self.cache:
            a, b = self.offsets[y:y+2]
            row = list(struct.iter_unpack('<II', self.data[a*8:b*8]))
            ends = [v[0] for v in row]
            require(ends[-1] == self.width and ends[0] > 0
                    and all(a < b for a, b in zip(ends, ends[1:])), 'invalid queried RLE row')
            self.cache[y] = (ends, [v[1] for v in row])
        ends, values = self.cache[y]
        return values[bisect.bisect_right(ends, x)]


def spans(cells):
    """Rows [y,x_start,x_end_exclusive,before,after,reference,seed]."""
    result = []
    for x, y, before, after, reference, seed in sorted(cells, key=lambda c: (c[1], c[0])):
        if result and result[-1][0] == y and result[-1][2] == x and result[-1][3:] == [before, after, reference, seed]:
            result[-1][2] += 1
        else:
            result.append([y, x, x+1, before, after, reference, seed])
    require(sum(s[2]-s[1] for s in result) == len(cells), 'span population mismatch')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('config')
    parser.add_argument('output')
    args = parser.parse_args()
    code_pin = sha(__file__)
    config_pin = sha(args.config)
    cfg = json.loads(Path(args.config).read_text())
    inputs = cfg['inputs']
    for name, value in inputs.items():
        require(sha(value['path']) == value['sha256'], 'input hash mismatch: '+name)
    get = lambda name: inputs[name]['path']
    width, height = cfg['grid']['width'], cfg['grid']['height']
    grids = {name: Grid(get(name+'_rows'), get(name+'_runs'), width, height)
             for name in ('physical', 'reference', 'seed', 'draft82', 'draft136_before', 'draft136_after')}
    report = json.loads(Path(get('seed_report')).read_text())
    rule = next(r for r in report['seed_rules'] if r['group_id'] == 'mainland-eurasia')
    require(rule['component_id_current_generation_only'] == 650207 and
            rule['inside_code'] == 19 and rule['outside_code'] == 18, 'unexpected Eurasia seed rule')
    for kind in ('rows', 'runs'):
        require(report['seed_'+kind+'_sha256'] == inputs['seed_'+kind]['sha256'], 'seed report binding mismatch')
        require(report['physical_'+kind+'_sha256'] == inputs['physical_'+kind]['sha256'], 'physical report binding mismatch')
    mountain = json.loads(Path(get('mountain_diagnostic')).read_text())['cells']
    delta = json.loads(Path(get('delta_diagnostic')).read_text())['cells']
    results = []
    for name, source in [('historical-draft82-mountain', mountain), ('historical-draft136-delta-overlay', delta)]:
        seen, cells, counts = set(), [], collections.Counter()
        for entry in source:
            if isinstance(entry, dict):
                x, y, after, before = entry['x'], entry['y'], entry['candidate'], entry['reference']
                require(grids['draft82'].at(x,y) == after, 'draft82 cell differs from diagnostic')
            else:
                x, y, before, after = entry
                require(grids['draft136_before'].at(x,y) == before and
                        grids['draft136_after'].at(x,y) == after, 'draft136 event differs from diagnostic')
            require((x,y) not in seen, 'duplicate diagnostic cell')
            seen.add((x,y))
            require({before,after} == {18,19} and grids['physical'].at(x,y) == 17,
                    'not a physical-land Europe/Asia change')
            reference, seed = grids['reference'].at(x,y), grids['seed'].at(x,y)
            require(reference in (18,19), 'reference label outside Europe/Asia')
            if isinstance(entry,dict):
                require(reference == before, 'reference label differs from mountain diagnostic')
            counts['cells'] += 1
            counts['in_selected_physical_eurasia_root' if seed in (18,19) else 'outside_selected_physical_eurasia_root'] += 1
            cells.append([x,y,before,after,reference,seed])
        results.append({'name':name,'counts':dict(counts),'spans':spans(cells)})
    for name,value in inputs.items():
        require(sha(value['path']) == value['sha256'], 'input changed: '+name)
    require(sha(__file__) == code_pin and sha(args.config) == config_pin, 'code/config changed')
    output = {'schema':'ural-existing-predicate-sparse-audit-v1',
              'status':'historical-diagnostic-not-an-allowlist', 'publishable_as_exception':False,
              'code_sha256':code_pin,'config_sha256':config_pin,'grid':cfg['grid'],'inputs':inputs,
              'span_columns':['y','x_start','x_end_exclusive','event_before','event_after','v7_reference','qualified_seed'],
              'selected_component_rule':rule,'results':results,
              'limitations':['These exact spans authenticate historical diagnostic events, not the current candidate or user-approved exceptions.',
                             'Seed values 18/19 prove membership in the pinned selected physical component only; zero excludes that component.',
                             'A component of the physical/reference shared-land intersection has not been constructed or authenticated here.',
                             'Neither Eurasia component membership nor Europe/Asia label pairs exempt unrelated errors.',
                             'No Caucasus, Panama, physical-mask exception list, selected boundary change, or map rebuild is produced.']}
    with open(args.output,'x') as f:
        json.dump(output,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    print(json.dumps([{'name':r['name'],'counts':r['counts'],'spans':len(r['spans'])} for r in results]))


if __name__ == '__main__':
    main()
