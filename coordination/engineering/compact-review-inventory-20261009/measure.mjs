import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {reviewInventoryCommitment} from '../../../scripts/premerge-evidence.mjs';

const root=path.dirname(fileURLToPath(import.meta.url));
const name=process.argv[2];
if(!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name??''))throw Error('Use a fresh simple run name');
const destination=path.join(root,name);
for(let p=root;;p=path.dirname(p)){const s=fs.lstatSync(p);if(!s.isDirectory()||s.isSymbolicLink())throw Error('Nonordinary destination ancestor');if(p===path.dirname(p))break;}
try{fs.lstatSync(destination);throw Error('Output already exists');}catch(error){if(error.code!=='ENOENT')throw error;}
const pinsPath=path.join(root,'original-inputs/input-pins.json');
if(fs.lstatSync(pinsPath).size>1048576)throw Error('Metadata over bound');
const pins=JSON.parse(fs.readFileSync(pinsPath));
if(pins.version!==1||pins.files.length!==3)throw Error('Incomplete inputs');
let complete=fs.statSync(process.execPath).size+1048576+fs.statSync(pinsPath).size;
for(const p of pins.files){if(!/^[a-z0-9-]+\.json$/.test(p.path)||!Number.isSafeInteger(p.bytes)||p.bytes<=0||p.bytes>33554432)throw Error('Invalid input descriptor');const s=fs.lstatSync(path.join(root,'original-inputs',p.path));if(!s.isFile()||s.isSymbolicLink()||s.size!==p.bytes)throw Error('Input stat differs');complete+=p.bytes;}
// Metadata measurement only; reserve the complete small executing module closure.
const closureBytes=1024*1024;complete+=closureBytes;
if(complete>268435456)throw Error('Complete metadata phase over bound');
const values=new Map();const sha=b=>createHash('sha256').update(b).digest('hex');
for(const p of pins.files){const b=fs.readFileSync(path.join(root,'original-inputs',p.path));if(b.length!==p.bytes||sha(b)!==p.sha256)throw Error('Whole input differs');values.set(p.path,JSON.parse(b));}
const pr=values.get('pr1593.json'),manifest=values.get('manifest1593.json'),files=values.get('files1593-pages.json').flat();
if(pr.head.sha!==pins.original_manifest.commit||files.length!==pr.changed_files||new Set(files.map(f=>f.filename)).size!==files.length)throw Error('Incomplete original PR inventory');
const inspected_files=[...new Set(files.flatMap(f=>[f.filename,f.previous_filename].filter(Boolean)))].sort();
const evidence_hashes=[...new Set([...manifest.baseline.files,...manifest.outputs,...manifest.sources.flatMap(s=>s.files??[])].map(f=>f.sha256))].sort();
const commitment=reviewInventoryCommitment({files,manifest});
const report={version:1,kind:'actual-complete-review-inventory-measurement',original_head:pr.head.sha,original_base:pr.base.sha,original_manifest:pins.original_manifest,changed_files:files.length,unique_evidence_hashes:evidence_hashes.length,literal_inventory_characters:JSON.stringify({inspected_files,evidence_hashes}).length,compact_inventory_characters:JSON.stringify({inventory_commitment:commitment}).length,github_comment_body_limit:65536,inventory_commitment:commitment,complete_prospective_bytes:complete,limits:['This counts the complete actual immutable review inputs; it does not assert their substantive geographic approval.','Subsequent actual PR1593 normal queue admission requires its independent completed review and required checks; not executed by this measurement.']};
const body=Buffer.from(JSON.stringify(report,null,2)+'\n');if(body.length>1048576)throw Error('Output reserve exceeded');
fs.mkdirSync(destination);fs.writeFileSync(path.join(destination,'measurement.json'),body,{flag:'wx',mode:0o644});console.log(JSON.stringify({destination,bytes:body.length,sha256:sha(body)}));
