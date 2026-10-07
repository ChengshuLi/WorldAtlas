import {createHash, randomUUID} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {stageGeographicRelease} from '../hosted/geographic-releases.js';
import {importBatch} from '../hosted/records.js';

const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const MiB = 1024 * 1024;
export const geographicAdmissionLimits = Object.freeze({rows: 250, requestBytes: MiB,
  fileBytes: 32 * MiB, phaseBytes: 256 * MiB, descriptors: 512});
const object = value => value && typeof value === 'object' && !Array.isArray(value);
const identity = value => typeof value === 'string' && value.trim() && value.length <= 2000;
const digest = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);

function rows(payload, field) {
  const values = payload[field] ?? [];
  if (!Array.isArray(values)) throw Error(`Release ${field} must be an array`);
  const ids = new Set();
  for (const row of values) {
    const id = field === 'memberships' ? row?.entity_id ?? row?.id : row?.id;
    if (!object(row) || !identity(id) || ids.has(id)) throw Error(`Invalid or duplicate ${field} identity`);
    ids.add(id);
    if (row.parent_id != null && !identity(row.parent_id)) throw Error('Invalid membership parent ID');
    if (row.source_id != null && !identity(row.source_id)) throw Error('Invalid release source ID');
    if (row.evidence != null && (!object(row.evidence) || JSON.stringify(row.evidence).length > 16384))
      throw Error('Invalid release evidence object');
    if (field === 'memberships' && ![0, 1].includes(row.active ?? 1)) throw Error('Invalid membership active flag');
  }
  return values;
}

/** Exercise the actual consumer's field rules without committing a database
 * operation. This proves field admission only: existing-state conflicts and
 * foreign keys still belong to the real transactional staging execution.
 * Unknown SQL fails closed; reaching the write boundary is deliberately refused.
 */
async function validateGeographicFields(payload, knownRelease, prerequisite = false) {
  if (prerequisite && Object.keys(payload).some(key => !['sources','entities','ingestion_id'].includes(key)))
    throw Error('Invalid geographic prerequisite collection');
  const columns = {
    atlas_geographic_releases: ['id','source_id','version','reference_date','status','hierarchy_sha256','footprints_sha256','membership_sha256','location_ids_sha256','changes_sha256','expected_counts','metadata','published_at'],
    atlas_geographic_memberships: ['release_id','entity_id','parent_id','reference_name','active','source_id','evidence'],
    atlas_geographic_changes: ['id','release_id','old_entity_id','new_entity_id','change_type','source_id','evidence'],
    atlas_ingestions: ['id','fingerprint','counts','created_at'],
  };
  const prerequisiteColumns = {
    atlas_sources: ['id','name','url','license','vintage','supported_from','supported_to','status','metadata'],
    atlas_entities: ['id','kind','name','parent_id','valid_from','valid_to','source_id','reference_owner','is_example','active','metadata'],
    atlas_ingestions: ['id','fingerprint','counts','created_at'],
  };
  const writes = prerequisite ? new Map(Object.entries(prerequisiteColumns).map(([table, fields]) => [
    table === 'atlas_ingestions' ? 'INSERT OR IGNORE INTO atlas_ingestions(id,fingerprint,counts,created_at) VALUES (?,?,?,?)' :
      `INSERT OR IGNORE INTO ${table} (${fields.join(',')}) VALUES (${fields.map(() => '?').join(',')})`,
    {table, fields},
  ])) : new Map(Object.entries(columns).map(([table, fields]) => [
    `INSERT INTO ${table}(${fields.join(',')}) VALUES(${fields.map(() => '?').join(',')})${table === 'atlas_ingestions' ? '' : ' ON CONFLICT DO NOTHING'}`,
    {table, fields},
  ]));
  const tokens = new Set(), marker = `Field admission refuses commit:${randomUUID()}`;
  let captured = false, normalizedRelease = knownRelease;
  const sink = {
    prepare(sql) {
      const write = writes.get(sql);
      const ingestionRead = sql === 'SELECT * FROM atlas_ingestions WHERE id=?';
      const releaseRead = !prerequisite && sql === 'SELECT * FROM atlas_geographic_releases WHERE id=?';
      if (!write && !ingestionRead && !releaseRead) throw Error('Unsupported field-admission SQL');
      return {bind(...values) {
        if (write) {
          if (values.length !== write.fields.length) throw Error('Invalid field-admission write shape');
          const token = Object.freeze({}); tokens.add(token);
          if (write.table === 'atlas_geographic_releases') {
            normalizedRelease = Object.fromEntries(write.fields.map((field, index) => [field,
              ['expected_counts','metadata'].includes(field) ? JSON.parse(values[index]) : values[index]]));
          }
          return token;
        }
        if (values.length !== 1 || typeof values[0] !== 'string') throw Error('Invalid field-admission read shape');
        return {async first() {
          if (ingestionRead) return null;
          return knownRelease?.id === values[0] ? {...knownRelease, status: 'staged'} : null;
        }};
      }};
    },
    async batch(statements) {
      if (!Array.isArray(statements) || !statements.length || statements.length > 251 ||
          statements.length !== tokens.size || new Set(statements).size !== statements.length ||
          statements.some(statement => !tokens.has(statement))) throw Error('Invalid field-admission write intent');
      captured = true;
      throw Error(marker);
    },
  };
  try {
    if (prerequisite) await importBatch(sink, payload);
    else await stageGeographicRelease(sink, payload);
  } catch (error) {
    // The handler wraps batch errors. A generic 409 is never sufficient proof.
    if (captured && error.status === 409 && error.message === (prerequisite ? `Import rejected: ${marker}` : marker)) return {release: normalizedRelease};
    throw error;
  }
  throw Error('Field admission unexpectedly returned without refusing a commit');
}

/** Preserve raw row objects/key order; the service remains the semantic authority.
 * Child identities bind the parent bytes, route, slice index and child content.
 * A bounded original request retains its original ingestion identity and bytes.
 */
export function splitGeographicReleaseBatch(bytes, part) {
  const payload = JSON.parse(bytes);
  if (!object(payload)) throw Error('Expected a release import object');
  const members = rows(payload, 'memberships'), changes = rows(payload, 'changes');
  const releaseId = payload.release?.id ?? payload.release_id;
  if (!identity(releaseId) || payload.release_id != null && payload.release_id !== releaseId)
    throw Error('Missing or conflicting release IDs');
  if (payload.release != null && !object(payload.release)) throw Error('Invalid release definition');
  if (payload.ingestion_id != null && !identity(payload.ingestion_id)) throw Error('Invalid ingestion ID');
  const count = members.length + changes.length + Number(Boolean(payload.release));
  if (count <= geographicAdmissionLimits.rows && bytes.length <= MiB && Buffer.byteLength(JSON.stringify(payload)) <= MiB)
    return [Buffer.from(bytes)];

  const parent = sha(bytes), envelope = Object.fromEntries(Object.entries(payload)
    .filter(([key]) => !['release', 'memberships', 'changes', 'ingestion_id'].includes(key)));
  const memberBytes = members.map(row => Buffer.byteLength(JSON.stringify(row)));
  const changeBytes = changes.map(row => Buffer.byteLength(JSON.stringify(row)));
  const chunks = [];
  let memberIndex = 0, changeIndex = 0;
  do {
    const index = chunks.length;
    const next = {...envelope, release_id: releaseId,
      ingestion_id: `geographic-split:v1:${sha(JSON.stringify([part.route, part.path, parent, index]))}`};
    if (index === 0 && payload.release) next.release = payload.release;
    if (Object.hasOwn(payload, 'memberships')) next.memberships = [];
    if (Object.hasOwn(payload, 'changes')) next.changes = [];
    let used = Number(Boolean(next.release));
    let wireBytes = Buffer.byteLength(JSON.stringify(next));
    if (wireBytes > MiB) throw Error('Release envelope exceeds request byte limit');
    for (const [field, input, sizes, getIndex, advance] of [
      ['memberships', members, memberBytes, () => memberIndex, () => memberIndex++],
      ['changes', changes, changeBytes, () => changeIndex, () => changeIndex++]]) {
      while (getIndex() < input.length && used < geographicAdmissionLimits.rows) {
        const addedBytes = sizes[getIndex()] + Number(next[field].length > 0);
        if (wireBytes + addedBytes > MiB) break;
        next[field].push(input[getIndex()]);
        wireBytes += addedBytes; advance(); used++;
      }
      // Do not jump over a membership that requires the following request.
      if (field === 'memberships' && memberIndex < members.length) break;
    }
    if (used === 0 && (memberIndex < members.length || changeIndex < changes.length))
      throw Error('Single release row exceeds request byte limit');
    const {ingestion_id: placeholder, ...content} = next;
    next.ingestion_id = `geographic-split:v1:${sha(JSON.stringify([part.route, part.path, parent, index, sha(JSON.stringify(content))]))}`;
    const body = Buffer.from(JSON.stringify(next));
    if (body.length !== wireBytes || body.length > MiB) throw Error('Release request byte accounting mismatch');
    chunks.push(body);
  } while (memberIndex < members.length || changeIndex < changes.length);
  return chunks;
}

/** Read/copy/authenticate every needed input before returning any executable plan.
 * Encoded, decoded and derived request bytes all count against the phase budget.
 * Returned bodies are captured bytes; execution must not reopen original paths.
 */
export async function admitGeographicReleaseBatches(parts, {readBatch, releases = [], phaseBytes = geographicAdmissionLimits.phaseBytes}) {
  if (!Array.isArray(parts) || parts.length > geographicAdmissionLimits.descriptors)
    throw Error('Required geographic inputs exceed complete phase descriptor budget');
  if (typeof readBatch !== 'function') throw Error('Geographic admission requires authenticated input reader');
  if (!Number.isSafeInteger(phaseBytes) || phaseBytes < 1 || phaseBytes > geographicAdmissionLimits.phaseBytes)
    throw Error('Invalid geographic admission phase budget');
  const plan = new Map(), names = new Set(), knownReleases = new Map(releases.map(release => [release.id, release]));
  let admittedBytes = 0;
  const admit = length => {
    admittedBytes += length;
    if (admittedBytes > phaseBytes) throw Error('Required geographic inputs/requests exceed complete phase budget');
  };
  for (const part of parts) {
    if (!part || !/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(part.path) || names.has(part.path) || !digest(part.sha256))
      throw Error('Invalid or duplicate geographic input descriptor');
    if (!['/api/records/import', '/api/geography/stage'].includes(part.route)) throw Error('Unsupported geographic input route');
    names.add(part.path);
    const encoded = Buffer.from(await readBatch(part));
    if (encoded.length > geographicAdmissionLimits.fileBytes) throw Error('Geographic input exceeds encoded file budget');
    admit(encoded.length);
    if (sha(encoded) !== part.sha256) throw Error('Prepared release hash mismatch: ' + part.path);
    if (part.encoding != null && (part.encoding !== 'gzip' || !digest(part.payload_sha256))) throw Error('Invalid geographic input encoding');
    const decoded = part.encoding === 'gzip' ? gunzipSync(encoded, {maxOutputLength: geographicAdmissionLimits.fileBytes}) : encoded;
    if (decoded.length > geographicAdmissionLimits.fileBytes) throw Error('Geographic input exceeds decoded file budget');
    admit(decoded.length);
    if (part.encoding === 'gzip' && sha(decoded) !== part.payload_sha256) throw Error('Prepared release payload hash mismatch: ' + part.path);
    const payload = JSON.parse(decoded);
    if (!object(payload)) throw Error('Expected geographic batch object');
    let requests;
    if (part.route === '/api/geography/stage') {
      requests = splitGeographicReleaseBatch(decoded, part);
      for (const body of requests) {
        const candidate = JSON.parse(body);
        const known = knownReleases.get(candidate.release_id);
        const validated = await validateGeographicFields(candidate, known);
        if (candidate.release) knownReleases.set(validated.release.id, validated.release);
      }
    }
    else {
      await validateGeographicFields(payload, null, true);
      if (decoded.length > MiB)
        throw Error('Geographic prerequisite exceeds service row/byte limits');
      requests = [Buffer.from(decoded)];
    }
    for (const body of requests) admit(body.length);
    plan.set(part.path, requests);
  }
  return {plan, admittedBytes};
}
