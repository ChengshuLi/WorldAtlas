import test from 'node:test';
import assert from 'node:assert/strict';
import {assignCategoryColors,auditCategoryColors} from '../scripts/build-category-palette.mjs';
import {displayCategoryKey} from '../src/color-perception.js';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {categoryColor,legacyCategoryColor} from '../src/model.js';
test('fixed graph assignment is independent of input ordering and meets a dense categorical control', () => {
  const keys=['a','b','c','d','e'],edges=keys.flatMap((a,i)=>keys.slice(i+1).map(b=>[a,b]));
  const colors=assignCategoryColors(keys,edges);
  assert.deepEqual(colors,assignCategoryColors([...keys].reverse(),[...edges].reverse().map(([a,b])=>[b,a])));
  for(const row of Object.values(auditCategoryColors(colors,edges).models))assert.equal(row.below_budget,0);
  assert.ok(Object.values(colors).every(value=>/^#[a-f\d]{6}$/.test(value)));
});
test('concurrent names sharing the upstream ID get distinct presentation colors without new source IDs', () => {
  const id='owner:Q148',a=displayCategoryKey(id,"People's Republic of China"),b=displayCategoryKey(id,'Republic of China');
  const colors=assignCategoryColors([a,b],[[a,b]]);
  assert.notEqual(colors[a],colors[b]);
  for(const row of Object.values(auditCategoryColors(colors,[[a,b]]).models))assert.equal(row.below_budget,0);
  assert.equal(JSON.parse(a)[0],id);assert.equal(JSON.parse(b)[0],id);
});
test('unconstrained names of the same identity retain the same preferred color', () => {
  const a=displayCategoryKey('owner:stable','Older source name'),b=displayCategoryKey('owner:stable','Newer source name');
  const colors=assignCategoryColors([a,b],[]);assert.equal(colors[a],colors[b]);
});
test('invalid or incomplete category graphs are rejected', () => {
  assert.throws(()=>assignCategoryColors(['a','a'],[]),/Invalid/);
  assert.throws(()=>assignCategoryColors(['a'],[['a','missing']]),/Unknown/);
  assert.throws(()=>assignCategoryColors(['a'],[],{passes:13}),/Invalid/);
  assert.throws(()=>auditCategoryColors({a:'#ffffff'},[['a','b']]),/Missing/);
});
test('the shipped palette passes all pinned historical constraints and matches the audited modern candidate', () => {
  const directory='data/engineering/palette-contrast-20261003-7e91/';
  const graph=JSON.parse(gunzipSync(fs.readFileSync(directory+'all-time-contrast-constraints.json.gz')));
  const candidate=JSON.parse(fs.readFileSync(directory+'palette-all-times-modern-candidate.json'));
  const report=JSON.parse(fs.readFileSync(directory+'contrast-all-times-modern-audit.json'));
  const actual=Object.fromEntries(Object.keys(candidate.colors).map(key=>[key,categoryColor(key)]));
  assert.deepEqual(actual,candidate.colors);
  assert.equal(createHash('sha256').update(JSON.stringify(actual)).digest('hex'),report.candidate_colors_sha256);
  const audit=auditCategoryColors(actual,[...graph.adjacent,...graph.nearby,...graph.concurrent_source_aliases]);
  for(const row of Object.values(audit.models))assert.equal(row.below_budget,0);
  assert.equal(categoryColor(null),'#53615c');
  assert.equal(categoryColor(displayCategoryKey('new:hosted-only','Actual incoming name')),legacyCategoryColor('new:hosted-only'));
});
