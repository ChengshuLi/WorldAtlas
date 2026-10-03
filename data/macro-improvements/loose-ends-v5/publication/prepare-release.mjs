// Offline release replay; keeps the original identity registry and every prior proof.
import fs from 'node:fs';import path from 'node:path';import zlib from 'node:zlib';import{createHash}from'node:crypto';import{execFileSync}from'node:child_process';
const args=process.argv.slice(2),options={};for(let i=0;i<args.length;i+=2){if(!['--root','--stage','--output'].includes(args[i])||!args[i+1]||options[args[i]])throw Error('Use --root ROOT --stage VERIFIED-STAGE --output FRESH-DIRECTORY');options[args[i]]=path.resolve(args[i+1]);}
if(Object.keys(options).length!==3)throw Error('All three arguments are required');
const root=options['--root'],stage=options['--stage'],output=options['--output'];
if(output===root||output.startsWith(root+path.sep)||fs.existsSync(output))throw Error('Fresh external output directory required');
const sha=raw=>createHash('sha256').update(raw).digest('hex'),hash=f=>sha(fs.readFileSync(f));
const read=f=>JSON.parse(f.endsWith('.gz')?zlib.gunzipSync(fs.readFileSync(f)):fs.readFileSync(f));
const save=(f,x)=>fs.writeFileSync(f,JSON.stringify(x)+'\n');
const validation=read(path.join(stage,'integration-validation.json'));
if(validation.verified!==true||validation.history_transfer!==false||validation.before_locations!==49623||validation.after_locations!==49625||validation.changed_ids!==3||validation.added_ids!==2||validation.removed_ids!==0)throw Error('Exact combined source-stage validation required');
const proofIndexFile=path.join(root,'data/macro-improvements/combined-restoration/installation-proof-index.json.gz'),proofIndex=read(proofIndexFile),archive=path.join(path.dirname(proofIndexFile),proofIndex.archive.path);
if(hash(archive)!==proofIndex.archive.sha256)throw Error('Predecessor archive hash changed');
fs.mkdirSync(output,{recursive:true});const prior=path.join(output,'prior-v4');fs.mkdirSync(prior);
// Python rejects links, special files and escaping paths before extracting trusted bytes.
execFileSync('python3',['-c',`import pathlib,tarfile,sys
p=pathlib.Path(sys.argv[2]).resolve()
with tarfile.open(sys.argv[1]) as t:
 for m in t.getmembers():
  q=(p/m.name).resolve()
  if not q.is_relative_to(p) or not m.isfile(): raise ValueError('Unsafe predecessor archive entry')
 t.extractall(p,filter='data')
`,archive,prior],{stdio:'inherit'});
for(const f of proofIndex.files)if(hash(path.join(prior,f.path))!==f.sha256)throw Error('Predecessor proof member hash changed');
const original=path.join(root,'data/geographic-repair-evidence/index.json');
const metadata=['macro-boundary-migration.json.gz','macro-foundation/migration-repairs.json.gz','macro-foundation/migration-areas.json.gz','macro-foundation/migration-regions.json.gz'].map(f=>path.join(root,'data',f));metadata.push(path.join(prior,'reference-receipt.json'));
const oldGeometry=[original,path.join(prior,'replacement-migration/index.json'),path.join(prior,'creation-migration/index.json')];
const nextGeometry=[path.join(stage,'replacement-migration/index.json'),path.join(stage,'creation-migration/index.json')];
const sequence=read(path.join(root,'data/macro-improvements/combined-restoration/identity-proof-sequence.json'));
const expected=[{type:'geometry',file:original},...metadata.map(file=>({type:'metadata',file})),...oldGeometry.slice(1).map(file=>({type:'geometry',file}))].map(({type,file})=>({type,sha256:hash(file)}));
if(JSON.stringify(sequence.steps)!==JSON.stringify(expected))throw Error('Archived identity chronology does not match predecessor receipts');
sequence.steps.push(...nextGeometry.map(file=>({type:'geometry',sha256:hash(file)})));const sequenceFile=path.join(output,'identity-proof-sequence.json');save(sequenceFile,sequence);
const releaseOutput=path.join(output,'geographic-release');
const argv=['--data',path.join(root,'data'),'--geography-data',path.join(stage,'creation'),'--output',releaseOutput,'--reviewed-version','5','--registry-manifest',path.join(root,'data/geographic-releases/index.json'),'--identity-proof-sequence',sequenceFile];
for(const file of [...oldGeometry,...nextGeometry])argv.push('--geometry-manifest',file);for(const file of metadata)argv.push('--metadata-migration',file);
execFileSync(process.execPath,['--max-old-space-size=4096',path.join(root,'scripts/prepare-geographic-release.mjs'),...argv],{stdio:'inherit'});
const release=read(path.join(releaseOutput,'index.json')),summary={version:1,offline:true,published:false,history_transfer:false,release:release.releases.at(-1),prior_archive_sha256:hash(archive),identity_proof_sequence_sha256:hash(sequenceFile),integration_validation_sha256:hash(path.join(stage,'integration-validation.json'))};
save(path.join(output,'release-preparation.json'),summary);console.log(JSON.stringify(summary));
