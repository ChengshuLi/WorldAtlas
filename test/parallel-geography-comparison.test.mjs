import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {valueBytes, valueSha, compareVersionedRepairLedgers} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

// A real fork and three-way merge feed immutable Git blobs to the unchanged
// original-authority gate. No fixture claims source/scientific approval.
test('parallel main authority is preserved by composition; actual removal and rebinding still fail', t => {
  const scratch = path.resolve('.cache/parallel-geography');
  fs.mkdirSync(scratch, {recursive: true});
  const repo = fs.mkdtempSync(path.join(scratch, 'fixture-'));
  t.after(() => fs.rmSync(repo, {recursive: true, force: true}));
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {stdio: ['ignore', 'pipe', 'pipe']}).toString().trim();
  git('init', '-q'); git('config', 'user.name', 'Synthetic control'); git('config', 'user.email', 'control@example.invalid');
  const write = (name, value) => fs.writeFileSync(path.join(repo, name), valueBytes(value));
  const commit = () => {git('add', '.'); git('commit', '-qm', 'Synthetic control'); return git('rev-parse', 'HEAD');};
  const read = (sha, name) => JSON.parse(git('show', `${sha}:${name}`));
  const pin = (name, value) => {const raw = valueBytes(value); return {commit: '1'.repeat(40), path: name,
    mode: '100644', git_blob_oid: createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex'),
    bytes: raw.length, sha256: valueSha(value)};};
  const authority = name => {const rule_preimage = pin(`${name}/rule.json`, {version: 3, source_profile: name});
    const entry = {policy_id: 'retained-source-addition', policy_version: 3, rule_sha256: rule_preimage.sha256,
      rule_preimage, source_authority: pin(`${name}/source.json`, {synthetic: name})};
    return {...entry, authority_sha256: valueSha(entry)};};
  const first = authority('initial'), parallel = authority('parallel');
  const select = entries => {const registry = {version: 1, kind: 'retained-rule-authority-registry-v1',
    entries: [...entries].sort((a,b) => a.authority_sha256.localeCompare(b.authority_sha256))};
    write('registry.json', registry); write('ledger.json', {version: 2, kind: 'native-additive-repair-ledger-v2',
      authority_registry_sha256: valueSha(registry), scope_ids: [], rows: []});};
  const compare = (base, candidate) => compareVersionedRepairLedgers(read(base, 'ledger.json'), read(candidate, 'ledger.json'),
    {beforeRegistry: read(base, 'registry.json'), afterRegistry: read(candidate, 'registry.json')});
  select([first]); const fork = commit();
  write('authored.json', {change: 'unrelated executable change'}); const head = commit();
  git('checkout', '-q', '--detach', fork); select([first, parallel]); const main = commit();
  assert.throws(() => compare(main, head), /Retained original authority removed\/rebound/);
  git('merge', '--no-ff', '-qm', 'Combine unchanged author and advanced main', head); const combined = git('rev-parse', 'HEAD');
  assert.equal(compare(main, combined).preserved_authorities, 2);
  assert.deepEqual(read(combined, 'registry.json'), read(main, 'registry.json'));
  assert.deepEqual(read(combined, 'authored.json'), read(head, 'authored.json'));
  for (const entries of [[first], [first, authority('rebound')]]) {
    git('checkout', '-q', '--detach', main); select(entries); const destructiveHead = commit();
    git('checkout', '-q', '--detach', main);
    git('merge', '--no-ff', '-qm', 'Actual destructive proposed merge', destructiveHead);
    assert.throws(() => compare(main, git('rev-parse', 'HEAD')), /Retained original authority removed\/rebound/);
  }
});
