import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {validateMacroFoundation} from '../scripts/check-macro-foundation.mjs';
import {footprintHash} from '../scripts/check-prepared.mjs';
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
function fixture(){
 const hierarchy=[{id:'c',level:'continent',name:'C',parent_id:null},{id:'s',level:'subcontinent',name:'S',parent_id:'c'},...['r1','r2'].map(id=>({id,level:'region',name:id,parent_id:'s'})),...['a1','a2'].map((id,i)=>({id,level:'area',name:id,parent_id:`r${i+1}`})),...['p1','p2'].map((id,i)=>({id,level:'province',name:id,parent_id:`a${i+1}`}))];
 const locations=[1,2].map(i=>({id:`l${i}`,properties:{id:`l${i}`,parent_id:`p${i}`},geometry:{type:'Polygon',coordinates:[[[i,0],[i+.5,0],[i+.5,.5],[i,.5],[i,0]]]}}));
 const macros=hierarchy.filter(row=>['continent','subcontinent','region'].includes(row.level));
 const source={id:'source:a',url:'https://example.org/test-only-geography',sha256:'a'.repeat(64),status:200,inspected:true};
 const reviewIndex={version:1,input_hierarchy_sha256:'b'.repeat(64),coverage:{continents:1,subcontinents:1,regions:2,units:4},reports:[{}]};
 const ledgers=[{groups:structuredClone(macros),sources:[source]}];
 const decisions={version:1,scope:'macro-own-boundaries-only',groups:macros.map(row=>({...row,convention:'Synthetic reporting domain, not a measured physical divide',source_ids:[source.id],shared_edges:[],required_changes:[],status:'candidate'})),named_land_routing:[{name:'Absent test island',region_id:'r2',source_ids:[source.id],represented:false}]};
 const certificate={version:1,status:'candidate',release:{id:'release:a',version:3,hierarchy_sha256:sha(hierarchy),footprints_sha256:footprintHash(locations)},regional_interiors_approved:false,groups:macros.map(row=>{const members=row.level==='region'?locations.filter(feature=>feature.id===(row.id==='r1'?'l1':'l2')):locations;return {id:row.id,level:row.level,parent_id:row.parent_id,member_location_ids_sha256:sha(members.map(feature=>feature.id).sort()),footprint_sha256:footprintHash(members)};})};
 return {hierarchy,locations,reviewIndex,ledgers,decisions,certificate};
}
test('macro partition checks separate member coherence from source completeness and descendant approval',()=>{
 const result=validateMacroFoundation(fixture());assert.equal(result.macro_groups,4);assert.equal(result.locations,2);assert.deepEqual(result.unrepresented_named_land,['Absent test island']);assert.equal(result.regional_interiors_approved,false);assert.equal(result.shoreline_coverage_approved,false);assert.equal(result.immutable_dissolved_envelopes_verified,false);assert.equal(result.physical_boundary_precision_verified,false);
});
test('a structural pass cannot invent semantic approval or permit regional interiors',()=>{
 let input=fixture();input.certificate.status='approved';assert.throws(()=>validateMacroFoundation(input),/cannot create semantic approval/);
 input=fixture();input.certificate.regional_interiors_approved=true;assert.throws(()=>validateMacroFoundation(input),/interiors unapproved/);
 input=fixture();input.certificate.status='approved';input.certificate.approval_evidence='Independent test-only source decision';input.certificate.envelopes_manifest_sha256='e'.repeat(64);input.decisions.groups.forEach(row=>row.status='approved');assert.equal(validateMacroFoundation(input).status,'approved');
 input.decisions.groups[0].required_changes=['Unresolved shared edge'];assert.throws(()=>validateMacroFoundation(input),/cannot create semantic approval/);
});
test('each current macro identity and adjacent-tier parent must have exact decision and envelope coverage',()=>{
 for(const mutate of [input=>input.decisions.groups.pop(),input=>input.certificate.groups.pop(),input=>input.decisions.groups[0].name='Changed',input=>input.hierarchy.find(row=>row.id==='p1').parent_id='r1',input=>input.locations[0].properties.id='wrong',input=>input.decisions.groups.push({...input.decisions.groups[0]}),input=>input.reviewIndex.coverage.regions=1]){const input=fixture();mutate(input);assert.throws(()=>validateMacroFoundation(input));}
});
test('member and footprint hashes detect cross-region reassignment and geometry edits',()=>{
 let input=fixture();input.locations[0].properties.parent_id='p2';assert.throws(()=>validateMacroFoundation(input),/no location members|fingerprint differs/);
 input=fixture();input.certificate.groups[0].member_location_ids_sha256='e'.repeat(64);assert.throws(()=>validateMacroFoundation(input),/fingerprint differs/);
 input=fixture();input.locations[0].geometry.coordinates[0][1][0]+=.1;assert.throws(()=>validateMacroFoundation(input),/current location footprints/);
});
test('only inspected successful sources with URLs and reproducible hashes support boundary decisions',()=>{
 for(const mutate of [input=>input.ledgers[0].sources[0].status=403,input=>input.ledgers[0].sources[0].inspected=false,input=>input.ledgers[0].sources[0].sha256=null,input=>input.decisions.groups[0].source_ids=['unknown']]){const input=fixture();mutate(input);assert.throws(()=>validateMacroFoundation(input),/source evidence/);}
});
test('named missing islands receive explicit routing without imaginary geometry',()=>{
 const input=fixture();input.decisions.named_land_routing.push({name:'Represented island',region_id:'r1',source_ids:['source:a'],represented:true,location_ids:['l1']});assert.equal(validateMacroFoundation(input).named_land_routes,2);
 for(const mutate of [data=>data.decisions.named_land_routing[0].represented=true,data=>data.decisions.named_land_routing[0].location_ids=['l2'],data=>data.decisions.named_land_routing[0].region_id='missing',data=>data.decisions.named_land_routing[1].location_ids=['l2'],data=>data.decisions.named_land_routing.push({...data.decisions.named_land_routing[0]})]){const data={...input,decisions:structuredClone(input.decisions)};mutate(data);assert.throws(()=>validateMacroFoundation(data));}
});

test('supplemental boundary sources receive the same inspection and pin requirements as retained ledgers',()=>{
 const input=fixture();input.decisions.sources=[{id:'source:new',url:'https://example.org/new-source',sha256:'c'.repeat(64),status:200,inspected:true}];input.decisions.groups[0].source_ids=['source:new'];assert.equal(validateMacroFoundation(input).validated,true);
 for(const change of [{status:403},{inspected:false},{sha256:null},{url:'unverified-text'}]){const edited={...input,decisions:structuredClone(input.decisions)};Object.assign(edited.decisions.sources[0],change);assert.throws(()=>validateMacroFoundation(edited),/source evidence/);}
 const newlyRetrieved=fixture();newlyRetrieved.decisions.new_sources=[{id:'source:retrieved',url:'https://example.org/new-retrieval',sha256:'d'.repeat(64),http_status:200,retrieved_in_this_review:true}];newlyRetrieved.decisions.groups[0].source_ids=['source:retrieved'];assert.equal(validateMacroFoundation(newlyRetrieved).validated,true);
});

test('partial named-land evidence preserves existing geometry while explicitly withholding completeness',()=>{
 const input=fixture();input.decisions.named_land_routing[0].existing_location_ids=['l2'];input.decisions.named_land_routing[0].existing_locations_present=true;input.decisions.named_land_routing[0].coverage_status='Existing source polygon only; named family completeness unverified';assert.equal(validateMacroFoundation(input).shoreline_coverage_approved,false);
 for(const change of [{existing_locations_present:false},{coverage_status:''},{existing_location_ids:['l1']}]){const edited={...input,decisions:structuredClone(input.decisions)};Object.assign(edited.decisions.named_land_routing[0],change);assert.throws(()=>validateMacroFoundation(edited));}
});
