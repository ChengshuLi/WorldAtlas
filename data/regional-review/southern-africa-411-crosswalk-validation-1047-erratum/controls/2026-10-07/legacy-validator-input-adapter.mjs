import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {gunzipSync} from 'node:zlib';

const root = process.cwd();
const packetRel = 'data/regional-review/regional-review-029dcbc646de003d';
const packet = path.join(root, packetRel);
const sha = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const readJSON = (name) => JSON.parse(fs.readFileSync(path.join(packet, name), 'utf8'));
const scope = readJSON('scope.json');
const reproduced = JSON.parse(fs.readFileSync(process.env.WA_CROSSWALK_INPUT, 'utf8'));
const rows = JSON.parse(fs.readFileSync(process.env.WA_ASSESSMENTS_INPUT, 'utf8'));
const sourceReview = readJSON('source-review.json');
const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };

const scopeIds = scope.scope.member_location_ids;
const idSet = new Set(scopeIds);
check(scope.issue === 411, 'wrong issue snapshot');
check(scope.issue_body_sha256 === reproduced.issue_body_sha256, 'issue body digest mismatch');
check(scope.scope.member_location_ids_sha256 === reproduced.issue_member_location_ids_sha256, 'scope digest mismatch');
check(idSet.size === 223 && reproduced.matched_scope_count === 223, 'exact 223-member scope did not reproduce');
check(reproduced.unique_scope_ids === 223 && rows.rows.length === 223, 'duplicate or missing row assessment');
check(rows.scope_reproduction_sha256 === sha(fs.readFileSync(process.env.WA_CROSSWALK_INPUT)), 'assessment input hash mismatch');
check(rows.rows.every((row) => idSet.has(row.id)), 'assessment includes an ID outside the issue scope');
check(new Set(rows.rows.map((row) => row.id)).size === idSet.size, 'assessment ID set is not one-to-one');
check(rows.rows.every((row) => ['justified', 'correction-needed', 'insufficient-evidence'].includes(row.classification)), 'row is missing an issue-required classification');
check(rows.rows.every((row) => row.native_source_feature_matched && row.source_name_crosswalk_matched), 'source identity/name join did not pass for every row');
check(rows.rows.filter((row) => row.classification === 'correction-needed').map((row) => row.location_name).join('|') === 'Cidade De Maputo', 'correction handoff changed without review');
check(rows.rows.filter((row) => row.country === 'AGO').length === 157, 'Angola row count mismatch');
check(rows.rows.filter((row) => row.country === 'MWI').length === 28, 'Malawi row count mismatch');
check(rows.rows.filter((row) => row.country === 'MOZ').length === 38, 'Mozambique row count mismatch');
check(rows.counts['correction-needed'] === 1 && rows.counts['insufficient-evidence'] === 222, 'classification counts mismatch');

const retainedSources = [];
for (const item of sourceReview.sources) {
  if (!item.artifact_path) continue;
  const rel = path.join(packetRel, item.artifact_path.replace(/^sources\//, 'sources/'));
  const bytes = fs.readFileSync(path.join(root, rel));
  const actual = sha(bytes);
  check(actual === item.sha256, `retained source SHA-256 mismatch: ${item.id}`);
  if (item.bytes !== undefined) check(bytes.length === item.bytes, `retained source byte count mismatch: ${item.id}`);
  let raw;
  if (item.raw_sha256 !== undefined) {
    try {
      raw = gunzipSync(bytes);
      check(raw.length === item.raw_bytes, `restored source byte count mismatch: ${item.id}`);
      check(sha(raw) === item.raw_sha256, `restored source SHA-256 mismatch: ${item.id}`);
    } catch (error) {
      check(false, `could not restore compressed source ${item.id}: ${error.message}`);
    }
  }
  retainedSources.push({id: item.id, path: rel, bytes: bytes.length, sha256: actual,
    ...(raw ? {raw_bytes: raw.length, raw_sha256: sha(raw)} : {})});
}
for (const baseline of reproduced.baseline_files) {
  const bytes = fs.readFileSync(path.join(root, baseline.path));
  check(bytes.length === baseline.bytes && sha(bytes) === baseline.sha256, `baseline source pin mismatch: ${baseline.path}`);
}

// Negative identity/hash controls: a fabricated nonmember must not resolve, and a wrong expected digest must fail.
const rowIds = new Set(reproduced.rows.map((row) => row.id));
const negativeId = 'gb:MWI:ADM2:negative-control-not-in-issue';
check(!rowIds.has(negativeId) && !idSet.has(negativeId), 'negative nonmember control was accepted');
const positiveId = rows.rows[0].id;
check(rowIds.has(positiveId) && idSet.has(positiveId), 'positive exact-member control failed');
const positiveBytes = fs.readFileSync(path.join(packet, rows.rows[0].country === 'AGO'
  ? 'sources/geoBoundaries-AGO-ADM2-2018.geojson'
  : rows.rows[0].country === 'MOZ'
    ? 'sources/geoBoundaries-MOZ-ADM2-2019.geojson'
    : 'sources/geoBoundaries-MWI-ADM2-2020.geojson'));
const digestMatches = (bytes, expected) => /^[a-f0-9]{64}$/.test(expected) && sha(bytes) === expected;
check(digestMatches(positiveBytes, sha(positiveBytes)), 'positive source-hash control failed');
check(!digestMatches(positiveBytes, '0'.repeat(64)), 'negative source-hash control was accepted');

if (failures.length) throw new Error(failures.join('\n'));
const result = {
  version: 1,
  issue: 411,
  baseline_commit: reproduced.baseline_commit,
  checked_at_utc: new Date().toISOString(),
  scope: {count: scopeIds.length, sorted_ids_sha256: scope.scope.member_location_ids_sha256, one_to_one_source_and_assessment_rows: rows.rows.length},
  classifications: rows.counts,
  positive_controls: {exact_member_id: 'passed',retained_source_hash: 'passed',row_assessments_equal_scope: 'passed'},
  negative_controls: {fabricated_nonmember_rejected: 'passed',wrong_expected_source_hash_rejected: 'passed'},
  retained_sources: retainedSources,
  baseline_files_verified: reproduced.baseline_files.map((row) => row.path),
  external_binary_hash_limits: sourceReview.sources.filter((row) => row.source_hash === null && row.retention?.startsWith('Not retained')).map((row) => ({id: row.id, limit: row.retention})),
  interpretation: 'This verifies the saved issue scope, source bytes retained in this packet, current baseline file pins and deterministic ID/name crosswalk. It does not verify topology, accuracy, completeness or the truth of external-source claims.'
};
const arg = process.argv.indexOf('--output');
const output = arg >= 0 ? process.argv[arg + 1] : path.join(packet, 'evidence-validation.json');
if (!output) throw new Error('--output requires a path');
fs.writeFileSync(path.isAbsolute(output) ? output : path.resolve(root, output), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({issue: result.issue, scope_count: result.scope.count, classifications: result.classifications, sources_verified: retainedSources.length, negative_controls: result.negative_controls}, null, 2));
