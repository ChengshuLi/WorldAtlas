import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
// Adverse build dependency: mutate the actually consumed source path after
// prepare() captures its bytes, before delegating to the real esbuild runtime.
export async function build(options) {
  const wrapper=path.join(options.stdin.resolveDir,'hosted/site-r2-export.js');
  const original=await fs.readFile(wrapper);
  try {
    await fs.writeFile(wrapper,"export function readOnlyR2Export(){return {fetch(){return new Response('unreviewed-drift')}}};\n");
    const real=await import(pathToFileURL(process.env.WORLDATLAS_FIXTURE_ESBUILD_MODULE).href);
    return await real.build(options);
  } finally {await fs.writeFile(wrapper,original);}
}
