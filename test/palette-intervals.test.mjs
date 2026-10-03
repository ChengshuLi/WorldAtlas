import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';

test('contrast constraints use actual half-open interval overlap, never range envelopes', () => {
  const result=spawnSync('python3',['-c',`
import importlib.util
s=importlib.util.spec_from_file_location('audit','scripts/audit-palette-all-times.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
assert not m.overlaps([[1900,1910]],[[1910,1920]])
assert not m.overlaps([[1900,1910],[1950,1960]],[[1920,1930]])
assert m.overlaps([[1900,1910],[1950,1960]],[[1959,1965]])
assert m.merge_ranges([(1950,1960),(1900,1910),(1905,1915),(1915,1920)])==[[1900,1920],[1950,1960]]
`],{encoding:'utf8'});
  assert.equal(result.status,0,result.stderr);
});
