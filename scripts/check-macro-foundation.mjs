import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gunzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import {footprintHash} from './check-prepared.mjs';

const tiers=['continent','subcontinent','region','area','province','location'];
const macroTiers=tiers.slice(0,3);
const text=value=>typeof value==='string'&&value.trim().length>0;
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const digest=value=>sha(JSON.stringify(value));
const hash=value=>/^[a-f0-9]{64}$/.test(value??'');
const sameIds=(a,b)=>{const right=new Set(b);return a.length===b.length&&new Set(a).size===a.length&&right.size===b.length&&a.every(id=>right.has(id));};
const read=file=>{const raw=fs.readFileSync(file),bytes=file.endsWith('.gz')?gunzipSync(raw):raw;return {raw,bytes,document:JSON.parse(bytes)};};
const inventory=(rows,label)=>{if(!Array.isArray(rows)||rows.some(row=>!text(row?.id))||new Set(rows.map(row=>row.id)).size!==rows.length)throw Error(`Invalid or duplicate ${label} inventory`);return new Map(rows.map(row=>[row.id,row]));};
const groupsOf=ledger=>ledger.groups??[...(ledger.continents??[]),...(ledger.subcontinents??[]),...(ledger.regions??[])];

/** Mechanical publication checks; independent geographic judgment remains explicit. */
export function validateMacroFoundation({hierarchy,locations,reviewIndex,ledgers,decisions,certificate}){
 const units=inventory(hierarchy,'hierarchy'),features=inventory(locations,'location');
 const macros=new Map([...units].filter(([,unit])=>macroTiers.includes(unit.level??unit.kind)));
 if([...units.values()].some(unit=>!tiers.slice(0,-1).includes(unit.level??unit.kind)))throw Error('Hierarchy contains unsupported geographic tiers');
 if(!reviewIndex||reviewIndex.version!==1||!hash(reviewIndex.input_hierarchy_sha256)||!Array.isArray(ledgers)||ledgers.length!==reviewIndex.reports?.length)throw Error('Incomplete macro review index/ledger inventory');
 const original=inventory(ledgers.flatMap(groupsOf),'original macro ledger');
 for(const [level,key] of [['continent','continents'],['subcontinent','subcontinents'],['region','regions']])if([...original.values()].filter(row=>row.level===level).length!==reviewIndex.coverage?.[key])throw Error(`Review index ${key} differs from ledger inventory`);
 if(original.size!==reviewIndex.coverage?.units)throw Error('Review index total differs from ledger inventory');
 const decisionDocuments=Array.isArray(decisions)?decisions:[decisions];
 if(decisionDocuments.some(doc=>doc?.version!==1||doc.scope!=='macro-own-boundaries-only'))throw Error('Boundary decisions must explicitly cover macro own boundaries only');
 const sources=new Map();
 for(const ledger of [...ledgers,...decisionDocuments])for(const source of [...(ledger.sources??[]),...(ledger.new_sources??[]),...(ledger.retained_sources??[])]){
  const inspected=source.inspected===true||source.retrieved_in_this_review===true;
  if(!inspected||(source.status??source.http_status)!==200||!hash(source.sha256)||!/^https?:\/\//.test(source.url??''))continue;
  if(!text(source.id))throw Error('Inspected source lacks identity');
  if(!sources.has(source.id))sources.set(source.id,[]);sources.get(source.id).push(source);
  if((ledger.retained_sources??[]).includes(source))sources.set(`retained:${source.id}`,[source]);
 }
 const checkSources=ids=>{if(!Array.isArray(ids)||!ids.length||ids.some(id=>!sources.has(id)))throw Error('Boundary convention cites missing, uninspected or unpinned source evidence');};
 const selected=inventory(decisionDocuments.flatMap(doc=>doc.groups??[]),'macro boundary decision');
 if(!sameIds([...selected.keys()],[...macros.keys()]))throw Error('Every current macro group requires exactly one boundary decision');
 const members=new Map([...units.keys()].map(id=>[id,[]])),regionOf=new Map();
 for(const feature of features.values()){
  const props=feature.properties;
  if(!props||props.id!==feature.id||!['Polygon','MultiPolygon'].includes(feature.geometry?.type))throw Error('Locations require stable polygon identities');
  let parent=props.parent_id;
  for(let tier=tiers.length-2;tier>=0;tier--){const group=units.get(parent);if((group?.level??group?.kind)!==tiers[tier])throw Error('Incomplete adjacent-tier location parent chain');members.get(parent).push(feature.id);if(tiers[tier]==='region')regionOf.set(feature.id,parent);parent=group.parent_id;}
  if(parent!==null)throw Error('Continent cannot have a parent');
 }
 for(const [id,unit] of units){
  const level=unit.level??unit.kind,tier=tiers.indexOf(level);
  if(!members.get(id).length)throw Error('Active geographic group has no location members');
  if(tier===0?unit.parent_id!==null:(units.get(unit.parent_id)?.level??units.get(unit.parent_id)?.kind)!==tiers[tier-1])throw Error('Incomplete adjacent-tier group parent chain');
  if(macroTiers.includes(level)){
   const decision=selected.get(id);
   if(decision.level!==level||decision.parent_id!==unit.parent_id||decision.name!==unit.name||!text(decision.convention)||!Array.isArray(decision.shared_edges)||!Array.isArray(decision.required_changes)||!['candidate','approved'].includes(decision.status))throw Error(`Macro decision is missing or stale: ${id}`);
   checkSources(decision.source_ids);
  }
 }
 if(!certificate||certificate.version!==1||!['candidate','approved'].includes(certificate.status)||certificate.regional_interiors_approved!==false||!text(certificate.release?.id)||!Number.isSafeInteger(certificate.release.version)||!hash(certificate.release.hierarchy_sha256)||!hash(certificate.release.footprints_sha256))throw Error('Macro certificate must pin a release and leave regional interiors unapproved');
 if(certificate.release.footprints_sha256!==footprintHash(locations))throw Error('Certificate does not match the current location footprints');
 const envelopes=inventory(certificate.groups,'macro envelope certificate');
 if(!sameIds([...envelopes.keys()],[...macros.keys()]))throw Error('Macro envelope certificate must cover every current macro group');
 for(const [id,unit] of macros){
  const row=envelopes.get(id),ids=members.get(id).sort(),footprints=ids.map(member=>features.get(member));
  if(row.member_location_ids_sha256!==digest(ids)||row.footprint_sha256!==footprintHash(footprints))throw Error(`Macro envelope fingerprint differs from its member locations: ${id}`);
  // Every parent footprint is defined from the disjoint descendant partition.
  const children=[...units.values()].filter(child=>child.parent_id===id),combined=children.flatMap(child=>members.get(child.id));
  if(!sameIds(combined,ids))throw Error('Parent membership differs from the disjoint union of its children');
  if(row.level!==undefined&&row.level!==(unit.level??unit.kind)||row.parent_id!==undefined&&row.parent_id!==unit.parent_id)throw Error('Stale macro envelope identity');
 }
 const routing=decisionDocuments.flatMap(doc=>doc.named_land_routing??[]),routeNames=new Set();
 for(const route of routing){
  if(!text(route.name)||routeNames.has(route.name)||(macros.get(route.region_id)?.level??macros.get(route.region_id)?.kind)!=='region'||typeof route.represented!=='boolean')throw Error('Named land requires one explicit region routing certificate');
  routeNames.add(route.name);checkSources(route.source_ids);
  const ids=route.location_ids??route.represented_location_ids??route.existing_location_ids??(route.location_id?[route.location_id]:[]);
  if(!Array.isArray(ids)||new Set(ids).size!==ids.length||ids.some(id=>regionOf.get(id)!==route.region_id))throw Error('Named land routing has missing or conflicting represented locations');
  if(route.represented&&ids.length===0)throw Error('Represented named land requires an explicit matching location inventory');
  if(!route.represented&&ids.length!==0&&(route.existing_locations_present!==true||![route.coverage_status,route.representation_precision,route.representation_note].some(text)))throw Error('Partial named land requires explicit existing-location presence and a coverage limitation; absent land cannot claim geometry');
 }
 if(certificate.status==='approved'&&(!hash(certificate.envelopes_manifest_sha256)||!text(certificate.approval_evidence)||[...selected.values()].some(row=>row.status!=='approved'||row.required_changes.length)))throw Error('Membership checks cannot create semantic approval; independent boundary decisions and approval evidence are required');
 return {validated:true,status:certificate.status,macro_groups:macros.size,locations:features.size,named_land_routes:routing.length,unrepresented_named_land:routing.filter(row=>!row.represented).map(row=>row.name),regional_interiors_approved:false,shoreline_coverage_approved:false,physical_boundary_precision_verified:false,immutable_dissolved_envelopes_verified:false,limitation:'Member footprint fingerprints verify the declared represented-land partition. They do not measure missing shorelines, physical divides, polygon overlaps or immutable dissolved envelopes after interior geometry changes.'};
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const args=process.argv.slice(2),values=new Map();for(let i=0;i<args.length;i+=2){if(!args[i+1])throw Error('Supply --data, --review-index, --certificate and repeated --decisions files');const key=args[i];if(!values.has(key))values.set(key,[]);values.get(key).push(args[i+1]);}
 const data=values.get('--data')?.[0]??'data',reviewFile=values.get('--review-index')?.[0]??'data/macro-foundation/review-index.json',certificateFile=values.get('--certificate')?.[0];
 if(!certificateFile||!values.get('--decisions')?.length)throw Error('Supply --certificate and repeated --decisions files');
 const hierarchy=read(path.join(data,'hierarchy.json')),world=read(path.join(data,'world-index.json')).document,locations=world.parts.flatMap(part=>read(path.join(data,part)).document.features),reviewIndex=read(reviewFile).document,certificate=read(certificateFile).document;
 const ledgers=reviewIndex.reports.map(report=>{const file=path.resolve(report.path),loaded=read(file);if(sha(loaded.raw)!==report.sha256||sha(loaded.bytes)!==report.raw_sha256)throw Error('Macro review ledger bytes changed');return loaded.document;});
 if(certificate.release?.hierarchy_sha256!==sha(hierarchy.raw))throw Error('Macro certificate hierarchy byte pin does not match prepared hierarchy');
 const envelopeFile=values.get('--envelopes')?.[0];if(certificate.status==='approved'&&!envelopeFile)throw Error('Approved macro certificate requires a pinned immutable envelope manifest');if(envelopeFile&&sha(fs.readFileSync(envelopeFile))!==certificate.envelopes_manifest_sha256)throw Error('Immutable envelope manifest bytes do not match the certificate');
 console.log(JSON.stringify(validateMacroFoundation({hierarchy:hierarchy.document,locations,reviewIndex,ledgers,decisions:values.get('--decisions').map(file=>read(file).document),certificate}),null,2));
}
