import fs from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import mapshaper from 'mapshaper';
const version='v0.2.0-duplicate';
const url=`https://raw.githubusercontent.com/Seshat-Global-History-Databank/cliopatria/${version}/cliopatria.geojson.zip`;
await fs.mkdir('.cache',{recursive:true});
const zip='.cache/cliopatria.geojson.zip';
try {await fs.access(zip);} catch {
  const response=await fetch(url); if(!response.ok)throw new Error(`Cliopatria download failed: ${response.status}`);
  await fs.writeFile(zip,Buffer.from(await response.arrayBuffer()));
}
execFileSync('python',['-c',"import zipfile; z=zipfile.ZipFile('.cache/cliopatria.geojson.zip'); name=next(n for n in z.namelist() if n.endswith('.geojson') and not n.startswith('__MACOSX')); open('.cache/cliopatria.geojson','wb').write(z.read(name))"]);
const raw=JSON.parse(await fs.readFile('.cache/cliopatria.geojson','utf8'));
const features=raw.features.filter(f=>f.properties.Type==='POLITY' && f.properties.FromYear<=2024 && f.properties.ToYear>=-3000).map((f,i)=>({type:'Feature',id:`cliopatria-${i}`,geometry:f.geometry,properties:{name:f.properties.Name,valid_from:Math.max(-3000,f.properties.FromYear===0?1:f.properties.FromYear),valid_to:f.properties.ToYear===-1||f.properties.ToYear===0?1:f.properties.ToYear+1,source_from:f.properties.FromYear,source_to:f.properties.ToYear,source:`Cliopatria ${version} / Seshat`,wikipedia:f.properties.Wikipedia,wikidata:f.properties.Wikidata,seshat_id:f.properties.SeshatID}})).sort((a,b)=>a.properties.valid_from-b.properties.valid_from);
const output=await mapshaper.applyCommands('-i input.geojson -simplify 25% keep-shapes -o output.geojson precision=0.0001',{'input.geojson':JSON.stringify({type:'FeatureCollection',features})});
const simplified=JSON.parse(output['output.geojson']).features, records=[];
await fs.mkdir('data/cliopatria',{recursive:true});
for(let i=0;i<simplified.length;i+=200) {
  const chunk=`part-${String(i/200).padStart(3,'0')}.json`, part=simplified.slice(i,i+200);
  await fs.writeFile(`data/cliopatria/${chunk}`,JSON.stringify({type:'FeatureCollection',features:part}));
  for(const f of part)records.push({id:f.id,valid_from:f.properties.valid_from,valid_to:f.properties.valid_to,chunk});
}
const sha256=createHash('sha256').update(await fs.readFile(zip)).digest('hex');
await fs.writeFile('data/cliopatria/index.json',JSON.stringify({source:'Bennett et al. (2025), Cliopatria / Seshat Global History Databank',version,url:'https://doi.org/10.1038/s41597-025-04516-9',download_url:url,sha256,license:'CC BY 4.0',license_url:'https://creativecommons.org/licenses/by/4.0/',note:'Coarse reconstructed political territories. POLITY rows only; RELATION composites excluded. Source endpoints are inclusive; exported endpoints are exclusive. Source year-zero endpoints are normalized to preserve inclusion for all nonzero calendar years. Simplified and repaired for display.',records}));
console.log(`Prepared ${simplified.length} historical territory records.`);
execFileSync('python', ['scripts/repair-geometries.py', 'data/cliopatria'], {stdio:'inherit'});
