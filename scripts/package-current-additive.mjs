// Ordinary packaging consumes accepted current products. Original authority and
// native/source qualification stay in the explicit preparation/regression path.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {containsPackagePath,loadPackageInputs,safePackagePath} from './package-inputs.mjs';
import {additiveBaseReference,bindAdditiveLedgerFeatures,verifyAdditiveLedgerSelection,additiveReleaseFootprintDigest,validateAdditivePatchFormat} from '../src/effective-footprint.js';
import {scientificNativeSelection,validateReferenceMetadataHeader,projectReferenceOwners,assertAppliedReferenceProperties} from '../src/reference-metadata.js';

const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const need=(ok,message)=>{if(!ok)throw Error(message);};
export async function prepareCurrentSelectedAdditive({root,selectedGrid,geographicRelease,features}) {
  root=await fs.realpath(root);
  const selectionFile=path.join(root,'data/ownership-selection.json'),selectionStat=await fs.lstat(selectionFile);
  need(selectionStat.isFile()&&await fs.realpath(selectionFile)===selectionFile,'Current selection must be ordinary');
  const selection=JSON.parse(await fs.readFile(selectionFile));
  if(selection.additive_release===undefined)return null;
  const definition=loadPackageInputs(root),inputInventory=[];
  async function read(pin){
    need(pin&&safePackagePath(pin.path)&&!pin.path.endsWith('/')&&containsPackagePath(definition.inputs,pin.path),'Undeclared current additive input');
    const file=path.join(root,pin.path),stat=await fs.lstat(file);
    need(stat.isFile()&&await fs.realpath(file)===file&&Number.isSafeInteger(pin.bytes)&&stat.size===pin.bytes,'Current additive whole length or ordinary path differs');
    const raw=await fs.readFile(file);
    need(raw.length===pin.bytes&&sha(raw)===pin.sha256,'Current additive whole checksum differs');
    if(pin.mode!==undefined)need(pin.mode===((stat.mode&0o111)?'100755':'100644'),'Current additive mode differs');
    const oid=createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex');
    if(pin.git_blob_oid!==undefined)need(oid===pin.git_blob_oid,'Current additive Git object differs');
    inputInventory.push({...pin,mode:(stat.mode&0o111)?'100755':'100644',git_blob_oid:oid,bytes:raw.length,sha256:sha(raw),whole_body_consumed:true});
    return raw;
  }
  const sidecar=JSON.parse(await read(selection.additive_release));
  need(sidecar.version===2&&sidecar.kind==='retained-native-additive-selection-v2','Unsupported current additive selection');
  const baseSelection=scientificNativeSelection(selection);
  need(isDeepStrictEqual(sidecar.base_selection,baseSelection),'Current additive selection belongs to a different native base');
  let projection,referenceMetadata,projectionAsset;
  if(selection.reference_projection!==undefined){
    // Preparation authenticated the receipt/source closure. Ordinary packaging
    // binds this accepted whole product to original N and current metadata M.
    const raw=await read(selection.reference_projection);
    projection=JSON.parse(raw);
    const {native,reference}=validateReferenceMetadataHeader(projection,{selection,manifest:selectedGrid.manifest});
    need(isDeepStrictEqual(reference,Object.fromEntries(['id','footprints_sha256','hierarchy_sha256'].map(key=>[key,geographicRelease[key]]))),
      'Current reference metadata differs from selected geographic release');
    const asset={path:'reference-metadata/current.json',bytes:raw.length,sha256:sha(raw)};
    referenceMetadata={version:1,asset,native_reference:native,reference};
    projectionAsset={path:asset.path,raw};
  }
  const wrapped=JSON.parse(await read(sidecar.runtime_envelope)),envelope=wrapped.additiveRelease??wrapped;
  const base=additiveBaseReference({additiveRelease:envelope,reference_release:envelope.effective_reference});
  need(isDeepStrictEqual(base,Object.fromEntries(['id','footprints_sha256','hierarchy_sha256'].map(key=>[key,geographicRelease[key]])))&&envelope.effective_reference.hierarchy_sha256===base.hierarchy_sha256,'Current additive reference differs from selected base');
  need(selection.sha256===selectedGrid.sha256&&selection.release_id===(referenceMetadata?.native_reference.id??geographicRelease.id),'Current additive native selection differs');
  need(Object.keys(sidecar.logical_asset_map??{}).sort().join(',')==='base_manifest,ledger,owner_roster,patch','Incomplete current additive asset roster');
  const assets=projectionAsset?[projectionAsset]:[],decoded={};
  for(const role of ['base_manifest','ledger','owner_roster','patch']){
    const pin=sidecar.logical_asset_map[role],logical=envelope[role];
    need(pin.bytes===logical.bytes&&pin.sha256===logical.sha256&&(pin.decoded_bytes??pin.bytes)===(logical.decoded_bytes??logical.bytes)&&(pin.decoded_sha256??pin.sha256)===(logical.decoded_sha256??logical.sha256),'Current additive logical/source binding differs: '+role);
    const raw=await read(pin);assets.push({path:logical.path,raw});
    let body=raw;
    if(logical.encoding==='gzip'){
      body=gunzipSync(raw,{maxOutputLength:logical.decoded_bytes+1});
      need(body.length===logical.decoded_bytes&&sha(body)===logical.decoded_sha256,'Current additive decoded identity differs');
    }
    decoded[role]=JSON.parse(body);
  }
  need(envelope.base_manifest.sha256===selectedGrid.sha256&&isDeepStrictEqual(decoded.base_manifest,selectedGrid.manifest),'Current additive base manifest differs');
  need(envelope.owner_roster.sha256===selectedGrid.manifest.original_assets.bounds.sha256&&assets.find(asset=>asset.path===envelope.owner_roster.path).raw.equals(selectedGrid.bounds),'Current additive owner roster differs from independently selected bounds');
  const originalOwners=decoded.owner_roster;
  const owners=projection?projectReferenceOwners(originalOwners,projection.location_changes,projection.provinces):originalOwners;
  need(Array.isArray(owners)&&owners.length===features.length,'Incomplete current additive owners');
  const byId=new Map(features.map(feature=>[feature.id,feature])),indices=new Set(),ids=new Set();
  for(const owner of owners){const feature=byId.get(owner.id);need(feature&&!ids.has(owner.id)&&Number.isSafeInteger(owner.index)&&owner.index>0&&!indices.has(owner.index)&&feature.pixelIndex===owner.index&&feature.properties.parent_id===owner.province_id,'Current additive owner identity or parent differs');ids.add(owner.id);indices.add(owner.index);}
  for(const change of projection?.location_changes??[])assertAppliedReferenceProperties(byId.get(change.location_id)?.properties,change.after_properties);
  const patch=decoded.patch,ledger=decoded.ledger;
  need(patch.kind==='unassigned-native-cells-v1'&&[1,2].includes(patch.version)&&isDeepStrictEqual(patch.base_reference,base)&&isDeepStrictEqual(patch.effective_reference,envelope.effective_reference)&&patch.ledger_sha256===envelope.ledger.sha256,'Current additive patch source/ledger differs');
  validateAdditivePatchFormat(patch,selectedGrid.manifest.size);
  need(patch.rows.every(row=>row.runs.every(run=>indices.has(run[2]))),'Current additive patch contains a foreign owner');
  const effective=bindAdditiveLedgerFeatures(features,ledger,envelope,base);
  verifyAdditiveLedgerSelection(ledger,effective,patch);
  need(additiveReleaseFootprintDigest(base,effective)===envelope.effective_reference.footprints_sha256,'Current additive effective footprint differs');
  return {selection,input_inventory:inputInventory,additiveRelease:envelope,reference_release:envelope.effective_reference,
    ...(referenceMetadata?{referenceMetadata}:{}),
    async publish(destination){
      const target=path.resolve(destination);
      for(const asset of assets){
        const file=path.join(target,asset.path);
        for(let parent=path.dirname(file);;parent=path.dirname(parent)){
          const stat=await fs.lstat(parent).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
          need(!stat||stat.isDirectory()&&!stat.isSymbolicLink(),'Current additive destination must be ordinary');
          if(parent===path.dirname(parent))break;
        }
        const present=await fs.lstat(file).catch(error=>{if(error.code==='ENOENT')return null;throw error;});
        need(!present,'Current additive destination already exists');
      }
      for(const asset of assets){const file=path.join(destination,asset.path);await fs.mkdir(path.dirname(file),{recursive:true});await fs.writeFile(file,asset.raw,{flag:'wx'});}
    }};
}
