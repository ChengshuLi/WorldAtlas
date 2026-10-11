"""Read exact retained originals from Git; run only the changed JSON join boundaries.
No output files, original mutation, native computation or source approval.
"""
import base64, hashlib, json, pathlib, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[3]
NOR = 'f3c8ecddff787f33e2b07de1fa36f4365abfc9df'
COD = '3853d5a5a10acd5012bc92cb0261765d8117dc02'
NP = 'research/geography/norway31-source-fit-20261011/'
CP = 'research/geography/gap-source-angola-drc-shared-seams-20261006/'
pins = []
def read(commit, path):
    size = int(subprocess.check_output(['git', '-C', str(ROOT), 'cat-file', '-s', commit + ':' + path]))
    assert 0 < size <= 32 * 1024 * 1024
    assert sum(pin['bytes'] for pin in pins) + size <= 256 * 1024 * 1024
    body = subprocess.check_output(['git', '-C', str(ROOT), 'show', commit + ':' + path])
    assert len(body) == size
    pins.append(dict(commit=commit, path=path, bytes=len(body), sha256=hashlib.sha256(body).hexdigest()))
    assert sum(pin['bytes'] for pin in pins) <= 256 * 1024 * 1024
    return body

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False) + '\n').encode()
def binding(value, kind):
    body = canonical(value)
    return {kind + '_sha256': hashlib.sha256(body).hexdigest(), kind + '_bytes_base64': base64.b64encode(body).decode()}

scope = json.loads(read(NOR, NP + 'vintages/source-premise-input-001/premise-input.json'))
cid = 'physical-component:9870535a638523dd87ea5eaf44ab2f0db3d12cba27db6c31a33773e669cf4215'
case = next(row for row in scope['candidate_source_native_bindings'] if row['component_id'] == cid)
geometry = binding(case['original_candidate_feature']['geometry'], 'geometry')
record = next(row for row in scope['original_physical_comparison_bindings'] if row['component_id'] == cid)['physical_comparison']['row']
assert geometry['geometry_sha256'] == record['candidate_geometry_sha256']
products = []
for commit, path, ordinal, expected_body, expected_feature, expected_geometry in [
    (NOR, NP + 'sources/administrative/gb-NOR-ADM2-consumed-simplified.geojson', 128,
     'ab294b0b1dadfb937daa07963aa5995544fd8a16a6c9eb6261a82bb66401d90e',
     'db4fcd8531dc5931884db4d0657fdec34db43aae6fa4d6869b7b957bda0a2d27',
     '3bc1da72053faad31bc2b427ca756e7ead13839beaadfc78bcfffe4162e215ef'),
    (COD, CP + 'sources/administrative/gb-AGO-ADM2-ADM2-consumed-simplified.geojson', 120,
     '7cf2a401b36480f7c22d9783e4364d3eb93c3ac643e2d34778b1ce059c786dcf',
     '3d0a03658cfff30847d0268e18842918cd5a20d2cbda7e5c0330a2546147b0f0',
     'fa622c83f7ee36fdb6c4cb300f47f6fa887c7c8fedead76834b9bd314f71badc')]:
    body = read(commit, path)
    assert hashlib.sha256(body).hexdigest() == expected_body
    feature = json.loads(body)['features'][ordinal]
    alias = dict(source_path=path, source_sha256=expected_body, feature_index=ordinal,
                 **binding(feature, 'feature'), **binding(feature['geometry'], 'geometry'))
    assert alias['feature_sha256'] == expected_feature and alias['geometry_sha256'] == expected_geometry
    products.append(dict(body_base64=base64.b64encode(body).decode(), binding=alias))
# Complete retained bodies go directly to the changed actual exported helpers.
runner = r'''
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {originalAdministrativeProductFeatures,originalAdministrativeProductMatch,retainedAdministrativeSourcePremises,validateAdministrativeNativeCase} from './scripts/additive-gap-repair.mjs';
import {footprintValueSha256 as digest} from './src/effective-footprint.js';
const {scope,cid,geometry,products,pins}=JSON.parse(fs.readFileSync(0,'utf8'));
const c=scope.candidate_source_native_bindings.find(r=>r.component_id===cid);
const record=scope.original_physical_comparison_bindings.find(r=>r.component_id===cid).physical_comparison.row;
const target=scope.current_neighbor_binding.rows.find(r=>r.component_id===cid).candidate_neighbors.find(r=>r.feature.id===c.retained_payload.target_stable_location_id).feature;
const args={record,candidate:c.original_candidate_feature.geometry,sourceCase:c,sourceScope:scope,target};
const before=retainedAdministrativeSourcePremises(args);
assert.deepEqual(before.failed_premises,['original-full-candidate-binding']);
Object.assign(scope.original_candidate_canonical_bindings.find(r=>r.component_id===cid),geometry,{derived_js_geometry_canonical_sha256:digest(args.candidate)});
const after=retainedAdministrativeSourcePremises(args);assert.equal(after.source_compatible,true);
const native={selected:{...after,candidate:args.candidate,pixelIndex:1,target_geometry_sha256:digest(target.geometry)},sourceCase:c,sourceScope:scope,target,owner:{id:target.id,index:1,province_id:target.properties.parent_id},geometryScope:'full-component'};
assert.equal(validateAdministrativeNativeCase(native).source_compatible,true);
const changed=structuredClone(args);changed.candidate.coordinates[0][1][0]+=0.01;
changed.sourceCase.original_candidate_feature.geometry=changed.candidate;
changed.sourceScope.original_candidate_canonical_bindings.find(r=>r.component_id===cid).derived_js_geometry_canonical_sha256=digest(changed.candidate);
assert(retainedAdministrativeSourcePremises(changed).failed_premises.includes('original-full-candidate-binding'));
const results=[];
for(const input of products){
 const body=Buffer.from(input.body_base64,'base64'),binding=input.binding,pin={path:binding.source_path};
 const check=features=>features.filter(f=>originalAdministrativeProductMatch(f,binding.feature_sha256,binding.geometry_sha256)).length;
 const beforeMatches=check(originalAdministrativeProductFeatures({sourceScope:{},pin,body}));assert.equal(beforeMatches,0);
 const sourceScope={original_administrative_canonical_bindings:[binding]};
 const afterMatches=check(originalAdministrativeProductFeatures({sourceScope,pin,body}));assert.equal(afterMatches,1);
 const wrong=structuredClone(sourceScope);wrong.original_administrative_canonical_bindings[0].feature_index++;
 assert.throws(()=>originalAdministrativeProductFeatures({sourceScope:wrong,pin,body}),/complete value/);
 const mutated=JSON.parse(body);mutated.features[binding.feature_index].properties.injected='different original';
 const changedBody=Buffer.from(JSON.stringify(mutated));
 assert.throws(()=>originalAdministrativeProductFeatures({sourceScope,pin,body:changedBody}),/product\/ordinal/);
 results.push({source_path:pin.path,feature_index:binding.feature_index,original_feature_sha256:binding.feature_sha256,original_geometry_sha256:binding.geometry_sha256,without_preimage_matches:beforeMatches,with_preimage_matches:afterMatches,wrong_actual_ordinal_rejected:true,changed_whole_product_rejected:true});
}
console.log(JSON.stringify({scope:'Serialization join boundaries only; no native computation or source approval.',inputs:pins,candidate:{component_id:cid,before:before.failed_premises,after:after.failed_premises,native_case_revalidation:true,changed_coordinate_rejected:true},products:results},null,2));
'''
subprocess.run(['node', '--input-type=module', '-e', runner], cwd=ROOT,
               input=json.dumps(dict(scope=scope,cid=cid,geometry=geometry,products=products,pins=pins)).encode(), check=True)
