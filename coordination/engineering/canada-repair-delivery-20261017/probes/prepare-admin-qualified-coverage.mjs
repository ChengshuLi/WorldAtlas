// Narrow only explicit request class rows after the complete original diagnostic.
// Whole source/physical bodies, membership, targets and every negative stay intact.
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [repo, commit, output, accounting] = process.argv.slice(2);
if (!repo || !/^[a-f0-9]{40}$/.test(commit) || !output || !accounting) throw Error('Require repository, exact input commit and two fresh output paths');
const {pinReader,jsonBytes,digest}=await import(pathToFileURL(path.join(repo,'scripts/prepare-delivery-handoff.mjs')));
const reader=pinReader(repo), P='coordination/engineering/canada-repair-delivery-20261017/';
const pins=['config/admin-source-evidence-003.json','admin-supported-native-patch-003.json','admin-native-diagnostic-003/native-diagnostic.json'].map(p=>reader.pin(commit,P+p));
const config=reader.json(pins[0]), patch=reader.json(pins[1]), diagnostic=reader.json(pins[2]);
if (!jsonBytes(patch.rows).equals(jsonBytes(diagnostic.supported_rows))) throw Error('Supported patch differs from complete original diagnostic');
const allowed=new Map(), original=new Set(), held=new Set();
const key=(y,x,o)=>`${y}/${x}/${o}`;
for(const r of diagnostic.requested_rows)for(const [a,b,o]of r.runs)for(let x=a;x<b;x++)original.add(key(r.y,x,o));
for(const r of diagnostic.held_rows)for(const [a,b,o]of r.runs)for(let x=a;x<b;x++)held.add(key(r.y,x,o));
for(const row of patch.rows)for(const [a,b,o]of row.runs){let m=allowed.get(o);if(!m)allowed.set(o,m=new Map());let rs=m.get(row.y);if(!rs)m.set(row.y,rs=[]);rs.push([a,b]);}
const before=jsonBytes(config), removed=new Set(), retained=new Set(), seen=new Set();let changed=0;
const oldRows=[];
for(const t of config.source_evidence.targets){if(t.coverage_rows===undefined)continue;
 if(seen.has(t.pixelIndex))throw Error('Repeated owner coverage rows');seen.add(t.pixelIndex);
 oldRows.push([t,t.coverage_rows]);const next=[];
 for(const row of t.coverage_rows){const runs=[];for(const [lo,hi,kind]of row.runs){
  for(let x=lo;x<hi;x++){const k=key(row.y,x,t.pixelIndex);if(!original.has(k))throw Error('Foreign original coverage key');if(held.has(k))removed.add(k);else retained.add(k);}
  for(const [a,b]of allowed.get(t.pixelIndex)?.get(row.y)??[]){const start=Math.max(a,lo),end=Math.min(b,hi);if(start<end)runs.push([start,end,kind]);}
 }if(runs.length)next.push({y:row.y,runs});}
 if(!next.length)throw Error('No supported class rows for original owner');
 if(!jsonBytes(next).equals(jsonBytes(t.coverage_rows)))changed++;
 t.coverage_rows=next;
}
if(original.size!==293965||held.size!==53||removed.size!==53||retained.size!==293912||seen.size!==137||[...held].some(k=>!removed.has(k)))throw Error('Complete original diagnostic partition changed');
const body=jsonBytes(config),saved=oldRows.map(([t])=>t.coverage_rows);
oldRows.forEach(([t,r])=>{t.coverage_rows=r;});
if(!before.equals(jsonBytes(config)))throw Error('A non-coverage field changed');
oldRows.forEach(([t],i)=>{t.coverage_rows=saved[i];});
fs.writeFileSync(output,body,{flag:'wx'});
const result={kind:'supported-request-coverage-row-rebinding',inputs:pins,original_cells:293965,supported_cells:293912,explicit_held_cells:53,original_targets:137,complete_source_members:config.source_evidence.targets.length,coverage_owners_changed:changed,only_changed_fields:'targets[].coverage_rows intersected with diagnostic supported_rows; every other configuration byte has canonical equality',removed_keys_exactly_diagnostic_holds:true,output:{bytes:body.length,sha256:digest(body)},limits:['This is request-scope preparation after a full original diagnostic. It does not qualify ownership or remove original held obligations.','Original full coverage rows and diagnostic remain immutable inputs. Full physical/source support and all manual and generated territorial negatives remain required.']};
fs.writeFileSync(accounting,jsonBytes(result),{flag:'wx'});console.log(JSON.stringify(result));
