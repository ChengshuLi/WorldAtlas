import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {prepareDeliveryRoleStaging} from '../scripts/delivery-handoff-advance.mjs';
const destination = '.cache/delivery-handoff/finalize';
const hash = (type, body) => createHash(type).update(body).digest('hex');
function entry(name, text = name) {
 const body = Buffer.from(text);
 return {body, pin: {path: name, commit: 'a'.repeat(40), mode: '100644', bytes: body.length,
  sha256: hash('sha256', body), git_blob_oid: hash('sha1', Buffer.concat([Buffer.from(`blob ${body.length}\0`), body]))}};
}
function fixture(t) {
 const root = fs.realpathSync(fs.mkdtempSync(path.join(os.tmpdir(), 'delivery-roles-')));
 t.after(() => fs.rmSync(root, {recursive: true, force: true}));
 return {root, target: name => path.join(root, destination, name),
  prepare: (entries, options = {}) => prepareDeliveryRoleStaging(root, destination, entries,
   {limits: {total: 4096}, ...options})};
}
test('preflight is read only, exact staging preserves original paths and matching resume', t => {
 const f = fixture(t), entries = [entry('coordination/engineering/a/source.json'), entry('data/reference.bin', '\0original\n')];
 const publish = f.prepare(entries);
 assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
 const result = publish(); assert.equal(result.created_files, 2);
 for (const e of entries) {assert.deepEqual(fs.readFileSync(f.target(e.pin.path)), e.body); assert.equal(fs.statSync(f.target(e.pin.path)).mode & 0o777, 0o644);}
 assert.equal(fs.existsSync(path.join(f.root, 'coordination')), false);
 assert.equal(f.prepare(entries)().resumed_files, 2);
});
test('all entries and destinations preflight before the first write', t => {
 const f = fixture(t), a = entry('first'), b = entry('last');
 fs.mkdirSync(path.dirname(f.target('last')), {recursive: true}); fs.writeFileSync(f.target('last'), 'partial');
 assert.throws(() => f.prepare([a, b]), /size\/mode|hash/);
 assert.equal(fs.existsSync(f.target('first')), false); assert.equal(fs.readFileSync(f.target('last'), 'utf8'), 'partial');
});
test('body identity, mode, traversal, duplicate conflicts and budgets refuse without writes', t => {
 const f = fixture(t), valid = entry('one');
 const cases = [
  [{...valid, body: Buffer.from('bad')}],
  [{...valid, pin: {...valid.pin, mode: '100755'}}],
  [entry('../escape')], [entry('/absolute')], [entry('a//b')],
  [valid, entry('one', 'different')],
  [{...valid, pin: {...valid.pin, git_blob_oid: 'b'.repeat(40)}}],
  [{...valid, pin: {...valid.pin, blob: 'b'.repeat(40)}}]
 ];
 for (const entries of cases) assert.throws(() => f.prepare(entries));
 assert.throws(() => f.prepare([valid], {limits: {total: 0}}), /budget/);
 assert.throws(() => f.prepare([valid], {limits: {total: 4096, member: 33554433}}), /allowance/);
 assert.throws(() => f.prepare([valid], {limits: {total: 4096, entries: 0}}), /entries/);
 assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
});
test('planned file/directory collisions refuse in either entry order', t => {
 const f = fixture(t);
 for (const entries of [[entry('a'), entry('a/b')], [entry('a/b'), entry('a')]]) assert.throws(() => f.prepare(entries), /collision/);
 assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
});
test('existing directories, files as ancestors and symlinks refuse before any write', t => {
 const f = fixture(t); fs.mkdirSync(f.target('directory'), {recursive: true});
 fs.writeFileSync(f.target('file'), 'sentinel');
 fs.symlinkSync(path.join(f.root, 'missing'), f.target('dangling'));
 fs.symlinkSync(f.root, f.target('ancestor'));
 for (const name of ['directory', 'file/child', 'dangling', 'ancestor/child']) assert.throws(() => f.prepare([entry('first'), entry(name)]), /Nonordinary/);
 assert.equal(fs.existsSync(f.target('first')), false); assert.equal(fs.readFileSync(f.target('file'), 'utf8'), 'sentinel');
});
test('publish rechecks the entire batch after preflight and captures caller buffers', t => {
 const f = fixture(t), a = entry('first'), b = entry('last'), publish = f.prepare([a, b]);
 a.body.fill(0); a.pin.path = 'changed';
 fs.mkdirSync(path.dirname(f.target('last')), {recursive: true}); fs.writeFileSync(f.target('last'), 'corrupt');
 assert.throws(publish); assert.equal(fs.existsSync(f.target('first')), false);
 fs.unlinkSync(f.target('last')); publish(); assert.equal(fs.readFileSync(f.target('first'), 'utf8'), 'first');
 assert.equal(fs.existsSync(f.target('changed')), false);
});
test('same-body duplicate paths stage once and share the existing bounded budget', t => {
 const f = fixture(t), a = entry('same'), charged = [];
 const budget = {add: pin => charged.push(pin.bytes), snapshot: () => ({})};
 assert.equal(f.prepare([a, a], {budget})().created_files, 1); assert.deepEqual(charged, [a.body.length]);
 const before = fs.readdirSync(path.join(f.root, destination));
 assert.throws(() => f.prepare([entry('new')], {budget: {add() {throw Error('budget refusal');}, snapshot() {}}}), /budget refusal/);
 assert.deepEqual(fs.readdirSync(path.join(f.root, destination)), before);
});
test('only the existing local cache delivery output convention is writable', t => {
 const f = fixture(t);
 for (const prefix of ['coordination/engineering/packet', '.cache/elsewhere', '.cache/delivery-handoff/../escape'])
  assert.throws(() => prepareDeliveryRoleStaging(f.root, prefix, [entry('a')], {limits: {total: 10}}), /output tree/);
});
test('same-size divergent files and wrong file modes are preserved and refused', t => {
 const f = fixture(t), a = entry('body', 'correct'); fs.mkdirSync(path.dirname(f.target('body')), {recursive: true});
 fs.writeFileSync(f.target('body'), 'changed', {mode: 0o644});
 assert.throws(() => f.prepare([entry('first'), a]), /hash/);
 assert.equal(fs.existsSync(f.target('first')), false); assert.equal(fs.readFileSync(f.target('body'), 'utf8'), 'changed');
 fs.writeFileSync(f.target('body'), a.body); fs.chmodSync(f.target('body'), 0o600);
 assert.throws(() => f.prepare([entry('first'), a]), /mode/);
 assert.equal(fs.statSync(f.target('body')).mode & 0o777, 0o600);
});
test('budget callback mutation refuses the complete batch before capture or publication', t => {
 const f = fixture(t), first = entry('first'), last = entry('last');
 const budget = {add() {last.body.fill(0);}, snapshot: () => ({})};
 assert.throws(() => f.prepare([first, last], {budget}), /changed during admission/);
 assert.equal(fs.existsSync(path.join(f.root, '.cache')), false);
});
