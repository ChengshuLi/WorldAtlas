import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {deriveSourceTargetNativeDelta,nativeRowLatitudes,nativePolygonIntervals,polygonParts} from '../src/native-grid.js';
import {ImmutableReader} from '../scripts/check-effective-geographic-regression.mjs';
import {constructOriginalAuthority} from '../scripts/delivery-handoff-advance.mjs';
import {diagnoseSourceTargetNativeAuthority} from '../coordination/engineering/selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';

const rectangle=(left,right,bottom=-40,top=40)=>({type:'Polygon',coordinates:[[[left,bottom],[right,bottom],[right,top],[left,top],[left,bottom]]]});
const feature=(id,pixelIndex,geometry,target_id)=>({id,pixelIndex,geometry,...(target_id?{target_id}:{})});
const version='a'.repeat(40),family='gb:TST:ADM2',a=family+':A',b=family+':B',c=family+':C';
const size=262166,latitudes=nativeRowLatitudes(size),latitudeBytes=Buffer.alloc(size*8);
for(let i=0;i<size;i++)latitudeBytes.writeDoubleLE(latitudes[i],i*8);
const digest=raw=>createHash('sha256').update(raw).digest('hex');
const blob=raw=>createHash('sha1').update(`blob ${raw.length}\0`).update(raw).digest('hex');
const collection=features=>({type:'FeatureCollection',features});
const rawFeature=(id,geometry)=>({type:'Feature',properties:{shapeID:id},geometry});
function constructorFixture(change=()=>{}){
  const first=rectangle(-.03,.006,-.02,.02),second=rectangle(.004,.03,-.02,.02);
  const cityGeometry={type:'MultiPolygon',coordinates:[first.coordinates,second.coordinates]};
  const direct=rectangle(.015,.06,-.02,.02);
  const state={originals:[rawFeature('A',first),rawFeature('B',second),rawFeature('C',direct)],
    roster:[{id:'city',index:1},{id:c,index:2},{id:'other-city',index:3}],
    lineage:{changes:[{id:'city',replaces:[a,b]},{id:'irrelevant-split-1',replaces:['unrelated']},{id:'irrelevant-split-2',replaces:['unrelated']}]},
    index:{parts:['geography/part-0.json']},
    accepted:collection([{type:'Feature',id:'city',geometry:cityGeometry,properties:{metadata:{source_member_ids:[a,b]}}}]),
    targets:[{id:a,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']},
      {id:b,target_id:'city',pixelIndex:1,source_family:family,base_geometry:cityGeometry,coverage_classes:['mapped_land_support']}],
    physical:{results:[{target:a,issues:[],support:{mapped_land_support:first}},{target:b,issues:[],support:{mapped_land_support:second}}]},
    measured:[{target:a,consumed:{geometry:first},selected:{id:'city',geometry:cityGeometry}},
      {target:b,consumed:{geometry:second},selected:{id:'city',geometry:cityGeometry}}],
    proposed:{rows:[{y:size/2,runs:[[Math.floor(size/2-.02/360*size),Math.floor(size/2-.02/360*size)+1,1]]}]},
    membership:true};
  change(state);
  const files=new Map(),byBlob=new Map();
  const put=(name,value)=>{
    const raw=Buffer.isBuffer(value)?value:Buffer.from(JSON.stringify(value));
    const pin={commit:version,path:name,mode:'100644',git_blob_oid:blob(raw),bytes:raw.length,sha256:digest(raw)};
    files.set(name,{raw,pin});byBlob.set(pin.git_blob_oid,raw);return pin;
  };
  const source=put('original-source.json',collection(state.originals)),roster=put('owners.json',state.roster);
  const physical=put('physical.json',state.physical),measured=put('measured.json',state.measured);
  const catalogue=put('coordination/engineering/original-geography-source-corpus-20261006/catalogue.json',{
    products:[{key:family,parts:[{path:source.path,bytes:source.bytes,sha256:source.sha256}],
      feature_count:state.originals.length,original_bytes:source.bytes,original_sha256:source.sha256}]});
  const nativeLatitudes=put('latitudes.f64le',latitudeBytes);
  const membership={index:put('data/world-index.json',state.index),lineage:put('data/semantic-report.json',state.lineage),
    parts:[put('data/geography/part-0.json',state.accepted)]};
  const evidence=put('source-evidence.json',{version:1,kind:'source-target-native-evidence-v1',catalogue,
    owner_roster:roster,physical_evidence:physical,physical_input:measured,physical_reproduction:put('physical.py',Buffer.from('# retained fixture')),
    native_latitudes:nativeLatitudes,native_contract:{size,native_latitudes:nativeLatitudes,original_assets:{bounds:{sha256:roster.sha256}}},
    base_reference:{id:'fixture-base'},families:[{source_id:family,parts:[source]}],
    targets:state.targets.map(target=>({...target,source_receipt_sha256:physical.sha256})),
    ...(state.membership?{source_membership:membership}:{})});
  const patch=put('patch.json',state.proposed);
  class FixtureReader extends ImmutableReader{
    git(...args){
      if(args[0]==='ls-tree'){
        const name=args.at(-1),entry=files.get(name);assert.ok(entry,name);
        return Buffer.from(`100644 blob ${entry.pin.git_blob_oid}\t${name}\0`);
      }
      if(args[0]==='cat-file'&&args[1]==='-e')return Buffer.alloc(0);
      if(args[0]==='cat-file'&&args[1]==='-s')return Buffer.from(String(byBlob.get(args[2]).length));
      if(args[0]==='cat-file'&&args[1]==='blob')return byBlob.get(args[2]);
      throw Error('Unexpected fixture Git request: '+args.join(' '));
    }
  }
  const reader=()=>new FixtureReader('.',version);
  const locators={source_evidence:{commit:version,path:evidence.path},native_patch:{commit:version,path:patch.path}};
  const binding={version:1,kind:'source-target-native-custody-v1',source_evidence:evidence,native_patch:patch};
  const preimage={...binding,kind:'source-target-native-rule-v1'};
  return {run:()=>constructOriginalAuthority(reader(),locators),
    diagnose:()=>diagnoseSourceTargetNativeAuthority(reader(),preimage,binding),files,byBlob,membership,reader,state};
}
function directTarget(state,{membership=true,overlap=false}={}){
  const geometry=state.originals[2].geometry;
  state.targets=[{id:c,pixelIndex:2,source_family:family,base_geometry:geometry,coverage_classes:['mapped_land_support']}];
  state.physical.results=[{target:c,issues:[],support:{mapped_land_support:geometry}}];
  state.measured=[{target:c,consumed:{geometry},selected:{id:c,geometry}}];
  const x=Math.floor(size/2+(overlap?.02:.05)/360*size);
  state.proposed.rows=[{y:size/2,runs:[[x,x+1,2]]}];state.membership=membership;
  if(!membership)state.originals[2].geometry=rectangle(.04,.06,-.02,.02);
}
function splitCompetitorFixture(change=()=>{}) {
  return constructorFixture(state=>{
    directTarget(state);
    state.originals[0].geometry=rectangle(.015,.035,-.02,.02);
    state.originals[1].geometry=rectangle(-.06,-.05,-.02,.02);
    state.roster.push({id:b,index:4});
    state.roster[0].province_id='province:left';
    state.roster[2].province_id='province:right';
    const basis='Published geographic subdivision within a source rural district';
    const source='https://example.org/retained-subdivision';
    state.lineage.changes=['city','other-city'].map(id=>({id,replaces:[a],basis,source}));
    state.accepted.features=['city','other-city'].map((id,i)=>({type:'Feature',id,
      geometry:rectangle(.015+i*.01,.025+i*.01,-.02,.02),properties:{id,
        parent_id:i?'province:right':'province:left',metadata:{source_member_ids:[a],
          original_id:'A',location_basis:basis,source_url:source}}}));
    change(state);
  });
}

const outcome=[];
function probe(name,change,expected){
 const f=splitCompetitorFixture(s=>{s.targets[0].territorial_exclusions=[s.originals[0].geometry];change(s);});
 let result;try{result={pass:true,cells:f.run().ledger_rows[0].native_cells};}catch(e){result={pass:false,error:e.message};}
 if(expected===null)assert.equal(result.pass,true);else assert.match(result.error,expected);
 outcome.push({name,result});
}
probe('supported simple split with whole original exclusion',(s)=>{},null);
probe('coherent multi-member descendants with whole original exclusion',s=>{
 const d=family+':D';s.originals.push(rawFeature('D',rectangle(.016,.018,-.02,.02)));
 for(const c of s.lineage.changes)c.replaces=[a,d];
 for(const f of s.accepted.features)f.properties.metadata.source_member_ids=[a,d];
},/Incomplete or ambiguous accepted split-source descendant/);
probe('missing descendant lineage cannot be bypassed by whole exclusion',s=>s.lineage.changes.pop(),/Incomplete accepted split-source descendant inventory/);
probe('no membership cannot be bypassed by whole exclusion',s=>s.membership=false,/Missing or ambiguous accepted source membership/);
console.log(JSON.stringify({kind:'stock-constructor-territorial-exclusion-route-controls',cases:outcome,limits:['Synthetic authenticated Git-transport fixtures exercise the actual unmodified constructOriginalAuthority entry point. They establish representation/guard behavior, not qualification of Canada cells.']},null,2));
