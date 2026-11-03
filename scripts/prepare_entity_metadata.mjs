#!/usr/bin/env node
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {withEntityRegistry} from '../web/v7-entity-adapter.js';

// A Neon export carries identity and bindings, never the UI color palette.
export function prepareEntityMetadata(proposal, exported = null) {
  if (!exported) return withEntityRegistry(proposal);
  if (!Array.isArray(exported.category_bindings)) throw Error('Missing registry category bindings');
  const bindings = new Map();
  for (const binding of exported.category_bindings) {
    if (bindings.has(binding.code)) throw Error('Duplicate exported category binding');
    bindings.set(binding.code, binding);
  }
  if (bindings.size !== proposal.categories.length) throw Error('Registry/category inventory mismatch');
  const categories = proposal.categories.map(category => {
    const binding = bindings.get(category.id);
    if (!binding || binding.physical_class !== category.physical_class)
      throw Error(`Registry/category physical-class mismatch: ${category.id}`);
    return {...category, entity_id: binding.entity_id};
  });
  return withEntityRegistry({...proposal, categories}, exported.entity_registry);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const args = process.argv.slice(2), stdin = args[0] === '--stdin';
    const registryIndex = args.indexOf('--registry');
    const exported = registryIndex < 0 ? null : JSON.parse(fs.readFileSync(args[registryIndex + 1], 'utf8'));
    if (!stdin && (!args[0] || !args[1])) throw Error('Usage: prepare_entity_metadata.mjs INPUT OUTPUT [--registry NEON_EXPORT]');
    const proposal = JSON.parse(fs.readFileSync(stdin ? 0 : args[0], 'utf8'));
    const result = JSON.stringify(prepareEntityMetadata(proposal, exported), null, 2) + '\n';
    if (stdin) process.stdout.write(result);
    else fs.writeFileSync(args[1], result, {flag: 'wx'});
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
