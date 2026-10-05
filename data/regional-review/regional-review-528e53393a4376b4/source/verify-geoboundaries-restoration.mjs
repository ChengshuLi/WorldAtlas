import {createHash} from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const started = new Date().toISOString();
const url = 'https://github.com/wmgeolab/geoBoundaries/raw/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/USA/ADM2/geoBoundaries-USA-ADM2.geojson';
const response = await fetch(url, {headers: {'User-Agent': 'WorldAtlas Geography Research/1.0'}});
if (!response.ok) throw new Error(`GeoBoundaries restoration returned HTTP ${response.status}`);
const bytes = Buffer.from(await response.arrayBuffer());
const sha256 = createHash('sha256').update(bytes).digest('hex');
const local = await fs.readFile(path.join(root, 'geoBoundaries-USA-ADM2.geojson'));
const pointer = await fs.readFile(path.join(root, 'geoBoundaries-USA-ADM2.geojson.lfs-pointer'), 'utf8');
const expected = pointer.match(/oid sha256:([a-f0-9]{64})\nsize (\d+)/);
if (!expected || sha256 !== expected[1] || bytes.length !== Number(expected[2]) || !bytes.equals(local)) {
  throw new Error('Immutable upstream object does not match retained LFS object, pointer, and bytes');
}
const receipt = {
  source_id: 'geoboundaries-usa-adm2-2018', requested_url: url, final_url: response.url,
  retrieved_started_at: started, retrieved_completed_at: new Date().toISOString(),
  http_status: response.status, content_type: response.headers.get('content-type'),
  resolved_commit: '9469f09592ced973a3448cf66b6100b741b64c0d',
  restored_object_sha256: sha256, restored_object_bytes: bytes.length,
  pointer_sha256: createHash('sha256').update(pointer).digest('hex'),
  pointer_bytes: Buffer.byteLength(pointer), retained_bytes_equal: true,
  license: 'Public Domain as stated in upstream metadata; upstream metadata cites US Census MAF/TIGER Database.',
  retained_path: 'source/geoBoundaries-USA-ADM2.geojson',
  limitation: 'This verifies byte restoration and metadata only; it does not certify geometry or legal boundaries.'
};
await fs.writeFile(path.join(root, 'geoBoundaries-restoration.json'), JSON.stringify(receipt, null, 2) + '\n');
console.log(JSON.stringify(receipt));
