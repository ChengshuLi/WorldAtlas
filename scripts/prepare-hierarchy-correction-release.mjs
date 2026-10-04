// Replays retained identity proofs and appends the bounded reference correction.
// All output is offline and external; this does not stage or publish a release.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {readGeographicReleaseManifest} from './read-geographic-release-manifest.mjs';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const hash=file=>sha(fs.readFileSync(file));
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const save=(file,value)=>fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n');
const args=process.argv.slice(2),options={};
for(let i=0;i<args.length;i+=2){
 if(!['--candidate','--output'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --candidate CROSSWALK-DIRECTORY --output FRESH-EXTERNAL-DIRECTORY');
 options[args[i]]=path.resolve(args[i+1]);
}
if(Object.keys(options).length!==2)throw Error('Both arguments are required');
const candidate=options['--candidate'],output=options['--output'];
if(output===root||output.startsWith(root+path.sep)||fs.existsSync(output))throw Error('Fresh external output directory required');
const receiptFile=path.join(candidate,'migration-receipt.json.gz'),receipt=read(receiptFile);
const current=readGeographicReleaseManifest(path.join(root,'data/geographic-releases')),before=current.releases.at(-1);
if(receipt.before_sha256!==before.hierarchy_sha256||receipt.footprints_sha256_before!==before.footprints_sha256)throw Error('Candidate differs from retained latest release');
if(receipt.reference_only!==true||receipt.historical_claims_transferred!==false||receipt.summary.geometry_changes!==0)throw Error('Reference-only correction required');
fs.mkdirSync(output);
const inputs=[];
function extract(indexFile,destination){
 const index=read(indexFile),archive=path.join(path.dirname(indexFile),typeof index.archive==='string'?index.archive:index.archive.path);
 const expected=index.archive_sha256??index.archive.sha256;
 if(hash(archive)!==expected)throw Error('Retained identity archive changed');
 fs.mkdirSync(destination);
 execFileSync('python3',['-c',`
import pathlib,tarfile,sys
root=pathlib.Path(sys.argv[2]).resolve()
with tarfile.open(sys.argv[1]) as archive:
 names=set()
 for entry in archive.getmembers():
  target=(root/entry.name).resolve()
  if not target.is_relative_to(root) or not entry.isfile() or entry.name in names: raise ValueError('Unsafe archive entry')
  names.add(entry.name)
 archive.extractall(root,filter='data')
`,archive,destination],{stdio:'inherit'});
 for(const entry of index.files){
  const member=path.resolve(destination,entry.path);
  if(!member.startsWith(destination+path.sep)||hash(member)!==entry.sha256)throw Error('Retained identity proof member changed');
 }
 inputs.push({path:path.relative(root,indexFile),sha256:hash(indexFile)},{path:path.relative(root,archive),sha256:expected});
 return destination;
}
const v4=extract(path.join(root,'data/macro-improvements/combined-restoration/installation-proof-index.json.gz'),path.join(output,'prior-v4'));
const v5=extract(path.join(root,'data/macro-improvements/loose-ends-v5/publication/installation-source-proof-index.json.gz'),path.join(output,'prior-v5'));
const geometry=[path.join(root,'data/geographic-repair-evidence/index.json'),...['replacement-migration/index.json','creation-migration/index.json'].map(file=>path.join(v4,file)),...['replacement-migration/index.json','creation-migration/index.json'].map(file=>path.join(v5,file))];
const metadata=['macro-boundary-migration.json.gz','macro-foundation/migration-repairs.json.gz','macro-foundation/migration-areas.json.gz','macro-foundation/migration-regions.json.gz'].map(file=>path.join(root,'data',file));
metadata.push(path.join(v4,'reference-receipt.json'));
const sequenceFile=path.join(root,'data/macro-improvements/loose-ends-v5/publication/identity-proof-sequence.json.gz'),sequence=read(sequenceFile);
const previous=[{type:'geometry',file:geometry[0]},...metadata.map(file=>({type:'metadata',file})),...geometry.slice(1).map(file=>({type:'geometry',file}))].map(({type,file})=>({type,sha256:hash(file)}));
if(JSON.stringify(sequence.steps)!==JSON.stringify(previous))throw Error('Retained identity chronology differs from archived proofs');
metadata.push(receiptFile);
sequence.steps.push({type:'metadata',sha256:hash(receiptFile)});
const nextSequence=path.join(output,'identity-proof-sequence.json');
save(nextSequence,sequence);
const release=path.join(output,'geographic-release');
const argv=['--data',path.join(root,'data'),'--geography-data',path.join(candidate,'geography'),'--output',release,'--reviewed-version',String(before.version+1),'--reference-date','2026-10-03','--registry-manifest',path.join(root,'data/geographic-releases/index.json'),'--identity-proof-sequence',nextSequence];
for(const file of geometry)argv.push('--geometry-manifest',file);
for(const file of metadata)argv.push('--metadata-migration',file);
execFileSync(process.execPath,['--max-old-space-size=4096',path.join(root,'scripts/prepare-geographic-release.mjs'),...argv],{stdio:'inherit'});
const manifest=read(path.join(release,'index.json')),after=manifest.releases.at(-1);
if(manifest.new_entities!==0||after.footprints_sha256!==before.footprints_sha256||after.hierarchy_sha256!==receipt.after_sha256)throw Error('Correction release changes geometry/registry or lacks matching hierarchy');
const result={version:1,offline:true,published:false,historical_claims_transferred:false,before_release:before,after_release:after,correction_receipt_sha256:hash(receiptFile),identity_proof_sequence_sha256:hash(nextSequence),preserved_identity_inputs:inputs};
save(path.join(output,'release-preparation.json'),result);
console.log(JSON.stringify(result));
