import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {ImmutableReader, processingAllowance} from '../../../../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../../../../scripts/delivery-handoff-advance.mjs';
import {valueBytes} from '../../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {committedPreparationFiles, requirePlainExecution} from '../../../../scripts/native-ownership/native-preparation-guards.mjs';

requirePlainExecution();
const [commit, evidencePath, patchPath, destination] = process.argv.slice(2);
const need = (ok, message) => { if (!ok) throw Error(message); };
need(process.argv.length === 6 && /^[a-f0-9]{40}$/.test(commit), 'Require exact input commit and three paths');
need(/^\.cache\/idn-native-qualification-[a-zA-Z0-9_-]+$/.test(destination), 'Require a fresh owned output vintage');
const root = fs.realpathSync(process.cwd());
const output = path.join(root, destination);
need(!fs.existsSync(output), 'Preserve prior output vintage');
fs.mkdirSync(output);
const observed = {availableBytes:process.availableMemory(),currentRssBytes:process.memoryUsage().rss,
  concurrentReservedBytes:Number(process.env.WORLDATLAS_CONCURRENT_RESERVED_BYTES ?? 0)};
const admission = processingAllowance(observed);
const head = execFileSync('git', ['-C', root, 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim();
const names = [
  'package.json',
  'scripts/check-effective-geographic-regression.mjs',
  'scripts/delivery-handoff-advance.mjs',
  'scripts/geography-prefetch.mjs',
  'scripts/native-ownership/native-preparation-guards.mjs',
  'src/native-grid.js',
  'src/ownership-codec.js',
  'coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs',
  'coordination/engineering/indonesia-adm2-current-cell-20261014/native-delivery-v1/qualify-native.mjs'
];
const code = committedPreparationFiles(root, head, names);
const reader = new ImmutableReader(root, commit, {allowance:admission,
  executionBytes:code.reduce((n,item)=>n+item.bytes,0),outputBytes:4*1024*1024});
const started = performance.now();
let qualified = false, failure = null, result = null;
const written = [];
function write(name, raw) {
  need(Buffer.isBuffer(raw) && raw.length <= 2*1024*1024, 'Bounded complete output exceeded');
  fs.writeFileSync(path.join(output, name), raw, {flag:'wx'});
  written.push({path:name,bytes:raw.length,sha256:createHash('sha256').update(raw).digest('hex')});
}
try {
  result = constructOriginalAuthority(reader, {
    source_evidence:{commit,path:evidencePath},native_patch:{commit,path:patchPath}
  });
  reader.checkMemory();
  need(result.component_ids.length > 0 && result.component_ids.length <= 8, 'Unexpected target workload');
  for (const [name, raw] of Object.entries(result.products)) write(name, raw);
  write('qualified-ledger-rows.json', valueBytes({rows:result.ledger_rows}));
  qualified = true;
} catch (error) {
  failure = String(error.stack ?? error);
}
const receipt = {version:1,kind:'actual-source-target-native-constructor-observation-v1',qualified,
  input_commit:commit,executed_commit:head,inputs:{source_evidence:evidencePath,native_patch:patchPath},
  admission_observations:observed,allowance:admission,execution_inventory:code,
  charged_phase_bytes:reader.used,input_inventory:[...reader.inventory.values()],
  elapsed_seconds:(performance.now()-started)/1000,observed_final_rss_bytes:process.memoryUsage().rss,
  observed_lifetime_maximum_rss_kib:process.resourceUsage().maxRSS,
  qualified_targets:result?.component_ids.length ?? 0,
  qualified_cells:result?.ledger_rows?.reduce((n,row)=>n+row.native_cells,0) ?? 0,
  outputs:written,failure,limits:[
    'Qualification uses the existing resource-aware ImmutableReader and unchanged source-target constructor.',
    'Native source coverage qualification alone does not establish current owner zero or accepted repair credit.',
    'Finite input workload is eight targets and the proposed native row blocks; no process-group cleanup or live aggregate RSS enforcement is claimed.',
    'Process resourceUsage maximum RSS is recorded in KiB; external Darwin time observations remain separate.'
  ],repaired_credit:0};
write('qualification-observation.json', valueBytes(receipt));
console.log(JSON.stringify({qualified,qualified_targets:receipt.qualified_targets,qualified_cells:receipt.qualified_cells,
  elapsed_seconds:receipt.elapsed_seconds,charged_phase_bytes:receipt.charged_phase_bytes,allowance:admission,failure}));
if (!qualified) process.exitCode = 1;
