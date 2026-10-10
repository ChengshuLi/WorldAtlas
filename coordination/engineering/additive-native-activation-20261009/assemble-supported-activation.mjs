import {SelectedGeometrySources} from '../../../scripts/check-effective-geographic-regression.mjs';
import {additiveBaseReference} from '../../../src/effective-footprint.js';
import {nativeBaseSelection,requirePriorAdditiveConservation,reclaimCompletedRebindFrame,normaliseRetainedRepairLedger,readCurrentRebindCustody,valueBytes,valueSha}
  from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const demand=(value,message)=>{if(!value)throw Error(message);};
const safe=p=>typeof p==='string'&&!p.includes('\\')&&p.split('/').every(s=>s&&s!=='.'&&s!=='..');

// The existing trusted reader authenticates the complete current-bank product and
// reacquires their selected operands. This assembler never substitutes a
// producer boolean for that authority and never writes/selects any output.
export function assembleSupportedActivation({snapshot,registry,originalLedger,originalPatches,
  rebindPin,baseAssets,logicalPaths}) {
  reclaimCompletedRebindFrame();
  demand(baseAssets&&Object.keys(baseAssets).sort().join(',')==='base_manifest,owner_roster'
    &&logicalPaths&&Object.keys(logicalPaths).sort().join(',')==='ledger,patch'
    &&Object.values(logicalPaths).every(safe),'Exact base assets and two safe new logical paths required');
  const resolver=new SelectedGeometrySources(snapshot),reader=snapshot.reader;
  demand(snapshot.manifest.size===262166
    &&snapshot.manifest.provenance?.successor_continuation?.issue===1520,
    'Require actual selected Arctic successor');
  requirePriorAdditiveConservation(snapshot,registry,originalLedger);
  demand(rebindPin&&typeof rebindPin==='object'&&!Array.isArray(rebindPin),
    'Complete current-bank rebind certificate required');
  const actual=reader.descriptor(rebindPin.path,rebindPin.commit);
  demand(actual.mode===rebindPin.mode&&actual.git_blob_oid===rebindPin.git_blob_oid&&actual.bytes===rebindPin.bytes,
      'Cold certificate ordinary custody differs');
  const certificate=reader.json(rebindPin.path,{version:rebindPin.commit,expected:rebindPin.sha256});
  const rows=[...normaliseRetainedRepairLedger(originalLedger,registry).rows.values()];
  const carriedMetadataBytes=2*valueBytes({registry,originalLedger,originalPatches,rebindPin,certificate,baseAssets,logicalPaths,
    source_metadata:{bank:resolver.bank??null,paths:resolver.paths,sources:resolver.sources,release:resolver.release,
      image:resolver.image?{index:resolver.image.index,map:resolver.image.map}:null}}).length;
  const result=readCurrentRebindCustody(reader,rebindPin,{baseSelection:nativeBaseSelection(snapshot.selection),
    registry,originalRows:rows,originalPatches,size:snapshot.manifest.size,snapshot,
    carriedMetadataBytes});
  demand(result.native.assigned_cells>0,'No new native cells: do not publish an activation');
  const ledger={...originalLedger,current_rebind:rebindPin,current_targets:result.current_targets};
  for(const p of Object.values(baseAssets))demand(safe(p.path)&&Number.isSafeInteger(p.bytes)
    &&p.bytes>0&&p.bytes<=33554432&&/^[a-f0-9]{64}$/.test(p.sha256),'Complete bounded logical runtime asset required');
  const ledgerHash=valueSha(ledger);
  demand(baseAssets.base_manifest.sha256===snapshot.selection.sha256
    &&baseAssets.owner_roster.sha256===snapshot.manifest.original_assets.bounds.sha256,
    'Runtime asset differs from independently selected manifest/owner');
  const base_reference={id:snapshot.selection.release_id,footprints_sha256:resolver.release.footprints_sha256,
    hierarchy_sha256:resolver.release.hierarchy_sha256};
  const effectiveHash=valueSha({domain:'worldatlas-effective-native-footprints:v2',base_reference,
    authority_registry_sha256:valueSha(registry),ledger_sha256:ledgerHash,components:rows});
  const effective_reference={id:'geography:additive:'+effectiveHash,footprints_sha256:effectiveHash,
    hierarchy_sha256:base_reference.hierarchy_sha256};
  const patch={version:2,kind:'unassigned-native-cells-v1',authority_registry_sha256:valueSha(registry),
    base_reference,effective_reference,ledger_sha256:ledgerHash,rows:result.native.rows};
  const assetDescriptors={...baseAssets,...Object.fromEntries(Object.entries({ledger,patch}).map(([key,body])=>
    [key,{path:logicalPaths[key],bytes:valueBytes(body).length,sha256:valueSha(body)}]))};
  const envelope={version:2,kind:'retained-native-base-plus-delta-v2',base_reference,effective_reference,
    ...assetDescriptors};
  additiveBaseReference({additiveRelease:envelope,reference_release:effective_reference});
  return {ledger,patch,envelope,qualification:{rebind_certificate:rebindPin,
    complete_result_sha256:valueSha(result),assigned_cells:result.native.assigned_cells,
    components:rows.length,limits:['Ordinary output custody and committed sidecar authentication remain mandatory.',
      'These bodies do not change selection or approve physical authority.']}};
}
