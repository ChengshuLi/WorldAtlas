import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';

// Riau cohort adaptation of the reviewed local Vietnam metadata adapter.
// Uses existing production authority/ledger helpers; not a new scientific method.
// The actual accepted base is an explicit input, never a projected merge SHA.
const [base, output] = process.argv.slice(2);
const root = process.cwd();
const prefix = 'coordination/engineering/indonesia-riau-current-cells-20261014/';
const qualified = 'aab952621aa5198bef76b7c5bc81c38c5b871bd5';
const sha = raw => createHash('sha256').update(raw).digest('hex');
const need = (ok, message) => { if (!ok) throw Error(message); };
const git = (...args) => execFileSync('git', ['-c', 'protocol.allow=never', ...args], {encoding: 'utf8'}).trim();
need(/^[a-f0-9]{40}$/.test(base ?? '') && output && path.isAbsolute(output), 'Exact accepted base and absolute owned output required');
need(process.env.GIT_NO_LAZY_FETCH === '1' && process.env.NODE_OPTIONS === undefined, 'No lazy fetch or preloaded code');
git('merge-base', '--is-ancestor', base, 'HEAD');
git('merge-base', '--is-ancestor', qualified, 'HEAD');
const head = git('rev-parse', 'HEAD');
need(!fs.existsSync(output) && fs.realpathSync(path.dirname(output)) === path.dirname(output), 'Fresh ordinary output required');
const codeNames = ['scripts/check-effective-geographic-regression.mjs', 'scripts/delivery-handoff-advance.mjs', 'scripts/geography-prefetch.mjs', 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs', 'src/native-grid.js', 'src/ownership-codec.js'];
const projectCode = codeNames.map(name => {
    const raw = fs.readFileSync(path.join(root, name));
    const committed = execFileSync('git', ['-c', 'protocol.allow=never', 'show', head + ':' + name]);
    need(raw.equals(committed), 'Working code differs: ' + name);
    need(git('rev-parse', head + ':' + name) === git('rev-parse', base + ':' + name), 'Code differs from actual accepted base: ' + name);
    return {path: name, commit: head, bytes: raw.length, sha256: sha(raw), git_blob_oid: git('rev-parse', head + ':' + name)};
});
const {ImmutableReader, processingAllowance} = await import(pathToFileURL(path.join(root, 'scripts/check-effective-geographic-regression.mjs')));
const {constructAuthorityRegistry} = await import(pathToFileURL(path.join(root, 'scripts/delivery-handoff-advance.mjs')));
const {valueBytes, valueSha, normaliseRetainedRepairLedger, compareVersionedRepairLedgers} = await import(pathToFileURL(path.join(root, 'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs')));
const runtimeBytes = fs.statSync(process.execPath).size;
const executionBytes = projectCode.reduce((n, p) => n + p.bytes, 0) + fs.statSync(process.argv[1]).size;
const observation = {availableBytes: process.availableMemory(), currentRssBytes: process.memoryUsage().rss, concurrentReservedBytes: Number(process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES ?? 0)};
const allowance = processingAllowance(observation);
const reader = new ImmutableReader(root, head, {allowance, executionBytes});
const readPinnedJson = pin => {
    const actual = reader.descriptor(pin.path, pin.commit);
    need(actual.mode === pin.mode && actual.git_blob_oid === pin.git_blob_oid && actual.bytes === pin.bytes, 'Immutable role identity differs: ' + pin.path);
    return reader.json(pin.path, {version: pin.commit, expected: pin.sha256});
};
fs.mkdirSync(output);
fs.writeFileSync(path.join(output, 'admission.json'), JSON.stringify({head, accepted_base: base, runtime_bytes: runtimeBytes, execution_bytes: executionBytes, project_code: projectCode, ...observation, allowance, limits: ['Existing cooperative phase/current-process RSS checks; no live process-tree or hard-wall enforcement.']}, null, 2) + '\n', {flag: 'wx'});
const started = performance.now();
try {
    const selector = reader.json('data/ownership-selection.json', {version: base});
    const sidecarDescriptor = reader.descriptor(selector.additive_release.path, base);
    need(sidecarDescriptor.bytes === selector.additive_release.bytes, 'Accepted sidecar size differs');
    const oldSidecar = reader.json(selector.additive_release.path, {version: base, expected: selector.additive_release.sha256});
    const priorPins = [oldSidecar.authority_registry, oldSidecar.logical_asset_map.ledger, oldSidecar.logical_asset_map.patch, oldSidecar.runtime_envelope];
    const newNames = ['authority/receipt.json', 'authority/qualified-ledger-rows.json', 'candidate-native-patch.json', 'authority/original-rule-preimage.json', 'authority/authority-binding.json'];
    const newDescriptors = newNames.map(name => reader.descriptor(prefix + name, qualified));
    const selectorBytes = reader.descriptor('data/ownership-selection.json', base).bytes + sidecarDescriptor.bytes;
    const inputBytes = selectorBytes + [...priorPins, ...newDescriptors].reduce((n, p) => n + p.bytes, 0);
    // Sixfold parsing plus sixfold composition carry, reserved before the large
    // prior products are opened. Encoded inputs and output buffers charge too.
    const compositionReserve = 12 * inputBytes;
    reader.metadataBytes += compositionReserve;
    reader.phase();
    const oldRegistry = readPinnedJson(oldSidecar.authority_registry);
    const oldLedger = readPinnedJson(oldSidecar.logical_asset_map.ledger);
    const oldPatch = readPinnedJson(oldSidecar.logical_asset_map.patch);
    const oldEnvelope = readPinnedJson(oldSidecar.runtime_envelope);
    const constructed = reader.json(prefix + 'authority/receipt.json', {version: qualified});
    constructed.ledger_rows = reader.json(prefix + 'authority/qualified-ledger-rows.json', {version: qualified});
    need(constructed.qualified_cells === 10775 && constructed.component_ids.length === 2, 'Exact successful Riau constructor result required');
    const candidate = reader.json(prefix + 'candidate-native-patch.json', {version: qualified});
    // The complete prospective carry survives the unchanged authority helper.
    const singleton = JSON.parse(constructAuthorityRegistry(reader, [{rule_preimage: {commit: qualified, path: prefix + 'authority/original-rule-preimage.json'}, source_authority: {commit: qualified, path: prefix + 'authority/authority-binding.json'}}])['authority-registry.json']);
    need(singleton.entries.length === 1 && constructed.ledger_rows.length === 2, 'Exact qualified authority/cohort required');
    const entry = singleton.entries[0];
    need(entry.rule_sha256 === constructed.rule_sha256 && !oldRegistry.entries.some(e => e.authority_sha256 === entry.authority_sha256), 'New authority differs or already exists');
    const registry = {...oldRegistry, entries: [...oldRegistry.entries, entry].sort((a, b) => a.authority_sha256.localeCompare(b.authority_sha256))};
    const rows = [...oldLedger.rows, ...constructed.ledger_rows.map(row => ({...row, authority_sha256: entry.authority_sha256, rule_sha256: entry.rule_sha256}))].sort((a, b) => a.component_id.localeCompare(b.component_id));
    const ledger = {...oldLedger, authority_registry_sha256: valueSha(registry), rows, scope_ids: rows.map(row => row.component_id)};
    const conservation = compareVersionedRepairLedgers(oldLedger, ledger, {beforeRegistry: oldRegistry, afterRegistry: registry});
    const normalized = normaliseRetainedRepairLedger(ledger, registry);
    const ledgerBytes = valueBytes(ledger);
    const effective = {...oldEnvelope.effective_reference, id: 'geography:indonesia-riau-current-cell-20261014', footprints_sha256: valueSha({domain: 'worldatlas-effective-native-footprints:v2', base_reference: oldEnvelope.base_reference, authority_registry_sha256: valueSha(registry), ledger_sha256: sha(ledgerBytes), components: [...normalized.rows.values()]})};
    const byRow = new Map();
    for (const row of [...oldPatch.rows, ...candidate.rows]) {
        const runs = byRow.get(row.y) ?? [];
        runs.push(...row.runs.map(run => [...run]));
        byRow.set(row.y, runs);
    }
    const patchRows = [...byRow].sort((a, b) => a[0] - b[0]).map(([y, runs]) => {
        runs.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
        const merged = [];
        for (const run of runs) {
            const last = merged.at(-1);
            need(!last || run[0] >= last[1], 'Proposed cells overlap the accepted cumulative patch');
            if (last && last[1] === run[0] && last[2] === run[2]) last[1] = run[1];
            else merged.push(run);
        }
        return {y, runs: merged};
    });
    const cells = list => list.reduce((n, row) => n + row.runs.reduce((m, run) => m + run[1] - run[0], 0), 0);
    const priorCells = cells(oldPatch.rows);
    need(cells(candidate.rows) === 10775 && cells(patchRows) === priorCells + 10775, 'Exact 10775-cell disjoint append required');
    const patch = {...oldPatch, authority_registry_sha256: valueSha(registry), ledger_sha256: sha(ledgerBytes), effective_reference: effective, rows: patchRows};
    const patchBytes = valueBytes(patch);
    const envelope = {...oldEnvelope, effective_reference: effective, ledger: {...oldEnvelope.ledger, path: 'additive-repairs/native-supplement-ledger.json', bytes: ledgerBytes.length, sha256: sha(ledgerBytes)}, patch: {...oldEnvelope.patch, path: 'additive-repairs/native-supplement-patch.json', bytes: patchBytes.length, sha256: sha(patchBytes)}};
    const products = {'authority-registry.json': valueBytes(registry), 'native-supplement-ledger.json': ledgerBytes, 'native-supplement-patch.json': patchBytes, 'runtime-envelope.json': valueBytes(envelope)};
    reader.checkMemory();
    need(Object.values(products).reduce((n, raw) => n + raw.length, 0) + 65536 < reader.outputBytes, 'Complete products exceed reserved output');
    for (const [name, raw] of Object.entries(products)) fs.writeFileSync(path.join(output, name), raw, {flag: 'wx'});
    const receipt = {status: 'composed-qualified-authority-and-cumulative-metadata', execution_commit: head, accepted_base: base, qualification_commit: qualified, elapsed_seconds: (performance.now() - started) / 1000, peak_rss_bytes: process.resourceUsage().maxRSS * 1024, phase_charged_bytes: reader.used, allowance, composition_reserved_bytes: compositionReserve, composition_input_bytes: inputBytes, prior_cells: priorCells, proposed_added_cells: 10775, cumulative_cells: priorCells + 10775, prior_authorities: oldRegistry.entries.length, cumulative_authorities: registry.entries.length, prior_ledger_rows: oldLedger.rows.length, cumulative_ledger_rows: rows.length, conservation, inherited_sidecar: oldSidecar, files: Object.entries(products).map(([name, raw]) => ({path: name, bytes: raw.length, sha256: sha(raw)})), input_inventory: [...reader.inventory.values()], limits: ['Registry qualification and cumulative metadata composition only; actual current-owner-zero and selected consumption remain pending.', 'No original source/GSHHG producer replay; no aggregate process-tree or hard-wall enforcement.', 'Physical003 observed885030912B exceeded870998016B allowance by14032896B; this call does not relabel that producer as compliant. All3279flagged repair and4760source-relative candidates remain excluded.']};
    fs.writeFileSync(path.join(output, 'composition-receipt.json'), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
    console.log(JSON.stringify({status: receipt.status, prior_cells: priorCells, proposed_added_cells: 10775, cumulative_cells: receipt.cumulative_cells, elapsed_seconds: receipt.elapsed_seconds, phase_charged_bytes: receipt.phase_charged_bytes}));
} catch (error) {
    fs.writeFileSync(path.join(output, 'failure.json'), JSON.stringify({error: error.message, elapsed_seconds: (performance.now() - started) / 1000, phase_charged_bytes: reader.used}, null, 2) + '\n', {flag: 'wx'});
    throw error;
}
