import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validatePremergeManifest} from '../../../scripts/premerge-evidence.mjs';
import {repositoryReader, sha256} from '../../../scripts/evidence-quality.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..');
const owned = 'data/regional-review/southeastern-county-vintage-978-erratum/';
const manifestPath = owned + 'evidence-quality.json';
const scriptPath = owned + 'numeric-table-negative-control-v4.mjs';
const receiptPath = owned + 'numeric-table-negative-control-v4.json';
const bytes = value => Buffer.from(JSON.stringify(value, null, 2) + '\n');
const descriptor = (name, raw, role) => ({path:name, bytes:raw.length, sha256:sha256(raw), hash_kind:'file-bytes', role});
const need = (ok, message) => { if (!ok) throw Error(message); };

const manifest = JSON.parse(fs.readFileSync(path.join(root, manifestPath), 'utf8'));
const scriptRaw = fs.readFileSync(path.join(root, scriptPath));
const table = manifest.rendered_tables.find(value => value.path.endsWith('/metric-table.md'));
need(table?.rows?.length, 'Missing generated metric table rows');
const first = table.rows[0], metric = manifest.metrics.find(value => value.id === first.metric_id);
const oldValue = (metric.value * (first.scale ?? 1)).toFixed(first.decimals);
const alteredValue = oldValue === '0.11111111' ? '0.22222222' : '0.11111111';
const tablePath = table.path;
const tableRaw = fs.readFileSync(path.join(root, tablePath));
const lines = tableRaw.toString('utf8').split('\n');
need(lines[first.line - 1] === first.template.replaceAll('{value}', oldValue), 'Metric row template is not the current output');
lines[first.line - 1] = first.template.replaceAll('{value}', alteredValue);
const alteredTable = Buffer.from(lines.join('\n'));

const methodId = 'six-county-frozen-reproduction';
const body = {
  method_id: methodId,
  kind: 'negative-control',
  outcome: 'passed',
  test: 'The repository premerge evidence validator rejects a rendered metric row that contradicts its numeric ledger after the fixture row bytes and declared whole-file descriptor hash/length are both refreshed.',
  table_path: tablePath,
  table_line: first.line,
  metric_id: first.metric_id,
  ledger_value: metric.value,
  original_rendered_value: oldValue,
  manipulated_rendered_value: alteredValue,
  original_table_sha256: sha256(tableRaw),
  manipulated_table_sha256: sha256(alteredTable),
  fixture_descriptor_sha256_refreshed: true,
  validator: 'scripts/premerge-evidence.mjs validatePremergeManifest',
  harness_sha256: sha256(scriptRaw),
  symlink_escape_rejected: true,
};
const receiptRaw = bytes(body);

// Mirror the actual added-file/change inventory, including this fixture harness
// and its receipt when the test is first run before the manifest is refreshed.
const fixture = structuredClone(manifest);
const extra = [descriptor(scriptPath, scriptRaw, 'control-code'), descriptor(receiptPath, receiptRaw, 'validation-control')];
for (const item of extra) { fixture.outputs = fixture.outputs.filter(output => output.path !== item.path); fixture.outputs.push(item); }
for (const item of extra) if (!fixture.change_receipts.some(row => row.path === item.path)) {
  fixture.change_receipts.push({path:item.path, status:'added'});
}
const tableDescriptor = fixture.outputs.find(output => output.path === tablePath);
need(tableDescriptor, 'Generated table descriptor is missing');
const files = fixture.change_receipts.map(row => ({filename:row.path, status:row.status, previous_filename:row.previous_path}));
const reservation = {worker_id:fixture.worker_id, owned_paths:[owned]};
const spec = {mode:'geography', evidence_quality:{subject_ids:fixture.subject_ids, pins:fixture.baseline.pins}};
const issue = {number:1252};
const pr = {base:{sha:fixture.baseline.commit}, changed_files:files.length};
const baseReader = repositoryReader(root);
const readOriginal = (name, vintage) => {
  if (vintage === 'candidate' && name === receiptPath) return receiptRaw;
  return baseReader(name, vintage);
};
const context = {files, manifestPath, issue, spec, reservation, branch:'geography/county-vintage-1252-erratum', pr};
const acceptedOriginal = validatePremergeManifest(fixture, {...context, readFile:readOriginal});
need(acceptedOriginal.metric_bindings_checked === fixture.metrics.length, 'Positive standard-validator fixture did not bind every numeric metric');
const mutatedFixture = structuredClone(fixture);
const mutatedDescriptor = mutatedFixture.outputs.find(output => output.path === tablePath);
mutatedDescriptor.bytes = alteredTable.length;
mutatedDescriptor.sha256 = sha256(alteredTable);
const readAltered = (name, vintage) => {
  if (vintage === 'candidate' && name === tablePath) return alteredTable;
  if (vintage === 'candidate' && name === receiptPath) return receiptRaw;
  return baseReader(name, vintage);
};
let rejected = false;
try {
  validatePremergeManifest(mutatedFixture, {...context, readFile:readAltered});
} catch (error) {
  rejected = /Rendered table differs from numeric ledger/.test(error.message);
  if (!rejected) throw error;
}
need(rejected, 'Standard validator accepted a mismatched rendered value after refreshed fixture hashes');

function safeExclusiveWrite(rootPath, relative, data) {
  need(!relative.startsWith('/') && !relative.includes('\\') && !relative.split('/').some(part => !part || part === '.' || part === '..'), 'Unsafe output path');
  const target = path.resolve(rootPath, relative), rootAbs = path.resolve(rootPath);
  need(target.startsWith(rootAbs + path.sep), 'Output escapes repository root');
  const parts = path.relative(rootAbs, target).split(path.sep); let cursor = rootAbs;
  for (const part of parts) {
    cursor = path.join(cursor, part);
    try { if (fs.lstatSync(cursor).isSymbolicLink()) throw Error('Symlink in output path'); }
    catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  fs.mkdirSync(path.dirname(target), {recursive:true});
  const fd = fs.openSync(target, 'wx', 0o644);
  try { fs.writeFileSync(fd, data); fs.fsyncSync(fd); } finally { fs.closeSync(fd); }
}
const fixtureRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-symlink-control-'));
const outside = fs.mkdtempSync(path.join(os.tmpdir(), 'worldatlas-symlink-target-'));
fs.symlinkSync(outside, path.join(fixtureRoot, 'escape'));
let symlinkEscapeRejected = false;
try { safeExclusiveWrite(fixtureRoot, 'escape/should-not-exist.json', receiptRaw); }
catch (error) { symlinkEscapeRejected = /Symlink in output path/.test(error.message); }
need(symlinkEscapeRejected && !fs.existsSync(path.join(outside, 'should-not-exist.json')), 'Symlink escape control did not reject before writing');
fs.rmSync(fixtureRoot, {recursive:true, force:true}); fs.rmSync(outside, {recursive:true, force:true});
body.symlink_escape_rejected = symlinkEscapeRejected;
body.harness_sha256 = sha256(scriptRaw);
const finalReceiptRaw = bytes(body);
safeExclusiveWrite(root, receiptPath, finalReceiptRaw);
console.log(JSON.stringify({outcome:'passed', metric_bindings_checked:acceptedOriginal.metric_bindings_checked, manipulated_table_rejected:rejected, symlink_escape_rejected:symlinkEscapeRejected, receipt_sha256:sha256(finalReceiptRaw)}));
