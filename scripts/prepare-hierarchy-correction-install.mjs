// Offline preparation only; publisher coordination and fresh live readback follow review.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {prepareInstall} from './install-macro-reference.mjs';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
 if(!['--candidate','--release','--stage'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --candidate CROSSWALK --release RELEASE-REPLAY --stage FRESH-EXTERNAL-DIRECTORY');
 options[args[i]]=path.resolve(args[i+1]);
}
if(Object.keys(options).length!==3)throw Error('All three arguments are required');
const stage=options['--stage'];
if(fs.existsSync(stage)||stage===root||stage.startsWith(root+path.sep))throw Error('Fresh external stage required');
const receipt=path.join(root,'data/engineering/hierarchy-crosswalk-20261003-a9c2/migration-receipt.json.gz');
const hash=file=>createHash('sha256').update(fs.readFileSync(file)).digest('hex');
if(hash(receipt)!==hash(path.join(options['--candidate'],'migration-receipt.json.gz')))throw Error('Candidate receipt differs from retained reviewed correction');
const prepared=await prepareInstall({data:path.join(root,'data'),geographyData:path.join(options['--candidate'],'geography'),releaseData:path.join(options['--release'],'geographic-release'),stage,receipts:[receipt],metadataMode:'reference-correction'});
console.log(JSON.stringify({offline:true,installed:false,published:false,validation_sha256:prepared.validation_sha256,counts:prepared.report.counts,changed_files:Object.keys(prepared.report.writes).length,report:path.join(stage,'report.json')}));
