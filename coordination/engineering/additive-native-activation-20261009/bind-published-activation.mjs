import {nativeBaseSelection,valueBytes,valueSha} from '../selected-geography-effective-prevention-20261009/selected-neighbor-prevention.mjs';
import {additiveBaseReference} from '../../../src/effective-footprint.js';
const demand=(v,m)=>{if(!v)throw Error(m);};
const whole=pin=>{
  demand(pin&&/^[a-f0-9]{40}$/.test(pin.commit)&&['100644','100755'].includes(pin.mode)
    &&/^[a-f0-9]{40}$/.test(pin.git_blob_oid)&&/^[a-f0-9]{64}$/.test(pin.sha256)
    &&Number.isSafeInteger(pin.bytes)&&pin.bytes>0&&pin.bytes<=33554432
    &&typeof pin.path==='string'&&!pin.path.startsWith('/')&&!pin.path.includes('\\')
    &&pin.path.split('/').every(p=>p&&p!=='.'&&p!=='..'),'Complete ordinary published activation pin required');
  if(pin.decoded_bytes!==undefined)demand(Number.isSafeInteger(pin.decoded_bytes)
    &&pin.decoded_bytes>0&&pin.decoded_bytes<=33554432&&/^[a-f0-9]{64}$/.test(pin.decoded_sha256),
    'Complete decoded activation pin required');
};

// Pure publication metadata binding. This does not read, approve, select or
// activate anything: the normal private selected reader authenticates all these
// whole locators, original policies and cold products before application use.
export function bindPublishedActivation({baseSelection,envelope,registry,envelopePin,registryPin,assets}) {
  additiveBaseReference({additiveRelease:envelope,reference_release:envelope?.effective_reference});
  demand(envelope.version===2&&registry?.version===1&&registry.kind==='retained-rule-authority-registry-v1'
    &&Object.keys(registry).sort().join(',')==='entries,kind,version'&&Array.isArray(registry.entries),
    'Existing V2 envelope and typed component authority registry required');
  demand(assets&&Object.keys(assets).sort().join(',')==='base_manifest,ledger,owner_roster,patch',
    'Four exact ordinary published runtime assets required');
  for(const pin of [envelopePin,registryPin,...Object.values(assets)])whole(pin);
  demand(envelopePin.bytes===valueBytes(envelope).length&&envelopePin.sha256===valueSha(envelope)
    &&registryPin.bytes===valueBytes(registry).length&&registryPin.sha256===valueSha(registry),
    'Whole publication differs from complete envelope/registry');
  for(const [role,pin]of Object.entries(assets)){
    const logical=envelope[role];
    demand(logical&&pin.bytes===logical.bytes&&pin.sha256===logical.sha256
      &&(pin.decoded_bytes??pin.bytes)===(logical.decoded_bytes??logical.bytes)
      &&(pin.decoded_sha256??pin.sha256)===(logical.decoded_sha256??logical.sha256),
      'Published runtime asset differs from qualified assembly: '+role);
  }
  demand(assets.base_manifest.sha256===baseSelection.sha256,'Published native base differs');
  return {version:2,kind:'retained-native-additive-selection-v2',
    base_selection:nativeBaseSelection(baseSelection),authority_registry:registryPin,
    runtime_envelope:envelopePin,logical_asset_map:assets};
}

export function selectPublishedActivation(baseSelection,sidecarPin) {
  whole(sidecarPin);demand(sidecarPin.decoded_bytes===undefined,'Committed selection sidecar must be ordinary JSON');
  return {...nativeBaseSelection(baseSelection),additive_release:{path:sidecarPin.path,bytes:sidecarPin.bytes,sha256:sidecarPin.sha256}};
}
