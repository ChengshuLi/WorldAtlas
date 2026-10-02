import http from 'node:http';
import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDatabase, seedDatabase, geography, snapshot } from './database.mjs';
import {environmentClassifications} from './src/environment-classifications.js';
process.chdir(path.dirname(fileURLToPath(import.meta.url)));
const db = openDatabase(); seedDatabase(db);
const catalog=geography(db);
if(fs.existsSync('data/pixel-audit.json'))catalog.pixelMissing=JSON.parse(fs.readFileSync('data/pixel-audit.json')).missing.map(f=>f.id);
if(fs.existsSync('data/prepared-evidence/index.json')){const raw=fs.readFileSync('data/prepared-evidence/index.json'),index=JSON.parse(raw);catalog.preparedEvidence={footprints_sha256:index.footprints_sha256,hierarchy_sha256:index.hierarchy_sha256,index_sha256:createHash('sha256').update(raw).digest('hex')};}
const geo = JSON.stringify(catalog);
const production = process.argv.includes('--production');
const vite = production ? null : await (await import('vite')).createServer({ server: { middlewareMode: true, host: '0.0.0.0', hmr: process.env.ATLAS_TEST_MODE === '1' ? false : undefined } });
const mime = { '.html':'text/html', '.js':'text/javascript', '.css':'text/css', '.svg':'image/svg+xml', '.png':'image/png' };
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if(req.method==='GET' && /^\/prepared-evidence\/(?:index\.json|part-\d+\.json\.gz)$/.test(url.pathname)){const file=`data${url.pathname}`;if(!fs.existsSync(file)){res.writeHead(404);return res.end('Not found');}res.setHeader('Content-Type',url.pathname.endsWith('.gz')?'application/gzip':'application/json');return fs.createReadStream(file).pipe(res);}
  if(req.method==='GET' && /^\/geographic-decisions\/(?:africa|asia|europe|north-america|south-america|oceania)\.json\.gz$/.test(url.pathname)){const file=`data${url.pathname.slice(0,-3)}`;if(!fs.existsSync(file)){res.writeHead(404);return res.end('Not found');}res.setHeader('Content-Type','application/gzip');return res.end(gzipSync(fs.readFileSync(file)));}
  if(req.method==='GET' && ['/geographic-migration-review.json.gz','/geographic-migration-archive.json.gz','/granularity-review-evidence.json.gz'].includes(url.pathname)){res.setHeader('Content-Type','application/gzip');return fs.createReadStream(`data${url.pathname}`).pipe(res);}
  if(req.method==='GET' && url.pathname==='/region-semantic-review.json.gz'){res.setHeader('Content-Type','application/gzip');return res.end(gzipSync(fs.readFileSync('data/region-semantic-review.json')));}
  if(req.method==='GET' && url.pathname==='/macro-review-evidence.json'){res.setHeader('Content-Type','application/json');return fs.createReadStream('data/macro-review-evidence.json').pipe(res);}
  if(req.method==='GET' && url.pathname==='/macro-corrections.json'){res.setHeader('Content-Type','application/json');return fs.createReadStream('data/macro-corrections.json').pipe(res);}
  if(req.method==='GET' && url.pathname==='/source-policy-corrections/summary.json'){res.setHeader('Content-Type','application/json');return fs.createReadStream('data/source-policy-corrections/summary.json').pipe(res);}
  if(req.method==='GET' && /^\/world-review-locations-\d+\.json\.gz$/.test(url.pathname)){res.setHeader('Content-Type','application/gzip');return fs.createReadStream(`data${url.pathname}`).pipe(res);}
  if(req.method==='GET' && ['/granularity-report.json','/hierarchy-report.json','/administrative-sources.json','/semantic-report.json','/granularity-audit.json','/coverage-report.json','/location-policy.json','/world-review.json','/source-inventory.json','/pixel-audit.json','/global-refinement-report.json','/regional-membership-report.json','/border-parent-review.json','/attribute-sources.json','/reference-polity-report.json','/settlement-source-report.json'].includes(url.pathname)){res.setHeader('Content-Type','application/json');return fs.createReadStream(`data${url.pathname}`).pipe(res);}
  if (url.pathname.startsWith('/api/')) {
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Cache-Control', 'no-store');
    if (req.method !== 'GET') { res.writeHead(405); return res.end(JSON.stringify({error:'Method not allowed'})); }
    try {
      if (url.pathname === '/api/geography') return res.end(geo);
      if (url.pathname === '/api/classifications') return res.end(JSON.stringify({version:1,unknown:null,attributes:environmentClassifications}));
      if (url.pathname === '/api/snapshot') return res.end(JSON.stringify(snapshot(db, Number(url.searchParams.get('year')), url.searchParams.get('examples') === '1',url.searchParams.get('source_evidence')==='1')));
      res.writeHead(404); return res.end(JSON.stringify({error:'Not found'}));
    } catch (error) { res.writeHead(400); return res.end(JSON.stringify({error:error.message})); }
  }
  if (vite) return vite.middlewares(req, res);
  let pathname;
  try { pathname = decodeURIComponent(url.pathname); } catch { res.writeHead(400); return res.end('Invalid path'); }
  const file = path.resolve('dist', '.' + (pathname === '/' ? '/index.html' : pathname));
  if (!file.startsWith(path.resolve('dist') + path.sep) || !fs.existsSync(file) || !fs.statSync(file).isFile()) { res.writeHead(404); return res.end('Not found'); }
  res.setHeader('Content-Type', mime[path.extname(file)] || 'application/octet-stream');
  fs.createReadStream(file).pipe(res);
});
server.listen(Number(process.env.PORT || 3000), '0.0.0.0', () => console.log(`WorldAtlas listening on http://localhost:${server.address().port}`));
async function close() { await vite?.close(); server.close(() => { db.close(); process.exit(0); }); }
process.on('SIGTERM', close); process.on('SIGINT', close);
