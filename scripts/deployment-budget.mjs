import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {spawn} from 'node:child_process';
import {Transform, Writable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {createGzip} from 'node:zlib';
import {fileURLToPath} from 'node:url';

export const deploymentPolicy = Object.freeze({
  package_limit_bytes: 256 * 1024 ** 2,
  package_reserve_bytes: 4 * 1024 ** 2,
  asset_limit_bytes: 25 * 1024 ** 2,
  asset_reserve_bytes: 1024 ** 2,
});
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;

export function deploymentCategory(file) {
  if (file.startsWith('drizzle/') || file.startsWith('dist/server/drizzle/')) return 'migration-transport';
  if (file.startsWith('dist/server/')) return 'worker';
  const asset = file.replace(/^dist\/client\//, '');
  if (/^(ownership\/|ownership-runtime\/|ownership-history\/)/.test(asset)) return 'ownership';
  if (asset.startsWith('geography/')) return 'geography';
  if (/^(reference-attributes\/|prepared-evidence\/|atlas-history)/.test(asset)) return 'prepared-evidence';
  if (asset.startsWith('assets/') || asset === 'index.html') return 'application';
  if (file === '.openai/hosting.json') return 'hosting-config';
  return 'review-and-reference';
}

async function inventory(root, relative, destination = relative) {
  const actual = path.join(root, relative), stat = await fs.lstat(actual);
  if (stat.isSymbolicLink()) throw Error(`Deployment entry must not be a symlink: ${relative}`);
  if (stat.isFile()) {
    const bytes = await fs.readFile(actual);
    return [{path: destination, bytes: bytes.length, sha256: hash(bytes), category: deploymentCategory(destination)}];
  }
  if (!stat.isDirectory()) throw Error(`Unsupported deployment entry: ${relative}`);
  const files = [];
  for (const name of (await fs.readdir(actual)).sort(compare)) {
    files.push(...await inventory(root, `${relative}/${name}`, `${destination}/${name}`));
  }
  return files;
}

export function budgetViolations(report, policy = deploymentPolicy) {
  for (const [name, value] of Object.entries(policy)) {
    if (!Number.isSafeInteger(value) || value < 0) throw Error(`Invalid budget: ${name}`);
  }
  if (policy.package_reserve_bytes >= policy.package_limit_bytes || policy.asset_reserve_bytes >= policy.asset_limit_bytes) throw Error('Reserve must be below its hard limit');
  const errors = [], packageTarget = policy.package_limit_bytes - policy.package_reserve_bytes;
  if (report.archive.uncompressed_bytes > packageTarget) errors.push(`Package tar is ${report.archive.uncompressed_bytes} bytes; target ${packageTarget}, hard limit ${policy.package_limit_bytes}; reduce by ${report.archive.uncompressed_bytes - packageTarget} bytes`);
  const assetTarget = policy.asset_limit_bytes - policy.asset_reserve_bytes;
  for (const file of report.files) if (file.bytes > assetTarget) errors.push(`${file.path}: ${file.bytes} bytes; asset target ${assetTarget}, hard limit ${policy.asset_limit_bytes}; reduce by ${file.bytes - assetTarget} bytes`);
  return errors;
}

export function formatDeploymentBudget(report) {
  const lines = [`Deployment: ${report.file_bytes} file bytes; tar ${report.archive.uncompressed_bytes} bytes; gzip ${report.archive.compressed_bytes} bytes.`,
    `Package reserve: ${report.policy.package_reserve_bytes} bytes; asset reserve: ${report.policy.asset_reserve_bytes} bytes (1 MiB = 1048576 bytes).`, 'Categories:'];
  for (const [name, category] of Object.entries(report.categories)) lines.push(`  ${name}: ${category.bytes} bytes (${category.files} files)`);
  lines.push('Largest files:');
  for (const file of [...report.files].sort((a, b) => b.bytes - a.bytes || compare(a.path, b.path)).slice(0, 10)) lines.push(`  ${file.path}: ${file.bytes} bytes`);
  lines.push(...report.violations.map(error => `FAIL: ${error}`));
  return lines.join('\n');
}

export function immutableAssetCandidates(report) {
  const candidates = report.files.filter(file => /^(dist\/client\/(ownership|ownership-runtime|geography|reference-attributes|prepared-evidence)\/)/.test(file.path));
  return {version: 1, status: 'proposed-only', project_id: report.project_id,
    package_archive_sha256: report.archive.sha256,
    candidate_bytes: candidates.reduce((sum, file) => sum + file.bytes, 0),
    object_storage_account_allowance_verified: false, uploads_verified: false,
    contract: {object_key: 'worldatlas/map-assets/sha256/<sha256>', audience: 'preserve owner-private authorization',
      route: 'proposed same-origin authenticated GET /api/map-assets/sha256/<sha256>',
      bytes: 'Stored bytes and SHA-256 must match; do not transparently decompress .gz inputs',
      browser_cache: 'private, max-age=31536000, immutable only after successful authorization',
      edge_cache: 'No public shared cache; authorize every request before serving an authenticated cache hit',
      activation: 'Publisher verifies all objects and pins a complete manifest/release before switching; retain local assets and previous version for rollback'},
    files: candidates.map(file => ({...file, object_key: `worldatlas/map-assets/sha256/${file.sha256}`}))};
}

// The primary build contains dist/drizzle; Sites needs those same derivatives
// at root drizzle. Map that directory in the tar without touching source SQL.
// A staged Site has already moved the transport to root and removed the copy.
export async function auditDeployment({root = '.', layout = 'build', archivePath, policy = deploymentPolicy} = {}) {
  root = path.resolve(root);
  if (!['build', 'site'].includes(layout)) throw Error('Use build or site deployment layout');
  const config = JSON.parse(await fs.readFile(path.join(root, '.openai/hosting.json')));
  if (!config.project_id) throw Error('Deployment needs its existing Site project ID');
  // lstat every parent, including .openai, rather than follow a linked input.
  if ((await fs.lstat(path.join(root, '.openai'))).isSymbolicLink()) throw Error('Deployment .openai must not be a symlink');
  const entries = ['.openai/hosting.json', 'dist'];
  let files = await inventory(root, '.openai/hosting.json');
  files.push(...await inventory(root, 'dist'));
  if (layout === 'build') {
    if (!files.some(file => file.path.startsWith('dist/drizzle/'))) throw Error('Build has no compiled migration transport');
    files = files.map(file => file.path.startsWith('dist/drizzle/') ? {...file, path: file.path.replace(/^dist\/drizzle\//, 'drizzle/'), category: 'migration-transport'} : file);
  } else {
    if (files.some(file => file.path.startsWith('dist/drizzle/'))) throw Error('Remove redundant dist/drizzle with the staging protocol before auditing a Site');
    entries.push('drizzle');
    files.push(...await inventory(root, 'drizzle'));
  }
  files.sort((a, b) => compare(a.path, b.path));
  if (archivePath) {
    archivePath = path.resolve(archivePath);
    if (entries.some(entry => archivePath === path.join(root, entry) || archivePath.startsWith(path.join(root, entry) + path.sep))) throw Error('Archive output must be outside deployment inputs');
    await fs.mkdir(path.dirname(archivePath), {recursive: true});
  }
  const args = ['--sort=name', '--format=posix', '--pax-option=delete=atime,delete=ctime', '--mtime=@0', '--owner=0', '--group=0', '--numeric-owner'];
  if (layout === 'build') args.push('--transform=s,^dist/drizzle,drizzle,');
  args.push('-cf', '-', '-C', root, ...entries);
  const output = archivePath ? await fs.open(archivePath, 'wx') : null;
  const tar = spawn('tar', args, {stdio: ['ignore', 'pipe', 'pipe']});
  let stderr = '', uncompressedBytes = 0, compressedBytes = 0;
  tar.stderr.on('data', bytes => { stderr += bytes.toString(); });
  const finished = new Promise((resolve, reject) => {
    tar.on('error', reject);
    tar.on('close', code => code === 0 ? resolve() : reject(Error(`Deployment tar failed (${code}): ${stderr}`)));
  });
  // Attach a handler immediately so an early spawn error cannot go unhandled.
  finished.catch(() => {});
  const digest = createHash('sha256');
  const counter = new Transform({transform(bytes, encoding, callback) { uncompressedBytes += bytes.length; callback(null, bytes); }});
  const sink = new Writable({write(bytes, encoding, callback) {
    compressedBytes += bytes.length; digest.update(bytes);
    if (output) output.writeFile(bytes).then(() => callback(), callback); else callback();
  }});
  try {
    await Promise.all([finished, pipeline(tar.stdout, counter, createGzip({level: 9}), sink)]);
  } catch (error) {
    tar.kill();
    if (output) { await output.close(); await fs.rm(archivePath, {force: true}); }
    throw error;
  }
  if (output) await output.close();
  // A report must not silently combine hashes from one build with archive
  // bytes from another writer. Refuse concurrent input changes.
  const after = [...await inventory(root, '.openai/hosting.json'), ...await inventory(root, 'dist')];
  if (layout === 'build') for (const file of after) if (file.path.startsWith('dist/drizzle/')) { file.path = file.path.replace(/^dist\/drizzle\//, 'drizzle/'); file.category = 'migration-transport'; }
  if (layout === 'site') after.push(...await inventory(root, 'drizzle'));
  after.sort((a, b) => compare(a.path, b.path));
  if (JSON.stringify(after) !== JSON.stringify(files)) {
    if (archivePath) await fs.rm(archivePath, {force: true});
    throw Error('Deployment inputs changed during archive accounting; stop other build writers and retry');
  }
  const categories = {};
  for (const file of files) {
    const category = categories[file.category] ??= {files: 0, bytes: 0};
    category.files++; category.bytes += file.bytes;
  }
  const report = {version: 1, measured_at_utc: new Date().toISOString(), layout, project_id: config.project_id,
    units: 'bytes; MiB = 1048576 bytes', policy: {...policy}, file_count: files.length,
    file_bytes: files.reduce((sum, file) => sum + file.bytes, 0), categories,
    archive: {format: 'POSIX tar, fixed metadata, gzip level 9', uncompressed_bytes: uncompressedBytes, compressed_bytes: compressedBytes, sha256: digest.digest('hex')},
    headroom: {package_hard_bytes: policy.package_limit_bytes - uncompressedBytes,
      package_target_bytes: policy.package_limit_bytes - policy.package_reserve_bytes - uncompressedBytes,
      largest_asset_hard_bytes: policy.asset_limit_bytes - Math.max(...files.map(file => file.bytes))},
    excluded: ['.git', 'node_modules', '.cache', 'data (including SQLite, source archives and research)', 'drizzle-source (retained raw source SQL)', 'source code and documentation outside dist'],
    files};
  report.violations = budgetViolations(report, policy);
  return report;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = {};
  for (let i = 2; i < process.argv.length; i += 2) {
    const key = process.argv[i];
    if (!['--root', '--layout', '--out', '--archive'].includes(key) || !process.argv[i + 1] || options[key]) throw Error('Use --root PATH --layout build|site --out REPORT [--archive NEW.tar.gz]');
    options[key] = process.argv[i + 1];
  }
  const root = path.resolve(options['--root'] ?? '.'), output = options['--out'] && path.resolve(options['--out']);
  const inputs = ['dist', '.openai/hosting.json', ...(options['--layout'] === 'site' ? ['drizzle'] : [])];
  if (output && inputs.some(input => output === path.join(root, input) || output.startsWith(path.join(root, input) + path.sep))) throw Error('Report must be outside deployment inputs');
  const report = await auditDeployment({root, layout: options['--layout'], archivePath: options['--archive']});
  if (options['--out']) {
    await fs.mkdir(path.dirname(output), {recursive: true});
    await fs.writeFile(output, JSON.stringify(report, null, 2) + '\n');
  }
  console.log(formatDeploymentBudget(report));
  if (report.violations.length) process.exitCode = 1;
}
