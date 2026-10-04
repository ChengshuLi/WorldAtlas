// Apply a reviewed offline stage to this isolated checkout; never publish live assets.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {applyInstall} from './install-macro-reference.mjs';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
 if(!['--stage','--expected-validation','--receipt'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --stage STAGE --expected-validation EXACT-SHA --receipt NEW-FILE');
 options[args[i]]=args[i+1];
}
if(Object.keys(options).length!==3)throw Error('All three arguments required');
const stage=path.resolve(options['--stage']),receipt=path.resolve(options['--receipt']);
if(stage===root||stage.startsWith(root+path.sep)||fs.existsSync(receipt))throw Error('External stage and new receipt required');
const {validation_sha256,...report}=JSON.parse(fs.readFileSync(path.join(stage,'report.json')));
const sha=raw=>createHash('sha256').update(raw).digest('hex');
if(sha(Buffer.from(JSON.stringify(report)+'\n'))!==validation_sha256||validation_sha256!==options['--expected-validation'])throw Error('Stage report does not match exact reviewed validation');
if(report.reference_only!==true||report.ownership_recompiled!==false||report.historical_records_changed!==false||report.semantic_complete!==false||report.macro_compatibility?.published!==false)throw Error('Wrong installation preservation/approval scope');
const result=applyInstall({data:path.join(root,'data'),stage,report,validation_sha256},{expectedValidation:validation_sha256});
for(const [name,pin] of Object.entries(report.writes))if(sha(fs.readFileSync(path.join(root,'data',name)))!==pin)throw Error('Installed asset differs from reviewed stage');
const artifact={version:1,...result,local_checkout_only:true,live_publication:false,counts:report.counts,written_files:Object.keys(report.writes).length,preserved_files:Object.keys(report.preserved).length,ownership_buffers:report.immutable_grid_parts.length,historical_claims_transferred:false,regional_interiors_approved:false};
fs.writeFileSync(receipt,encodeEvidenceJSON(artifact),{flag:'wx'});
console.log(JSON.stringify(artifact));
