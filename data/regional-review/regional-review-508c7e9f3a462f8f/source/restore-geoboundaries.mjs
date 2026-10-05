import crypto from 'node:crypto';
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.dirname(fileURLToPath(import.meta.url));
const objects = [
  {oid: '81fdd384df8012e5007ed2994a8ab306352f3c48e32cd8ea99182195e8647f43', size: 10500644, file: 'geoBoundaries-USA-ADM2.geojson'},
  {oid: 'a4d2a82a1cd434960b6ed49531bff3330d0881674eea9dc8711e1ad6bf049b9f', size: 939, file: 'geoBoundaries-USA-ADM2-metaData.json'},
];
const endpoint = 'https://github.com/wmgeolab/geoBoundaries.git/info/lfs/objects/batch';
for (const object of objects) {
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {Accept: 'application/vnd.git-lfs+json', 'Content-Type': 'application/vnd.git-lfs+json'},
    body: JSON.stringify({operation: 'download', transfers: ['basic'], objects: [{oid: object.oid, size: object.size}]}),
  });
  if (!response.ok) throw new Error(`LFS batch request failed: ${response.status}`);
  const batch = await response.json();
  const result = batch.objects?.find((item) => item.oid === object.oid && item.size === object.size);
  const action = result?.actions?.download;
  if (!action?.href || !action.href.startsWith('https://')) throw new Error(`Pinned LFS action missing for ${object.file}`);
  const downloaded = await fetch(action.href, {headers: action.header ?? {}});
  if (!downloaded.ok) throw new Error(`LFS object download failed: ${downloaded.status}`);
  const bytes = Buffer.from(await downloaded.arrayBuffer());
  const digest = crypto.createHash('sha256').update(bytes).digest('hex');
  if (bytes.length !== object.size || digest !== object.oid) throw new Error(`LFS source mismatch for ${object.file}: ${bytes.length} bytes, SHA-256 ${digest}`);
  const output = path.join(root, object.file);
  try {
    const existing = await fs.readFile(output);
    const existingDigest = crypto.createHash('sha256').update(existing).digest('hex');
    if (existingDigest !== digest) throw new Error(`Refusing to replace existing bytes in ${object.file}`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    await fs.writeFile(output, bytes, {flag: 'wx'});
  }
  console.log(JSON.stringify({path: object.file, bytes: bytes.length, sha256: digest}));
}
