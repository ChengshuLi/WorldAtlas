import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import registry from './verified-candidates.json' with {type:'json'};
import {NATIVE_METHOD} from '../../src/ownership-method.js';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');

// This is a mathematical materialization gate, never geographic approval or
// publication authorization. Future candidates need a newly reviewed immutable
// exhaustive comparison entry, not reuse of another vintage's green receipt.
export function validateNativeSelectionReceipt(manifest, manifestSha256, receipt) {
  if (manifest.method !== NATIVE_METHOD || receipt.method !== manifest.method ||
    receipt.baseline_commit !== manifest.provenance?.baseline_commit ||
    receipt.preparation_commit !== manifest.provenance?.evaluation_commit ||
    receipt.checked_rows !== manifest.size || receipt.checked_cells !== manifest.size ** 2 ||
    receipt.unchecked_cells !== 0 || receipt.checked_runs * 2 !== manifest.runWords ||
    receipt.owned_cells !== manifest.accounting?.owned_cells || receipt.owners !== manifest.accounting?.owners ||
    receipt.installation_ready !== false)
    throw Error('Native comparison receipt differs from selected source/method/domain');
  const products = receipt.products;
  if (!Array.isArray(products) || !products.length || products.length > 512 ||
    new Set(products.map(product => product.path)).size !== products.length ||
    products.some(product => !hash(product.sha256) || !Number.isSafeInteger(product.bytes) ||
      product.bytes < 0 || product.bytes > 32 * 1024 * 1024))
    throw Error('Native comparison product inventory is incomplete');
  const inventoryHash = digest(Buffer.from(JSON.stringify(products)));
  if (receipt.two_run_products !== products.length || receipt.run_one_sha256 !== inventoryHash ||
    receipt.run_two_sha256 !== inventoryHash ||
    products.find(product => product.path === 'manifest.json')?.sha256 !== manifestSha256)
    throw Error('Native candidate lacks matching complete two-run product proof');
  const assets = products.filter(product => product.path.startsWith('native-v1/ownership/'));
  if (assets.length !== manifest.parts.length || manifest.parts.some(part => {
    const product = assets.find(product => product.path === part.path);
    return product?.sha256 !== part.sha256 || product.bytes !== part.bytes;
  })) throw Error('Native comparison grid assets differ from selected manifest');
  return true;
}

export function requireVerifiedNativeSelection(manifest, manifestSha256, repo = '.') {
  const pin = registry.candidates[manifestSha256];
  if (registry.version !== 1 || !pin || !/^[a-f0-9]{40}$/.test(pin.commit) || !hash(pin.sha256) ||
    pin.role !== 'reviewed-exhaustive-native-rule-comparison' || pin.installation_approval !== false ||
    !/^coordination\/engineering\/[a-zA-Z0-9_-]+\/[a-zA-Z0-9_.-]+\.json$/.test(pin.path))
    throw Error('Native selection requires a reviewed exhaustive comparison registration');
  const tree = execFileSync('git', ['-C', repo, 'ls-tree', '-z', pin.commit, '--', pin.path], {encoding:'utf8'});
  if (!/^100644 blob /.test(tree) || tree.slice(tree.indexOf('\t') + 1) !== pin.path + '\0')
    throw Error('Native comparison receipt must be an immutable ordinary blob');
  const blob = tree.split(' ')[2].split('\t')[0];
  const length = Number(execFileSync('git', ['-C', repo, 'cat-file', '-s', blob], {encoding:'utf8'}));
  if (!Number.isSafeInteger(length) || length < 1 || length > 32 * 1024 * 1024)
    throw Error('Native comparison receipt exceeds original file budget');
  const bytes = execFileSync('git', ['-C', repo, 'cat-file', 'blob', blob], {maxBuffer:32*1024*1024});
  if (bytes.length !== length || digest(bytes) !== pin.sha256) throw Error('Native comparison receipt hash differs');
  validateNativeSelectionReceipt(manifest, manifestSha256, JSON.parse(bytes));
  return {...pin, manifest_sha256:manifestSha256};
}
