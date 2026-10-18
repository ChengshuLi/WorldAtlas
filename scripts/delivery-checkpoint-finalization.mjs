// Optional accepted-checkpoint transport for the existing delivery finalizer.
// This does not mint scientific authority: acquisition retains the ordinary
// accepted PR, tested tree, original job and complete artifact checks.
import fs from 'node:fs';
import path from 'node:path';
import {randomUUID} from 'node:crypto';
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

// Preflight before publishing the batch. Canonical adoption is automatic, not
// a second manual copy instruction. A failed adoption is resumable only with
// identical completed products and either the original or chosen locator.
export function admitCanonicalCheckpoint(root, reader, selector, bytes, resume = false) {
  if (bytes === undefined) return () => {};
  need(Buffer.isBuffer(bytes), 'Canonical checkpoint bytes required');
  bytes = Buffer.from(bytes);
  validateAcceptedCheckpointLocator(JSON.parse(bytes));
  const directory = path.join(root, 'data'), filename = path.join(root, ACCEPTED_CHECKPOINT_LOCATOR);
  const previous = reader.hasPath(selector.commit, ACCEPTED_CHECKPOINT_LOCATOR)
    ? reader.read(reader.pin(selector.commit, ACCEPTED_CHECKPOINT_LOCATOR)) : undefined;
  const inspect = () => {
    need(fs.lstatSync(directory).isDirectory() && fs.realpathSync(directory) === directory,
      'Nonordinary canonical checkpoint directory');
    const stat = fs.lstatSync(filename, {throwIfNoEntry: false});
    need(!stat || stat.isFile() && fs.realpathSync(filename) === filename, 'Nonordinary canonical checkpoint file');
    const current = stat ? fs.readFileSync(filename) : undefined;
    need(current === undefined && previous === undefined || current !== undefined &&
      (previous !== undefined && current.equals(previous) || resume && current.equals(bytes)),
    'Canonical checkpoint changed outside this finalization');
    return current;
  };
  inspect();
  return () => {
    if (inspect()?.equals(bytes)) return;
    const temporary = path.join(directory, `.selected-checkpoint-${randomUUID()}.tmp`);
    try {
      fs.writeFileSync(temporary, bytes, {flag: 'wx', mode: 0o644});
      inspect();
      fs.renameSync(temporary, filename);
    } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
  };
}
