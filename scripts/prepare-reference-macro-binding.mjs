// Compose existing macro proofs across an exact metadata-only reference change.
// Approval stays in its original scope; new release publication remains pending.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {gunzipSync,gzipSync} from 'node:zlib';
import {isDeepStrictEqual} from 'node:util';
import {footprintHash} from './check-prepared.mjs';
import {encodeEvidenceJSON} from './evidence/encode-json.mjs';
const sha=raw=>createHash('sha256').update(raw).digest('hex');
const encode=value=>encodeEvidenceJSON(value);
const read=file=>JSON.parse(file.endsWith('.gz')?gunzipSync(fs.readFileSync(file)):fs.readFileSync(file));
const macroTiers=['region','subcontinent','continent'];
export function prepareReferenceMacroBinding({data,before,after,release,receiptSha256}){
 const base=path.join(data,'macro-foundation'),files=new Map();
 const names=['macro-certificate.json','approved-boundary-decisions.json','review-index.json','regional-handoffs.json.gz'];
 const prior=Object.fromEntries(names.map(name=>[name,read(path.join(base,name))]));
 const hashes=Object.fromEntries(names.map(name=>[name,sha(fs.readFileSync(path.join(base,name)))]));
 const certificate=prior['macro-certificate.json'];
 if(certificate.status!=='approved'||certificate.publication_verified!==true||certificate.release.hierarchy_sha256!==before.proof.hierarchy_sha256||certificate.release.footprints_sha256!==before.proof.footprints_sha256||release.hierarchy_sha256!==after.proof.hierarchy_sha256||release.footprints_sha256!==after.proof.footprints_sha256)throw Error('Macro compatibility requires exact prior approved/published and candidate pins');
 const macros=after.units.filter(unit=>macroTiers.includes(unit.level));
 const original=new Map(certificate.groups.map(row=>[row.id,row]));
 if(macros.length!==116||original.size!==116||[...['continent','subcontinent','region']].some((tier,i)=>macros.filter(row=>row.level===tier).length!==[6,29,81][i]))throw Error('Macro inventory changed');
 const proofs=[];
 for(const unit of macros){
  const old=before.groups.get(unit.id),proof=original.get(unit.id),ids=[...after.members.get(unit.id)].sort(),oldIds=[...before.members.get(unit.id)].sort();
  if(!old||!proof||!['name','level','parent_id'].every(key=>old[key]===unit[key])||!isDeepStrictEqual(ids,oldIds)||proof.level!==unit.level||proof.parent_id!==unit.parent_id||proof.member_location_ids_sha256!==sha(JSON.stringify(ids)))throw Error('Macro conventions or descendant identities changed');
  const footprints=footprintHash(ids.map(id=>after.locations.get(id)));
  if(footprints!==proof.footprint_sha256)throw Error('Macro footprint differs from original approved proof');
  proofs.push({...proof,locations:ids.length});
 }
 const root=path.dirname(data),oldEnvelopeFile=path.resolve(root,certificate.envelopes_manifest_path);
 if(!oldEnvelopeFile.startsWith(base+path.sep)||sha(fs.readFileSync(oldEnvelopeFile))!==certificate.envelopes_manifest_sha256)throw Error('Approved envelope manifest changed');
 const envelope=read(oldEnvelopeFile),oldDirectory=path.dirname(oldEnvelopeFile),verificationFile=path.join(oldDirectory,'independent-verification.json'),verification=read(verificationFile);
 if(verification.verified!==true||verification.envelopes_manifest_sha256!==certificate.envelopes_manifest_sha256||verification.hierarchy_sha256!==before.proof.hierarchy_sha256||envelope.hierarchy_sha256!==before.proof.hierarchy_sha256||envelope.groups.length!==116)throw Error('Prior envelope verification differs');
 const envelopeDirectory=`macro-foundation/envelopes-v${release.version}`;
 if(fs.existsSync(path.join(data,envelopeDirectory)))throw Error('New envelope vintage already exists');
 const envelopeFiles=[];
 for(const row of envelope.groups){
  const proof=proofs.find(item=>item.id===row.id);
  if(!proof||row.member_location_ids_sha256!==proof.member_location_ids_sha256||row.locations!==proof.locations||path.isAbsolute(row.path)||row.path.split('/').includes('..'))throw Error('Envelope membership/path differs');
  const raw=fs.readFileSync(path.join(oldDirectory,row.path));
  if(sha(raw)!==row.sha256||sha(gunzipSync(raw,{maxOutputLength:32*1024*1024}))!==row.geometry_sha256)throw Error('Approved envelope bytes changed');
  files.set(envelopeDirectory+'/'+row.path,raw);
  envelopeFiles.push({path:path.relative(data,path.join(oldDirectory,row.path)),sha256:sha(raw),geometry_sha256:row.geometry_sha256});
 }
 const binding={version:1,kind:'unchanged-macro-reference-compatibility',correction_receipt_sha256:receiptSha256,before_release:certificate.release,after_release:release,prior_macro_files_sha256:hashes,groups:proofs,envelope_files:envelopeFiles,macro_conventions_changed:false,location_geometry_changed:false,named_land_routing_changed:false,original_approval_scope_retained:true,new_approval_created:false,regional_interiors_approved:false,location_attribute_imports_ready:false,published:false,prior_envelope_verification_sha256:sha(fs.readFileSync(verificationFile)),limits:['Exact existing member geometries and envelope bytes are reused; no new overlay measurement or source inspection.','Original macro reporting-convention approval is retained; no regional semantic, physical-precision or source-completeness approval.','Actual served release and matched Site verification remain designated-publisher work.']};
 const bindingName=`macro-foundation/reference-compatibility-v${release.version}.json.gz`;
 files.set(bindingName,encodeEvidenceJSON(binding,{gzip:true}));
 const envelopeIndex={...envelope,hierarchy_sha256:after.proof.hierarchy_sha256,reference_compatibility:{path:'data/'+bindingName,sha256:sha(files.get(bindingName)),prior_manifest_path:certificate.envelopes_manifest_path,prior_manifest_sha256:certificate.envelopes_manifest_sha256,measurement_repeated:false}};
 files.set(envelopeDirectory+'/envelope-index.json',encode(envelopeIndex));
 files.set(envelopeDirectory+'/independent-verification.json',encode({...verification,hierarchy_sha256:after.proof.hierarchy_sha256,envelopes_manifest_sha256:sha(files.get(envelopeDirectory+'/envelope-index.json')),method:'Existing independent overlay verification composed with exact unchanged macro memberships, member geometries and envelope bytes',prior_verification_sha256:binding.prior_envelope_verification_sha256,new_overlay_measurement:false,reference_compatibility_sha256:sha(files.get(bindingName))}));
 const decisions=structuredClone(prior['approved-boundary-decisions.json']);
 for(const row of decisions.groups){
  const ids=after.members.get(row.id);if(!ids)throw Error('Approved macro decision missing');
  const children=after.units.filter(unit=>unit.parent_id===row.id).map(unit=>unit.id).sort();
  for(const key of ['current_immediate_child_ids','candidate_immediate_child_ids','immediate_member_ids'])if(row[key])row[key]=children;
  row.location_count=ids.length;
  row.current_counts={locations:ids.length,area:0,province:0};
  for(const unit of after.units.filter(unit=>['area','province'].includes(unit.level))){let parent=unit.parent_id;while(parent){if(parent===row.id)row.current_counts[unit.level]++;parent=after.groups.get(parent).parent_id;}}
  if(row.current_area_members)row.current_area_members=after.units.filter(unit=>unit.level==='area'&&unit.parent_id===row.id).map(unit=>({id:unit.id,name:unit.name,locations:after.members.get(unit.id).length}));
 }
 const releasePins=Object.fromEntries(['id','version','hierarchy_sha256','footprints_sha256'].map(key=>[key,release[key]]));
 Object.assign(decisions,{release:releasePins,publication_verified:false,prior_decisions_sha256:hashes['approved-boundary-decisions.json'],reference_compatibility_path:'data/'+bindingName,reference_compatibility_sha256:sha(files.get(bindingName)),runtime_installation_required:true});
 files.set('macro-foundation/approved-boundary-decisions.json',encode(decisions));
 const nextCertificate={...certificate,status:'reference-compatible-pending-publication',release:releasePins,publication_verified:false,local_installation_verified:false,prior_certificate_sha256:hashes['macro-certificate.json'],boundary_decisions_sha256:sha(files.get('macro-foundation/approved-boundary-decisions.json')),envelopes_manifest_path:'data/'+envelopeDirectory+'/envelope-index.json',envelopes_manifest_sha256:sha(files.get(envelopeDirectory+'/envelope-index.json')),reference_compatibility_path:'data/'+bindingName,reference_compatibility_sha256:sha(files.get(bindingName)),publication_status_at_certificate_creation:'pending-designated-publisher-matched-release-and-site-readback',publication_receipt_path:null,new_approval_created:false,regional_interiors_approved:false};
 delete nextCertificate.local_installation_validation_sha256;
 nextCertificate.pending_publication_checkpoints=['Install reviewed metadata generation without changing location geometry or ownership','Publish and verify exact release, served lookup, inspector, parent boundaries and static/server pins','Verify preserved original claims and archives; keep regional interiors and location-attribute imports closed'];
 files.set('macro-foundation/macro-certificate.json',encode(nextCertificate));
 files.set('macro-foundation/review-index.json',encode({...prior['review-index.json'],current_release:releasePins,publication_verified:false,reference_compatibility_path:'data/'+bindingName,retained_source_inspection_context:true}));
 const handoffs=structuredClone(prior['regional-handoffs.json.gz']);
 Object.assign(handoffs,{release:releasePins,macro_certificate_sha256:sha(files.get('macro-foundation/macro-certificate.json')),publication_verified:false,reference_compatibility_path:'data/'+bindingName});
 for(const row of handoffs.regions){row.publication_verified=false;row.location_attribute_imports_ready=false;row.regional_interiors_approved=false;}
 files.set('macro-foundation/regional-handoffs.json.gz',encodeEvidenceJSON(handoffs,{gzip:true}));
 const gate=read(path.join(data,'research-geography-gate.json'));
 if(gate.ready_for_location_attributes!==false||gate.regions.length!==0)throw Error('Existing regional certificates require separately reviewed revalidation');
 gate.reason='Existing macro reporting conventions are unchanged; candidate reference correction release and matched Site publication await designated-publisher verification. No complete regional branches are approved; location-attribute imports remain closed.';
 gate.macro_boundaries={...gate.macro_boundaries,publication_verified:false,pending_release:releasePins,pending_macro_certificate_sha256:sha(files.get('macro-foundation/macro-certificate.json')),reference_compatibility_path:'data/'+bindingName,publication_status:'pending-reference-correction-release-and-site-verification'};
 files.set('research-geography-gate.json',encode(gate));
 return {files,binding};
}
