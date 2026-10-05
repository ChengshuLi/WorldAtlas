import fs from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {build} from 'esbuild';

export function cloudflareConfig({domain = '', audience = '', publicReadOnly = false} = {}) {
  return {
    name: 'worldatlas-explorer', main: 'index.js', compatibility_date: '2026-10-01',
    workers_dev: true, preview_urls: false,
    // Authentication must run even when a request matches a static file.
    assets: {directory: '../client', binding: 'ASSETS', run_worker_first: true},
    r2_buckets: [{binding: 'BUCKET', bucket_name: 'worldatlas-archives'}],
    vars: {ATLAS_CONTENT_BACKEND: 'postgres', ATLAS_READ_ONLY: '1',
      ATLAS_ACCESS_TEAM_DOMAIN: domain, ATLAS_ACCESS_AUD: audience,
      ATLAS_PUBLIC_READ_ONLY: publicReadOnly === true ? '1' : '0'},
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
  process.chdir(root);
  process.env.ATLAS_HOSTED_BUILD = '1';
  await import('./build-static.mjs');
  await fs.mkdir('dist/client', {recursive: true});
  for (const name of await fs.readdir('dist')) {
    if (name !== 'client') await fs.rename(`dist/${name}`, `dist/client/${name}`);
  }
  await fs.mkdir('dist/cloudflare', {recursive: true});
  await build({entryPoints: ['hosted/cloudflare-worker.js'], outfile: 'dist/cloudflare/index.js',
    bundle: true, format: 'esm', platform: 'browser', target: 'es2022', minify: true});
  await fs.writeFile('dist/cloudflare/wrangler.json', JSON.stringify(cloudflareConfig({
    domain: process.env.ATLAS_ACCESS_TEAM_DOMAIN, audience: process.env.ATLAS_ACCESS_AUD,
    publicReadOnly: process.env.ATLAS_PUBLIC_READ_ONLY === '1',
  }), null, 2) + '\n');
  console.log('Cloudflare package prepared; explicit access mode, PostgreSQL and read-only defaults. No deployment or database migrations performed.');
}
