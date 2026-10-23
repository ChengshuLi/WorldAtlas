import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {pinReader, jsonBytes, digest} from '../../../../scripts/prepare-delivery-handoff.mjs';

const root = process.cwd();
const evidenceRoot = 'coordination/engineering/congo-original-repair-20261018/residual-930-research-20261023/evidence';
const templatePath = 'coordination/engineering/congo-original-repair-20261018/kimvula-source-target-diagnostic-001/source-evidence-generated/source-evidence.json';
const physicalPin = {commit:'7839ae9de7d57c732050df05e7f6d5c9b42afd88', path:'coordination/engineering/congo-original-repair-20261018/physical-001/whole-target-support.json'};
const sourceStagePin = {commit:'7839ae9de7d57c732050df05e7f6d5c9b42afd88', path:'coordination/engineering/congo-original-repair-20261018/source-stage-001/original-stage-inputs.json'};
const lundaId = 'gb:AGO:ADM1:26408823B58820355179323';
const targetsById = new Map([
  ['gb:COD:ADM2:63176286B26674316015082', {owner:14464, name:'Sandoa'}],
  ['gb:COD:ADM2:63176286B41140464701712', {owner:14492, name:'Kapanga'}],
]);
const read = rel => JSON.parse(fs.readFileSync(path.join(root, rel), 'utf8'));
const reader = pinReader(root);
const head = execFileSync('git', ['rev-parse', 'HEAD'], {cwd:root, encoding:'utf8'}).trim();
const matrix = read(`${evidenceRoot}/930-key-center-conflict-matrix.json`);
const physical = read(`${evidenceRoot}/frozen-physical-mask-membership-join.json`);
const template = read(templatePath);
const physicalEvidencePin = reader.pin(physicalPin.commit, physicalPin.path);
const sourceStage = reader.json(reader.pin(sourceStagePin.commit, sourceStagePin.path));
const wholeReceipt = reader.json(physicalEvidencePin);
const familyParts = template.territorial_exclusion_sources;
const sourceBodyManifestBytes = fs.readFileSync(`${evidenceRoot}/verified-source-body-manifest.json`);
const sourceBodyManifest = JSON.parse(sourceBodyManifestBytes.toString('utf8'));
const sourceIds = new Set(familyParts.map(f => f.source_id));
if (sourceIds.size !== 20) throw new Error(`Expected 20 complete original negative families, got ${sourceIds.size}`);
if (!Array.isArray(sourceStage) || sourceStage.length !== 50) throw new Error('Original 50-target source-stage pin changed');
if (wholeReceipt.scope?.target_count !== undefined && wholeReceipt.scope.target_count !== 50) throw new Error('Whole-target receipt scope differs');

const physByKey = new Map(physical.result.keys.map(r => [`${r.owner_id}/${r.y}/${r.x}`, r]));
const sourceByTarget = new Map(sourceStage.map(s => [s.target, s]));
const rows = matrix.rows.filter(row => row.inside_center_candidates.some(c => c.source_id === lundaId));
if (rows.length !== 115) throw new Error(`Lunda Sul key count changed: ${rows.length}`);
const counts = new Map();
for (const row of rows) {
  const [owner,y,x] = row.key;
  const targetMeta = targetsById.get(row.original_cod_target);
  if (!targetMeta || targetMeta.owner !== owner || row.original_class !== 'land' || !row.primary_target_source_vector_member) throw new Error(`Unexpected target/class/vector at ${row.key}`);
  const mask = physByKey.get(`${owner}/${y}/${x}`);
  if (!mask?.physical_support_mask || mask.inland_water_support_mask) throw new Error(`Physical mask does not support land row ${row.key}`);
  const stage = sourceByTarget.get(row.original_cod_target);
  if (!stage || stage.consumed?.properties?.shapeName !== targetMeta.name || stage.selected?.id !== row.original_cod_target) throw new Error(`Original source-stage identity mismatch for ${row.original_cod_target}`);
  const byOwner = counts.get(owner) ?? new Map();
  const xs = byOwner.get(y) ?? [];
  xs.push(x); byOwner.set(y,xs); counts.set(owner,byOwner);
}
const targets = [...targetsById.entries()].map(([targetId,meta]) => {
  const entry = sourceByTarget.get(targetId);
  const coverage = [...counts.get(meta.owner).entries()].sort((a,b)=>a[0]-b[0]).map(([y,xs])=>{
    xs.sort((a,b)=>a-b); const runs=[];
    for(const x of xs){const prev=runs.at(-1);if(prev&&prev[1]===x)prev[1]++;else runs.push([x,x+1,'mapped_land_support']);}
    return {y,runs};
  });
  return {id:targetId,target_id:targetId,pixelIndex:meta.owner,source_family:'gb:COD:ADM2',base_geometry:entry.selected.geometry,
    coverage_classes:['mapped_land_support'],coverage_rows:coverage,source_receipt_sha256:physicalEvidencePin.sha256};
});
const patchRows=[];
for(const [owner, byY] of counts){
  for(const [y,xs] of [...byY.entries()].sort((a,b)=>a[0]-b[0])){
    xs.sort((a,b)=>a-b);const runs=[];
    for(const x of xs){const prev=runs.at(-1);if(prev&&prev[1]===x&&prev[2]===owner)prev[1]++;else runs.push([x,x+1,owner]);}
    patchRows.push({y,runs});
  }
}
patchRows.sort((a,b)=>a.y-b.y||a.runs[0][0]-b.runs[0][0]);
const sourceEvidence = structuredClone(template);
delete sourceEvidence.base_reference; delete sourceEvidence.native_contract; delete sourceEvidence.native_latitudes; delete sourceEvidence.owner_roster; delete sourceEvidence.territorial_exclusion_sources;
sourceEvidence.targets = targets;
const config = {version:1, selector:{commit:head,path:'data/ownership-selection.json'}, compact_territorial_exclusions:true,
  territorial_exclusion_families:familyParts.map(f=>f.source_id), source_evidence:sourceEvidence};
const out=`${path.dirname(new URL(import.meta.url).pathname)}`;
fs.writeFileSync(path.join(out,'source-evidence-config.json'),jsonBytes(config));
fs.writeFileSync(path.join(out,'native-patch.json'),jsonBytes({rows:patchRows}));
const report={version:1,kind:'cod-lunda-sul-115-input-binding-v1',code_commit:head,
  source_stage:reader.pin(sourceStagePin.commit,sourceStagePin.path),physical_evidence:physicalEvidencePin,
  matrix_path:`${evidenceRoot}/930-key-center-conflict-matrix.json`,matrix_sha256:digest(fs.readFileSync(`${evidenceRoot}/930-key-center-conflict-matrix.json`)),
  physical_mask_join_path:`${evidenceRoot}/frozen-physical-mask-membership-join.json`,physical_mask_join_sha256:digest(fs.readFileSync(`${evidenceRoot}/frozen-physical-mask-membership-join.json`)),
  source_body_manifest_sha256:digest(sourceBodyManifestBytes),candidate_source_id:lundaId,source_family_count:sourceIds.size,
  target_counts:{Sandoa:rows.filter(r=>r.original_cod_target_name==='Sandoa').length,Kapanga:rows.filter(r=>r.original_cod_target_name==='Kapanga').length},
  requested_cells:rows.length,all_original_land:true,all_original_vector_members:true,all_physical_support:true,all_inland_water_support:false,
  limits:['Center conflict and frozen-mask consistency only; no territorial applicability or whole-cell conclusion.','No geometry producer or source observer rerun.','The exact stock source-evidence and native-authority route must consume the committed config and patch.']};
fs.writeFileSync(path.join(out,'input-binding.json'),jsonBytes(report));
console.log(JSON.stringify({out,targets:targets.map(t=>({id:t.id,pixelIndex:t.pixelIndex,coverage_rows:t.coverage_rows.length})),requested_cells:rows.length,patch_rows:patchRows.length,selector:config.selector,physical_evidence:physicalEvidencePin}));
