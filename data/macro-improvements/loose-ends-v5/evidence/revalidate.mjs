// Revalidate existing factual evidence without editing its source records.
import fs from 'node:fs';import path from 'node:path';
import {fileURLToPath} from 'node:url';import {createHash} from 'node:crypto';
import {gzipSync} from 'node:zlib';
import {revalidatePreparedEvidence} from '../../../../scripts/revalidate-prepared-evidence.mjs';
import {prepareEvidenceBundle} from '../../../../scripts/prepare-evidence-bundle.mjs';
const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'../../../..');
const [beforeInput,receiptInput]=process.argv.slice(2);
if(!beforeInput||!receiptInput)throw Error('Use BEFORE_GEOGRAPHY_DIRECTORY AGGREGATE_RECEIPT');
if(process.cwd()!==root)throw Error('Run from the repository root for durable relative archive references');
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const before=path.resolve(beforeInput),data=path.join(root,'data');
const packed=gzipSync(fs.readFileSync(receiptInput),{mtime:0});
const receipt=path.join(here,'aggregate-source-receipt.json.gz');
if(fs.existsSync(receipt)&&!fs.readFileSync(receipt).equals(packed))throw Error('Pinned migration receipt changed');
if(!fs.existsSync(receipt))fs.writeFileSync(receipt,packed);
const products=[{id:'dated-reference-names',kind:'names'},{id:'demographic-evidence',kind:'records'}]
 .map(product=>({...product,directory:path.join(data,product.id)}));
const validated=revalidatePreparedEvidence({before,after:data,products,
 migrationReceipts:[path.relative(root,receipt)],archiveDirectory:here});
const bundle=prepareEvidenceBundle({data,output:path.join(data,'prepared-evidence')});
const result={version:1,verified:true,published:false,products:validated,
 prepared_bundle:{records:bundle.records,names:bundle.names,parts:bundle.parts.length,
 pending_products:bundle.pending_products,footprints_sha256:bundle.footprints_sha256,
 hierarchy_sha256:bundle.hierarchy_sha256,location_index_sha256:bundle.location_index_sha256,
 index_sha256:sha(fs.readFileSync(path.join(data,'prepared-evidence/index.json')))},
 source_record_bytes_preserved:true,historical_membership_assigned:false,
 historical_claims_transferred:false};
fs.writeFileSync(path.join(here,'result.json'),JSON.stringify(result));
const files=Object.fromEntries(fs.readdirSync(here).filter(name=>name!=='index.json').sort()
 .map(name=>[name,{sha256:sha(fs.readFileSync(path.join(here,name)))}]));
fs.writeFileSync(path.join(here,'index.json'),JSON.stringify({version:1,issue:540,files,published:false}));
console.log(JSON.stringify(result));
