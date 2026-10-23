// Optional accepted-checkpoint transport for the existing delivery finalizer.
// This does not mint scientific authority: acquisition retains the ordinary
// accepted PR, tested tree, original job and complete artifact checks.
import fs from 'node:fs';
import path from 'node:path';
import {createHash, randomUUID} from 'node:crypto';
import {locate} from './delivery-handoff-advance.mjs';
import {ACCEPTED_CHECKPOINT_LOCATOR, acquireAcceptedCheckpoint, readAcceptedCheckpoint,
  releaseAcceptedCheckpoint, validateAcceptedCheckpointLocator} from './accepted-selected-checkpoint.mjs';

const chosenOperands = new WeakMap();
const need = (ok, message) => { if (!ok) throw Error(message); };
const canonical = value => Array.isArray(value) ? value.map(canonical) : value && typeof value === 'object'
  ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value;
const same = (a, b) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));

function operand(config, reader) {
  const pin = locate(reader, config.accepted_checkpoint);
  const bytes = reader.read(pin), locator = validateAcceptedCheckpointLocator(JSON.parse(bytes));
  need(locator.retained_artifact, 'Finalization checkpoint requires its committed retained artifact');
  return {pin, bytes, locator};
}

export async function acquireFinalizationCheckpoint(config, reader, options = {}) {
  if (!Object.hasOwn(config, 'accepted_checkpoint')) return undefined;
  const {pin, bytes, locator} = operand(config, reader);
  const archive = locate(reader, {commit: pin.commit, path: locator.retained_artifact.path});
  const result = await acquireAcceptedCheckpoint({...options, repo: options.repo ?? 'ChengshuLi/WorldAtlas',
    locator: locator.acceptance, retainedArchive: () => reader.read(archive)});
  need(result.available, result.reason);
  chosenOperands.set(result.handle, {commit: pin.commit, path: pin.path, bytes: Buffer.from(bytes)});
  try { finalizationCheckpointBytes(config, reader, result.handle); }
  catch (error) { releaseAcceptedCheckpoint(result.handle); throw error; }
  return result.handle;
}

export function finalizationCheckpointBytes(config, reader, handle) {
  if (!Object.hasOwn(config, 'accepted_checkpoint')) {
    need(handle === undefined, 'Checkpoint capability requires an explicit finalization operand');
    return undefined;
  }
  const {pin, bytes, locator} = operand(config, reader), proof = readAcceptedCheckpoint(handle);
  const chosen = chosenOperands.get(handle);
  need(chosen && chosen.commit === pin.commit && chosen.path === pin.path && chosen.bytes.equals(bytes),
    'Checkpoint operand differs from the authenticated acquisition');
  need(same(locator.acceptance, {pr_number: proof.receipt.pr_number,
    request_id: proof.receipt.request_id, head: proof.source.head}), 'Chosen checkpoint differs from acquired acceptance');
  const facts = proof.products['derived-facts.json'];
  const selection = reader.json(Object.hasOwn(config.selector, 'sha256') ? config.selector : locate(reader, config.selector));
  need(facts?.candidate_commit === proof.source.candidate_commit && same(facts.candidate_selection, selection),
    'Checkpoint does not supply the prior selected baseline');
  return Buffer.from(bytes);
}

// One canonical writer for the existing finalizer's derived destinations.
// All files are preflighted before staging; interrupted adoption can resume only
// with the same immutable outputs and exact preimage/postimage bytes.
const identity = raw => raw === null ? undefined : ({bytes: raw.length, sha256: createHash('sha256').update(raw).digest('hex')});
export function admitCanonicalOutputs(root, bindings, resume = false) {
  const rows = bindings.map(({path: name, bytes, expected, previous, allowMissing = false, retained = false}) => {
    if (!retained && expected === undefined) expected = identity(bytes);
    need(typeof name === 'string' && !path.isAbsolute(name)
      && name.split('/').every(part => part && part !== '.' && part !== '..'), 'Safe canonical output path required');
    if (retained) need(retained === true && bytes === undefined && expected
      && Number.isSafeInteger(expected.bytes) && expected.bytes > 0 && /^[a-f0-9]{64}$/.test(expected.sha256)
      && same(expected, previous), 'Complete unchanged canonical retention required');
    else need((Buffer.isBuffer(bytes) || bytes === null && previous && Number.isSafeInteger(previous.bytes) && /^[a-f0-9]{64}$/.test(previous.sha256)) && same(identity(bytes), expected), 'Canonical output changed after finalization');
    return {name, bytes, expected: expected && {...expected}, previous: previous && {...previous}, allowMissing, retained};
  });
  need(new Set(rows.map(row => row.name)).size === rows.length, 'Duplicate canonical output path');
  need(rows.every(row => rows.every(other => row === other || !row.name.startsWith(other.name + '/'))),
    'Overlapping canonical output paths');
  const inspect = row => {
    let directory = root;
    for (const part of row.name.split('/').slice(0, -1)) {
      directory = path.join(directory, part);
      const stat = fs.lstatSync(directory, {throwIfNoEntry: false});
      need(!stat || stat.isDirectory() && fs.realpathSync(directory) === directory,
        'Nonordinary canonical output directory');
    }
    const filename = path.join(root, row.name), stat = fs.lstatSync(filename, {throwIfNoEntry: false});
    need(!stat || stat.isFile() && !(stat.mode & 0o111) && fs.realpathSync(filename) === filename,
      'Nonordinary canonical output file');
    const current = stat ? identity(fs.readFileSync(filename)) : undefined;
    need(current === undefined && (row.previous === undefined || row.allowMissing || resume && row.bytes === null)
      || current !== undefined && (row.previous && same(current, row.previous) || resume && same(current, row.expected)),
    'Canonical output changed outside this finalization: ' + row.name);
    return current;
  };
  for (const row of rows) inspect(row);
  return () => {
    for (const row of rows) {
      // Retained inputs are already bound to the accepted Git tree by the
      // finalizer. Recheck any materialized bytes, but leave sparse holes alone.
      if (row.retained) { inspect(row); continue; }
      need(same(identity(row.bytes), row.expected), 'Canonical output changed after finalization');
      if (same(inspect(row), row.expected)) continue;
      const filename = path.join(root, row.name), directory = path.dirname(filename);
      if (row.bytes === null) { inspect(row); fs.unlinkSync(filename); continue; }
      fs.mkdirSync(directory, {recursive: true});
      const temporary = path.join(directory, `.finalize-${randomUUID()}.tmp`);
      try {
        inspect(row);
        fs.writeFileSync(temporary, row.bytes, {flag: 'wx', mode: 0o644});
        inspect(row);
        fs.renameSync(temporary, filename);
      } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
    }
  };
}

// Retained library checkpoint operation uses the same ordinary writer.
export function admitCanonicalCheckpoint(root, reader, selector, bytes, resume = false) {
  if (bytes === undefined) return () => {};
  need(Buffer.isBuffer(bytes), 'Canonical checkpoint bytes required');
  bytes = Buffer.from(bytes);
  validateAcceptedCheckpointLocator(JSON.parse(bytes));
  const previous = reader.hasPath(selector.commit, ACCEPTED_CHECKPOINT_LOCATOR)
    ? identity(reader.read(reader.pin(selector.commit, ACCEPTED_CHECKPOINT_LOCATOR))) : undefined;
  return admitCanonicalOutputs(root, [{path: ACCEPTED_CHECKPOINT_LOCATOR, bytes, previous}], resume);
}
