import {assertPackageStage} from './package-build.mjs';
import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {build} from 'esbuild';

export function cloudflareConfig({domain = '', audience = '', publicReadOnly = false, preserveAssets = false} = {}) {
  const config = {
    name: 'worldatlas-explorer', main: 'index.js', compatibility_date: '2026-10-01',
    workers_dev: true, preview_urls: false,
    // Authentication must run even when a request matches a static file.
    assets: {directory: '../client', binding: 'ASSETS', run_worker_first: true},
    r2_buckets: [{binding: 'BUCKET', bucket_name: 'worldatlas-archives'}],
    vars: {ATLAS_CONTENT_BACKEND: 'postgres', ATLAS_READ_ONLY: '1',
      ATLAS_ACCESS_TEAM_DOMAIN: domain, ATLAS_ACCESS_AUD: audience,
      ATLAS_PUBLIC_READ_ONLY: publicReadOnly === true ? '1' : '0'},
  };
  // Omitted public-build settings retain deployed plain-text/JSON variables.
  // Empty Access defaults are placeholders, not an instruction to clear them.
  if (publicReadOnly === true && !preserveAssets) {
    config.keep_vars = true;
    for (const key of ['ATLAS_ACCESS_TEAM_DOMAIN', 'ATLAS_ACCESS_AUD']) {
      if (config.vars[key] === '') delete config.vars[key];
    }
  }
  // Worker-only compatibility comes first. Wrangler's existing metadata path
  // retains the deployed assets and bindings without exporting secret values.
  if(preserveAssets){delete config.assets;delete config.r2_buckets;delete config.vars;config.unsafe={metadata:{keep_assets:true,keep_bindings:['plain_text','json','secret_text','secret_key','r2_bucket','hyperdrive','assets']}};}
  return config;
}

export async function bundleCloudflareWorker(root,output){
  await fs.mkdir(output,{recursive:true});
  await build({absWorkingDir:root,entryPoints:['hosted/cloudflare-worker.js'],outfile:path.join(output,'index.js'),bundle:true,format:'esm',platform:'browser',target:'es2022',minify:true});
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  assertPackageStage();
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  process.chdir(root);
  process.env.ATLAS_HOSTED_BUILD = '1';
  await import('./build-static-inner.mjs');
  await fs.mkdir('dist/client', {recursive: true});
  for (const name of await fs.readdir('dist')) {
    if (name !== 'client') await fs.rename(`dist/${name}`, `dist/client/${name}`);
  }
  await fs.mkdir('dist/cloudflare', {recursive: true});
  await bundleCloudflareWorker(root,path.join(root,'dist/cloudflare'));
  await fs.writeFile('dist/cloudflare/wrangler.json', JSON.stringify(cloudflareConfig({
    domain: process.env.ATLAS_ACCESS_TEAM_DOMAIN, audience: process.env.ATLAS_ACCESS_AUD,
    publicReadOnly: process.env.ATLAS_PUBLIC_READ_ONLY === '1',
  }), null, 2) + '\n');
  console.log('Cloudflare package prepared; explicit access mode, PostgreSQL and read-only defaults. No deployment or database migrations performed.');
}
