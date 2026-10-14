// Recheck exact committed scientific inputs; do not re-fetch different vintages.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
import {constructOriginalAuthority} from '../../../scripts/delivery-handoff-advance.mjs';
import {ImmutableReader} from '../../../scripts/check-effective-geographic-regression.mjs';
const directory=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(directory,'../../..');
const commit=execFileSync('git',['-C',root,'rev-parse','HEAD'],{encoding:'utf8'}).trim();
const binding=JSON.parse(fs.readFileSync(path.join(directory,'authority-binding.json')));
const locator=pin=>({commit:pin.commit,path:pin.path});
const reader=new ImmutableReader(root,commit,{allowance:{phaseBytes:1073741824,rssBytes:1610612736}});
const start=Date.now();
const result=constructOriginalAuthority(reader,{source_evidence:locator(binding.source_evidence),native_patch:locator(binding.native_patch)});
for(const [name,body]of Object.entries(result.products))
  if(!body.equals(fs.readFileSync(path.join(directory,name))))throw Error('Original authority body differs: '+name);
console.log(JSON.stringify({targets:result.ledger_rows.length,cells:result.ledger_rows.reduce((sum,row)=>sum+row.native_cells,0),
  rule_sha256:result.rule_sha256,elapsed_seconds:(Date.now()-start)/1000,max_rss:process.resourceUsage().maxRSS*1024}));
