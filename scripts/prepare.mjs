// Natural Earth is public domain. Keep shared edges during simplification.
import fs from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import mapshaper from 'mapshaper';
const revision = 'ca96624a56bd078437bca8184e78163e5039ad19';
await fs.mkdir('.cache', { recursive: true });
const hashes = {};
const codesRevision = '2e9d6498a0456f4afc2f6cf367d1e12a9ed4afe1';
async function download(name) {
  const path = `.cache/${name}.json`;
  let raw;
  try { raw = await fs.readFile(path, 'utf8'); } catch {
    const response = await fetch(`https://raw.githubusercontent.com/nvkelso/natural-earth-vector/${revision}/geojson/${name}.geojson`);
    if (!response.ok) throw new Error(`Download failed: ${response.status}`);
    raw = await response.text(); await fs.writeFile(path, raw);
  }
  hashes[name] = createHash('sha256').update(raw).digest('hex');
  return JSON.parse(raw).features;
}
await download('ne_10m_admin_0_countries');
await download('ne_10m_admin_1_states_provinces');
execFileSync('python', ['scripts/administrative.py'], {stdio:'inherit'});
const simplified = await mapshaper.applyCommands('-i input.geojson -simplify 25% keep-shapes -o output.geojson precision=0.0001', {'input.geojson': await fs.readFile('.cache/administrative.geojson', 'utf8')});
await fs.mkdir('data', { recursive: true });
await fs.writeFile('.cache/world-display.geojson', simplified['output.geojson']);
execFileSync('python', ['scripts/repair-geometries.py', '.cache/world-display.geojson'], {stdio:'inherit'});
const display=JSON.parse(await fs.readFile('.cache/world-display.geojson','utf8'));
await fs.mkdir('data/geography',{recursive:true});
const parts=[];
for(let i=0;i<display.features.length;i+=1500){
  const part=`geography/part-${i/1500}.json`;parts.push(part);
  await fs.writeFile(`data/${part}`,JSON.stringify({type:'FeatureCollection',features:display.features.slice(i,i+1500)}));
}
await fs.writeFile('data/world-index.json',JSON.stringify({parts}));
execFileSync('python', ['scripts/complete-hierarchy.py'], {stdio:'inherit'});
execFileSync('python', ['scripts/reconcile-topology.py'], {stdio:'inherit'});
execFileSync('python', ['scripts/geographic-regions.py'], {stdio:'inherit'});
const hasReviewedDecisions=await fs.access('data/geographic-decisions').then(()=>true,()=>false);
for(const script of ['semantic-sources','complete-coverage','semantic-locations','refine-remote','finalize-geography','framework-sources','refine-italy-framework','rebuild-framework','refine-global-locations','reconcile-regional-membership','reconcile-border-parents','reference-polities','clean-local-source','apply-macro-review',...(hasReviewedDecisions?['apply-geographic-decisions']:[]),'review-framework','audit-granularity','review-world'])execFileSync('python',[`scripts/${script}.py`],{stdio:'inherit'});
await fs.writeFile('data/sources.json', JSON.stringify({ revision, hashes, country_codes: {revision: codesRevision, sha256: createHash('sha256').update(await fs.readFile('.cache/country-codes.csv')).digest('hex'), url: 'https://github.com/datasets/country-codes'}, url: 'https://www.geoboundaries.org/', description: 'Country-specific named administrative districts with sourced city aggregation, compact territory consolidation and physical rural subdivisions. See semantic-report.json and granularity-audit.json. Counts are outcomes, not quotas. Versioned geographic groups use Natural Earth, China prefectures, ISTAT functional territories and explicitly identified retained WGSRPD groups, independently of political ownership. Geometry is simplified for display. Every location has a complete six-level atlas hierarchy. Source groupings and explicitly identified whole-territory tiers are recorded in hierarchy-report.json. Per-country source dates, licenses, and hashes are recorded in administrative-sources.json.' }, null, 2));
const finalIndex=JSON.parse(await fs.readFile('data/world-index.json','utf8'));
const ids=new Set((await Promise.all(finalIndex.parts.map(async part=>JSON.parse(await fs.readFile(`data/${part}`,'utf8')).features))).flat().map(f=>f.id));
const examples = JSON.parse(await fs.readFile('data/examples.json', 'utf8'));
examples.states = examples.states.filter(record=>ids.has(record.location_id));
await fs.writeFile('data/examples.json', JSON.stringify(examples, null, 2));
