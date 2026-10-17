// Preserve the complete original administrative request and every old negative.
// Add reviewed whole-USA generation and complete canonical cohort custody only.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [repo, cohortPath, output] = process.argv.slice(2);
if (!repo || !cohortPath || !output) throw Error('Require repository, authenticated cohort inventory and fresh output path');
const {pinReader,jsonBytes} = await import(pathToFileURL(path.join(repo,'scripts/prepare-delivery-handoff.mjs')));
const reader=pinReader(repo), original=reader.pin('68e28d58293f7c951378886fa40cf680a2c3694f','coordination/engineering/canada-repair-delivery-20261017/config/admin-source-evidence-002.json');
const config=reader.json(original), before=jsonBytes(config), cohort=JSON.parse(fs.readFileSync(cohortPath));
for (const pin of [cohort.index,...cohort.parts]) reader.read(pin);
if (config.source_evidence.source_membership.cohort_inventory || config.territorial_exclusion_families) throw Error('Original inputs already have additions');
config.source_evidence.source_membership.cohort_inventory=cohort;
config.territorial_exclusion_families=['gb:USA:ADM1'];
const body=jsonBytes(config);
const check=structuredClone(config); delete check.source_evidence.source_membership.cohort_inventory; delete check.territorial_exclusion_families;
if (!before.equals(jsonBytes(check))) throw Error('Original configuration changed');
fs.writeFileSync(output,body,{flag:'wx'});
console.log(JSON.stringify({original,output,bytes:body.length,changes:['source_evidence.source_membership.cohort_inventory','territorial_exclusion_families'],limits:['The complete original 293965-cell request and every prior exclusion remain unchanged.','This prepares source-evidence inputs; it does not qualify native ownership.']}));
