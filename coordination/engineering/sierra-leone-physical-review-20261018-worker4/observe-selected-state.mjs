// Read existing selected products only; no authority qualification or composition.
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {selectedBootstrap, loadBaseSelection, loadNativeRowTable, acquireNativeRows}
  from '../../../scripts/check-effective-geographic-regression.mjs';

const root=path.dirname(fileURLToPath(import.meta.url));
const need=(ok,message)=>{if(!ok)throw Error(message);};
const sha=b=>createHash('sha256').update(b).digest('hex');
const base='75861b9784f75b7894bfc51fa0419f40f966157d';
const output=path.resolve(process.argv[2]??'');
need(process.argv[2]&&!fs.existsSync(output)&&!fs.lstatSync(output,{throwIfNoEntry:false}), 'Fresh output required');
for(let p=output;p!==path.dirname(p);p=path.dirname(p))need(!fs.lstatSync(p,{throwIfNoEntry:false})?.isSymbolicLink(),'Symlink output refused');
need(fs.statSync(path.dirname(output)).isDirectory(),'Output parent required');
const intervalBytes=fs.readFileSync(path.join(root,'intervals/block-030.json.gz'));
need(sha(intervalBytes)==='534192593d9caba16e86286e888e8384cfdadf35f5372d6536b31139565001a0','Retained Cloud intervals changed');
const intervals=JSON.parse(gunzipSync(intervalBytes));
need(intervals.length===613,'Retained original interval count');
const requested=intervals.flatMap(([y,a,b,owners])=>{
  need(owners.length===1,'Original unique owner required');
  return Array.from({length:b-a},(_,i)=>({y,x:a+i,original_owner:owners[0]}));
});
need(requested.length===1213&&new Set(requested.map(k=>k.y+':'+k.x)).size===1213,'Exact original keys required');
const started=new Date().toISOString();
console.log(JSON.stringify({event:'actual-start',utc:started,pid:process.pid,operation:'stock-existing-native-owner-observation',original_cells:1213,intervals:613,owners:7,base}));
const {beforeReader:reader,executionCode,runtime,identities}=selectedBootstrap(process.cwd(),base,base);
for(const p of executionCode){const actual=reader.read(p.path,{version:base});need(actual.length===p.bytes&&sha(actual)===p.sha256,'Executed stock code drift: '+p.path);}
const snapshot=loadBaseSelection(reader);
const table=loadNativeRowTable(snapshot);
const rows=[...new Set(requested.map(k=>k.y))].sort((a,b)=>a-b);
const projected=acquireNativeRows(snapshot,table,rows);
const selection=snapshot.selection,hook=selection.additive_release;
need(hook,'Actual selected additive sidecar missing');
const sideBytes=reader.read(hook.path,{expected:hook.sha256});
need(sideBytes.length===hook.bytes,'Actual selected sidecar changed');
const sidecar=JSON.parse(sideBytes),p=sidecar.logical_asset_map.patch;
// This authenticates the literal accepted patch, without traversing authorities.
const descriptor=reader.descriptor(p.path,p.commit);
need(['mode','git_blob_oid','bytes'].every(k=>descriptor[k]===p[k]),'Accepted patch ordinary identity changed');
const patchEncoded=reader.read(p.path,{version:p.commit,expected:p.sha256});
let patchBytes=patchEncoded;
if(p.decoded_bytes!==undefined){patchBytes=gunzipSync(patchEncoded);need(patchBytes.length===p.decoded_bytes&&sha(patchBytes)===p.decoded_sha256,'Accepted patch decoded identity changed');}
const patch=JSON.parse(patchBytes),patchRows=new Map(patch.rows.map(r=>[r.y,r.runs]));
const baseRows=new Map(rows.map((y,i)=>[y,Array.from({length:(projected.offsets[i+1]-projected.offsets[i])/3},(_,j)=>Array.from(projected.words.subarray(projected.offsets[i]+j*3,projected.offsets[i]+j*3+3)))]));
const contacts=(runs,x)=>runs.filter(([a,b])=>a<=x&&x<b).map(r=>r[2]);
const keys=requested.map(k=>{
  const base_owners=contacts(baseRows.get(k.y),k.x),additive_owners=contacts(patchRows.get(k.y)??[],k.x);
  need(base_owners.length<=1&&additive_owners.length<=1,'Malformed existing owner rows');
  const conflict=base_owners.length>0&&additive_owners.length>0;
  return {...k,base_owner:base_owners[0]??0,accepted_additive_owner:additive_owners[0]??0,
    effective_selected_owner:conflict?null:(additive_owners[0]??base_owners[0]??0),existing_product_overlap:conflict};
});
const source=snapshot.geometrySources.read('data/geography/part-22.json');
const selectedTargets=source.collection.features.filter(f=>f.properties.id.startsWith('gb:SLE:ADM2:'));
need(selectedTargets.length===14,'Complete selected SLE primary target context required');
const product={kind:'SLE-original1213-existing-selected-owner-observation',base,started_utc:started,finished_utc:new Date().toISOString(),
  original_cells:1213,original_intervals:613,original_owners:7,affected_native_rows:rows.length,keys,selected_targets:selectedTargets,
  native_custody:projected.custody,selector:selection,patch_pin:p,patch_file_sha256:sha(patchEncoded),sidecar_pin:reader.inventory.get(base+':'+hook.path),
  selected_source:{source:source.source,whole_sha256:source.whole_sha256},stock_execution_code:executionCode,runtime,identities,
  consumed_inputs:[...reader.inventory.values()],
  limits:['Read-only observations of existing selected products at the stated immutable base. No authority requalification, native raster production or selected composition.',
    'Base, additive and effective owner states remain separate. Existing-product overlaps remain explicit rather than resolved by invented precedence.',
    'The complete original1213/613/7 review scope is retained even if an existing owner is observed. Final current-baseline admission belongs to parent.']};
const body=Buffer.from(JSON.stringify(product,null,2)+'\n');
fs.mkdirSync(output);fs.writeFileSync(path.join(output,'selected-state.json'),body,{flag:'wx'});
const publication={version:1,complete:true,files:[{path:'selected-state.json',bytes:body.length,sha256:sha(body)}]};
fs.writeFileSync(path.join(output,'publication.json'),JSON.stringify(publication,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({event:'actual-exit',utc:product.finished_utc,pid:process.pid,cells:keys.length,rows:rows.length,base_occupied:keys.filter(k=>k.base_owner).length,additive_occupied:keys.filter(k=>k.accepted_additive_owner).length,conflicts:keys.filter(k=>k.existing_product_overlap).length,output,bytes:body.length,sha256:sha(body)}));
