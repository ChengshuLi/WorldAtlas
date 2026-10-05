import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {gzipSync} from 'node:zlib';

const root = path.dirname(fileURLToPath(import.meta.url));
const sources = [
  ['census-geography-levels', 'https://www.census.gov/programs-surveys/economic-census/guidance-geographies/levels.html', 'html'],
  ['census-georgia-state-local-guide', 'https://www.census.gov/geographies/reference-files/2010/geo/state-local-geo-guides-2010/georgia.html', 'html'],
  ['census-kentucky-state-local-guide', 'https://www.census.gov/geographies/reference-files/2010/geo/state-local-geo-guides-2010/kentucky.html', 'html'],
  ['census-2018-boundary-vintage', 'https://www.census.gov/programs-surveys/acs/geography-acs/geography-boundaries-by-year/2018.html', 'html'],
  ['georgia-sos-county-roster', 'https://mvp.sos.ga.gov/resource/1674861955000/County_Number_List', 'pdf'],
  ['kentucky-constitution', 'https://apps.legislature.ky.gov/law/constitution', 'html'],
  ['kentucky-revised-statutes-chapter-67', 'https://apps.legislature.ky.gov/law/statutes/chapter.aspx?id=37377', 'html'],
  ['census-2018-cartographic-boundaries', 'https://www.census.gov/geographies/mapping-files/2018/geo/carto-boundary-file.html', 'html'],
  ['census-functional-status-codes', 'https://www.census.gov/library/reference/code-lists/functional-status-codes.html', 'html'],
];
const sha = (b) => crypto.createHash('sha256').update(b).digest('hex');
const dir = path.join(root, 'authorities');
await fs.mkdir(dir, {recursive: true});
for (const [id, url, kind] of sources) {
  const filename = `${id}.${kind === 'html' ? 'html.gz' : 'pdf'}`;
  try {
    const receipt = JSON.parse(await fs.readFile(path.join(dir, `${id}.retrieval.json`), 'utf8'));
    if (receipt.retention === 'restoration-only') {
      console.log(JSON.stringify({source_id:id, status:'restoration-only', source_sha256:receipt.source_sha256}));
      continue;
    }
    await fs.access(path.join(dir, filename));
    console.log(JSON.stringify({source_id:id, status:'already-retained'}));
    continue;
  } catch {}
  const started = new Date().toISOString();
  const response = await fetch(url, {headers: {'User-Agent': 'WorldAtlas Geography Research/1.0'}});
  if (!response.ok) throw new Error(`${id} fetch failed: ${response.status}`);
  const original = Buffer.from(await response.arrayBuffer());
  const retained = kind === 'html' ? gzipSync(original, {mtime: 0}) : original;
  await fs.writeFile(path.join(dir, filename), retained, {flag: 'wx'});
  const receipt = {
    source_id: id,
    requested_url: url,
    final_url: response.url,
    retrieved_started_at: started,
    retrieved_completed_at: new Date().toISOString(),
    http_status: response.status,
    content_type: response.headers.get('content-type'),
    etag: response.headers.get('etag'),
    last_modified: response.headers.get('last-modified'),
    retained_path: `source/authorities/${filename}`,
    retained_encoding: kind === 'html' ? 'gzip; mtime=0; decompressed bytes are exact response body' : 'exact response body',
    source_bytes: original.length,
    source_sha256: sha(original),
    retained_bytes: retained.length,
    retained_sha256: sha(retained),
    license_note: id.startsWith('census-') ? 'U.S. Census Bureau public federal reference source; consult the retained Census access policy for reuse limits and attribution.' : 'Official state government reference. Retained for research evidence; legal conclusions cite the source section and date.',
  };
  await fs.writeFile(path.join(dir, `${id}.retrieval.json`), JSON.stringify(receipt, null, 2) + '\n', {flag: 'wx'});
  console.log(JSON.stringify(receipt));
}
