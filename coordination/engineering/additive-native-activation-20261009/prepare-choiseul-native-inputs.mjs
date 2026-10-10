import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {SelectedGeometrySources} from '../../../scripts/check-effective-geographic-regression.mjs';
import {valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const demand=(value,message)=>{if(!value)throw Error(message);};
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const COMMIT='05895ecdf2e612deac1fcf1c86fb14796addca62';
const ANALYSIS='research/geography/melanesia-gap-batch-37ed51b2-20261009/vintages/choiseul-six-exact-003/analysis.json';
const ANALYSIS_SHA='08cd5edac8633ca4791b9e128f3d909fa041b30aac7f4cda6fb9c9e1be698229';
const TARGET='gb:SLB:ADM1:17018030B68013150931387';

// Diagnostic operands only. The fixed retained source-fit outcome can support
// a native evaluation, but is not an old pilot/Alaska authority or an activation
// permit. The surrounding issued reader must carry all returned metadata and
// source bytes until their actual final use; it enforces whole-member admission.
export function prepareChoiseulNativeInputs(snapshot) {
  const resolver=new SelectedGeometrySources(snapshot),reader=snapshot.reader;
  demand(snapshot.manifest.size===262166,'Actual canonical selected grid required');
  const analysis=reader.json(ANALYSIS,{version:COMMIT,expected:ANALYSIS_SHA});
  demand(analysis.schema==='melanesia-choiseul-six-source-fit/v3'&&analysis.cases.length===6
    &&analysis.current_atlas_context.target_id===TARGET,'Foreign retained six-case source outcome');
  const p=analysis.consumed_simplified_source,descriptor=reader.descriptor(p.path,COMMIT);
  demand(descriptor.mode==='100644'&&descriptor.bytes===p.compressed_bytes
    &&p.uncompressed_bytes===93632&&p.feature_count===10,'Whole original simplified source differs');
  const encoded=reader.read(p.path,{version:COMMIT,expected:p.compressed_sha256,decoded:p.uncompressed_bytes});
  const raw=gunzipSync(encoded,{maxOutputLength:p.uncompressed_bytes});
  demand(raw.length===p.uncompressed_bytes&&sha(raw)===p.uncompressed_sha256,'Whole simplified source inverse differs');
  const source=JSON.parse(raw),feature=source.features?.[p.feature_index];
  demand(source.features?.length===10&&feature&&valueSha(feature)===p.feature_sha256
    &&valueSha(feature.geometry)===p.geometry_sha256,'Complete original source feature identity differs');
  const current=resolver.read(analysis.current_atlas_context.target_path);
  const matches=current.collection.features.filter(f=>f.id===TARGET);
  demand(matches.length===1&&valueSha(matches[0].geometry)===analysis.current_atlas_context.target_geometry_sha256,
    'Selected current target changed from retained source-fit before state');
  const pixelIndex=snapshot.owners.findIndex(owner=>owner.id===TARGET)+1;
  demand(pixelIndex>0&&snapshot.owners.filter(owner=>owner.id===TARGET).length===1,'Missing/duplicate selected target owner');
  const cases=analysis.cases;
  demand(new Set(cases.map(c=>c.component_id)).size===6&&cases.every(c=>c.source_coverage_exact===true
    &&c.native_grid_recheck_required===true&&c.unique_recorded_subject_count===1
    &&c.source_product_geometry_sha256===p.geometry_sha256&&c.source_product_feature_sha256===p.feature_sha256
    &&c.unique_recorded_source_subject_id===TARGET&&valueSha(c.candidate_geometry)===c.component_geometry_sha256),
    'Retained complete source/candidate binding differs');
  return {scopeIds:cases.map(c=>c.component_id),
    sourceRows:cases.map(c=>({component_id:c.component_id,target_id:TARGET,pixelIndex,source_compatible:true})),
    candidates:cases.map(c=>({component_id:c.component_id,target_id:TARGET,pixelIndex,geometry:c.candidate_geometry})),
    custody:{analysis:{...reader.descriptor(ANALYSIS,COMMIT),sha256:ANALYSIS_SHA},
      original_source:{...descriptor,sha256:p.compressed_sha256,decoded_bytes:raw.length,decoded_sha256:sha(raw)},
      current_target:{source:current.source,whole_sha256:current.whole_sha256,geometry_sha256:valueSha(matches[0].geometry)},
      selected_owner:{id:TARGET,pixelIndex},selected_selection:snapshot.selection},
    limits:['Retained source coverage only; no supported additive policy or native activation authority is issued.',
      'Original 34-part continuous-neighbor evidence does not assert a new 36-part selected neighbor comparison.']};
}
