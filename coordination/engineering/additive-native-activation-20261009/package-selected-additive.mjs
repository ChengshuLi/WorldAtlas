import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {ImmutableReader,loadSelection} from '../../../scripts/check-effective-geographic-regression.mjs';
import {loadPackageInputs,containsPackagePath} from '../../../scripts/package-inputs.mjs';
import {valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const demand=(v,m)=>{if(!v)throw Error(m);};
const publications=new WeakMap();
const ordinary=name=>{
  demand(path.isAbsolute(name)&&path.resolve(name)===name,'Canonical ordinary path required');
  let at=path.parse(name).root;
  for(const component of name.slice(at.length).split(path.sep)){
    at=path.join(at,component);demand(!fs.lstatSync(at).isSymbolicLink(),'Ordinary ancestors required');
  }
  const stat=fs.lstatSync(name);demand(stat.isFile(),'Ordinary whole file required');return stat;
};

// A selected reader deliberately freezes its accepted descriptors. A new copy
// frame reauthenticates the four already accepted pins while charging every
// retained selection/view/descriptor byte. Returned bytes grant no authority.
export function readBoundPublicationAssets(reader,roster,declared) {
  demand(roster.length===4&&new Set(roster.map(p=>p.pin.path)).size===4,'Four distinct bound publication bodies required');
  const copy=new ImmutableReader(reader.repo,reader.version,{
    runtimeBytes:reader.runtimeBytes,executionBytes:reader.executionBytes,
    metadataBytes:reader.metadataBytes+2*valueBytes([...reader.inventory.values()]).length,
    outputBytes:reader.outputBytes,gitExecutable:reader.gitExecutable});
  const actual=roster.map(({pin})=>{
    demand(declared(pin.path),'Undeclared additive publication body');
    let version=pin.commit;try{copy.git('cat-file','-e',version+'^{commit}');}catch{version=copy.version;}
    const p=copy.descriptor(pin.path,version);
    demand(p.mode===pin.mode&&p.git_blob_oid===pin.git_blob_oid&&p.bytes===pin.bytes,'Additive publication whole custody differs');
    copy.admit(p,pin.decoded_bytes??0);return {pin,version};
  });
  const bodies=actual.map(({pin,version})=>copy.read(pin.path,{version,expected:pin.sha256,decoded:pin.decoded_bytes??0}));
  return {bodies,input_inventory:structuredClone([...reader.inventory.values(),...copy.inventory.values()]),complete_phase_bytes:copy.used};
}

// Called before context/database allocations. The package issuer authenticates
// its executing closure; the existing private selected reader authenticates all
// source/rule/current-rebind authority. This bridge grants no new authority.
export async function preparePackageSelectedAdditive({root,currentExecution,consumedContext,restoredReceipt,selectedGrid,geographicRelease}) {
  const selectionPath=path.resolve(root,'data/ownership-selection.json');
  let stat;try{stat=ordinary(selectionPath);}catch(error){if(error.code==='ENOENT')return null;throw error;}
  demand(stat.size<=131072,'Bounded selection metadata required');
  const selectionFd=fs.openSync(selectionPath,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
  let selectionRaw;
  try{
    const buffer=Buffer.alloc(stat.size+1);let offset=0;
    while(offset<buffer.length){const count=fs.readSync(selectionFd,buffer,offset,buffer.length-offset,null);if(!count)break;offset+=count;}
    demand(offset===stat.size,'Whole bounded selection length changed');selectionRaw=buffer.subarray(0,offset);
    const held=fs.fstatSync(selectionFd),end=ordinary(selectionPath);
    for(const key of ['dev','ino','size','mode','mtimeMs','ctimeMs'])demand(stat[key]===held[key]&&held[key]===end[key],'Selection whole identity changed');
  }finally{fs.closeSync(selectionFd);}
  const selection=JSON.parse(selectionRaw);
  if(selection.additive_release===undefined)return null;
  demand(consumedContext&&restoredReceipt,'Selected V4 artifact consumption and original restoration required');
  const {requireConsumedArcticArtifacts}=await import('../arctic-three-retained-land-fit-repair-native-20261008/qualified-artifact-consumer.mjs');
  const consumed=requireConsumedArcticArtifacts(consumedContext);
  const {requireCurrentExecution:requireExecution}=await import('../eastern-two-gap-repair-native-20261007/current-execution.mjs');
  if(currentExecution!==undefined)demand(currentExecution===consumed.currentExecution,'Foreign outer package execution');
  const execution=requireExecution(consumed.currentExecution);
  demand(execution.stage_root===fs.realpathSync(root),'Additive bridge belongs to another package stage');
  const definition=loadPackageInputs(root);
  const git=process.platform==='darwin'?'/Library/Developer/CommandLineTools/usr/bin/git':'/usr/bin/git';
  const gitStat=ordinary(git),executionBytes=2*execution.files.reduce((n,p)=>n+p.bytes,0);
  // Literal original restorer saved state is {receipt,map,old,membershipImage}.
  // The whole member sizes come from its pinned canonical/prior indexes; the
  // membership index is retained whole. Index helpers themselves have returned.
  demand(restoredReceipt.issue===1295&&restoredReceipt.canonical_index_sha256==='b82b195d94530d9b1f48153f7e47616f8b841cb1438ddf59994ba4869a1d7876'
    &&restoredReceipt.prior_index_sha256==='ca1ab5fc3ef24470bcb79412f1d47a88281c6df0931461c5eb356079b75986fe'
    &&restoredReceipt.new_release_memberships?.index_sha256==='9e21c69da2d4eb68ff66a586c3efa716a71224ce9344338fb2c9da1b2d62989c',
    'Different inherited restoration requires an explicit complete carry catalogue');
  const inheritedBytes=2*(461664+95064+235002+valueBytes(restoredReceipt).length
    +valueBytes(consumedContext).length+valueBytes(consumed).length);
  const metadataBytes=8*1048576+inheritedBytes+2*valueBytes(execution).length;
  const reader=new ImmutableReader(execution.source_root,execution.source_commit,{
    runtimeBytes:execution.runtime.bytes+gitStat.size,executionBytes,
    metadataBytes,outputBytes:4194304,gitExecutable:git});
  const wholeRead=reader.read.bind(reader);
  reader.read=(name,options)=>{
    demand(containsPackagePath(definition.inputs,name)||execution.files.some(p=>p.path===name),
      'Undeclared additive package source/code payload: '+name);
    return wholeRead(name,options);
  };
  const gitFd=fs.openSync(git,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
  let gitHash;
  try{gitHash=createHash('sha256').update(fs.readFileSync(gitFd)).digest('hex');
    const end=fs.fstatSync(gitFd);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])demand(end[k]===gitStat[k],'Git program drift');
  }finally{fs.closeSync(gitFd);}
  const snapshot=loadSelection(reader);
  demand(snapshot&&valueSha(snapshot.selection)===valueSha(selection),'Package selection differs from actual immutable selected source');
  demand(snapshot.manifest&&snapshot.selection.sha256===selectedGrid.sha256
    &&snapshot.selection.release_id===geographicRelease.id,'Additive bridge differs from selected build bank');
  const view=snapshot.additive;demand(view,'Require privately consumed additive authority');
  const envelope=view.envelope;
  demand(valueSha(envelope.base_reference)===valueSha(Object.fromEntries(['id','footprints_sha256','hierarchy_sha256'].map(k=>[k,geographicRelease[k]]))),
    'Additive runtime reference differs from actual build source');
  const roster=Object.entries(view.sidecar.logical_asset_map).map(([role,pin])=>({role,pin,logical:envelope[role]}));
  for(const {pin,logical} of roster){
    demand(containsPackagePath(definition.inputs,pin.path),'Undeclared additive package payload: '+pin.path);
    demand(/^additive-repairs\/[A-Za-z0-9_.-]+$/.test(logical.path),'Unsafe additive public asset path');
  }
  demand(new Set(roster.map(p=>p.logical.path)).size===4,'Four distinct additive public assets required');
  const outputBytes=roster.reduce((n,p)=>n+p.pin.bytes,0);demand(outputBytes<=4194304,'Complete additive publication exceeds reserved output');
  reader.metadataBytes+=snapshot.metadataBytes+2*valueBytes(view).length;reader.phase();
  const copied=readBoundPublicationAssets(reader,roster,name=>containsPackagePath(definition.inputs,name)||execution.files.some(p=>p.path===name));
  const bodies=copied.bodies;
  requireExecution(execution);
  const gitEnd=ordinary(git);for(const k of ['dev','ino','size','mode','mtimeMs','ctimeMs'])demand(gitEnd[k]===gitStat[k],'Git program pathname drift');
  demand(createHash('sha256').update(fs.readFileSync(git)).digest('hex')===gitHash,'Whole executing Git program drift');
  const token=Object.freeze({additiveRelease:envelope,reference_release:envelope.effective_reference});
  publications.set(token,{root:fs.realpathSync(root),roster,bodies,gitHash,inheritedBytes,outputBytes,
    input_inventory:copied.input_inventory,complete_phase_bytes:copied.complete_phase_bytes});
  return token;
}

export function prepareOrdinaryPublicationDirectory(root,relative) {
  demand(relative==='dist/additive-repairs','Exact additive publication directory required');
  let at=fs.realpathSync(root);
  for(const component of relative.split('/')){
    at=path.join(at,component);
    let stat;try{stat=fs.lstatSync(at);}catch(error){if(error.code!=='ENOENT')throw error;}
    if(stat)demand(stat.isDirectory()&&!stat.isSymbolicLink(),'Ordinary publication ancestors required');
    else{fs.mkdirSync(at,{mode:0o755});stat=fs.lstatSync(at);demand(stat.isDirectory()&&!stat.isSymbolicLink(),'Fresh ordinary publication directory required');}
  }
  return at;
}

export function publishPackageSelectedAdditive(token,{root,destination='dist'}) {
  if(token===null)return null;
  const retained=publications.get(token);demand(retained&&retained.root===fs.realpathSync(root),'Privately authenticated package additive publication required');
  demand(destination==='dist','Stock public destination required');
  // Bodies were whole authenticated and admitted before application allocation.
  // No new source reads or authority parsing occur during this publication.
  for(let i=0;i<retained.roster.length;i++){
    const name=path.resolve(root,destination,retained.roster[i].logical.path);
    prepareOrdinaryPublicationDirectory(root,'dist/additive-repairs');
    const fd=fs.openSync(name,fs.constants.O_WRONLY|fs.constants.O_CREAT|fs.constants.O_EXCL|fs.constants.O_NOFOLLOW,0o644);
    try{fs.writeFileSync(fd,retained.bodies[i]);fs.fsyncSync(fd);}finally{fs.closeSync(fd);}
  }
  publications.delete(token);return token;
}
