// Explicit full/model-reader setup. No package environment is synthesized.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {preflightArtifactPackage} from './arctic-package-preflight.mjs';
import {issueCheckoutExecution} from './artifact-checkout-execution.mjs';
import {restoreCanonicalProducts} from '../eastern-two-gap-repair-native-20261007/restore-canonical-products.mjs';
import {consumeQualifiedArcticArtifacts} from './qualified-artifact-consumer.mjs';
import {installV9Stage} from './install-v9-stage.mjs';
const N2='coordination/engineering/arctic-three-retained-land-fit-repair-native-20261008';
export async function prepareModelReaderCheckout({root=process.cwd(),profile,shard}) {
  assert.equal(profile,'full');assert([0,1,2].includes(shard),'Declared full regression shard required');
  root=fs.realpathSync(root);
  const selection=JSON.parse(fs.readFileSync(path.join(root,'data/ownership-selection.json')));
  if(!selection.artifact_consumption)return {applicable:false};
  const stage=JSON.parse(fs.readFileSync(path.join(root,N2,'context-stage-v9.json')));
  assert.equal(stage.version,4);assert.deepEqual(stage.artifact_consumption,selection.artifact_consumption);
  // Complete selected physical/decode/member admission precedes runtime hashing
  // and restoration. The genuine same-root checkout is declared explicitly.
  const admission=preflightArtifactPackage({source:root,stage:root,sidecar:stage});
  const execution=issueCheckoutExecution({root,admission});
  fs.mkdirSync(path.join(root,'.cache'),{recursive:true});
  const restoredReceipt=restoreCanonicalProducts({root,mode:'checkout',temporaryRoot:path.join(root,'.cache')});
  const context=await consumeQualifiedArcticArtifacts({root,stage,selection,restoredReceipt,currentExecution:execution});
  context.installation=await installV9Stage({root,stage,context});
  return {applicable:true,kind:'qualified-model-reader-checkout',execution:context.receipt.current_execution,
    consumption:context.receipt,installation:context.installation,scientific_producers_invoked:false};
}
