// Original Cloudflare output custody. This records actual files; it does not
// turn a saved receipt into a new build or confer Actions producer authority.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {loadPackageInputs, validatePackageInputs, containsPackagePath, safePackagePath} from './package-inputs.mjs';

export const OUTPUT_MANIFEST = '.cache/package-output-manifest.json';
export const OUTPUT_SOURCE = '.cache/package-output-source.json';
export const OUTPUT_ARTIFACT_PREFIX = 'cloudflare-package-output-';
const need = (ok, message) => { if (!ok) throw Error(message); };
const sha = raw => createHash('sha256').update(raw).digest('hex');
const commit = value => /^[a-f0-9]{40}$/.test(value ?? '');
const hash = value => /^[a-f0-9]{64}$/.test(value ?? '');
const positive = value => Number.isSafeInteger(value) && value > 0;
const MAX_METADATA = 8 * 1024 * 1024;
// Content sizes are admitted from actual inventories and available disk, not a
// fixed package-size allowance. These metadata bounds do not change deployment limits.
// Content is streamed with one 1 MiB buffer. No whole package is held in memory.
export const PACKAGE_OUTPUT_LIMITS = Object.freeze({files: 20000, member_bytes: Number.MAX_SAFE_INTEGER,
  total_bytes: Number.MAX_SAFE_INTEGER, metadata_bytes: MAX_METADATA});
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

function ordinary(root, relative, directory = false) {
  need(safePackagePath(relative) && !relative.endsWith('/'), 'Safe ordinary package path required');
  let at = fs.realpathSync(root);
  const names = relative.split('/');
  for (let i = 0; i < names.length; i++) {
    at = path.join(at, names[i]);
    const stat = fs.lstatSync(at);
    need(!stat.isSymbolicLink() && (i < names.length - 1 || directory ? stat.isDirectory() : stat.isFile()),
      'Nonordinary package member or ancestor: ' + relative);
  }
  return at;
}

export function streamedPackageFile(root, relative, maximum = PACKAGE_OUTPUT_LIMITS.member_bytes) {
  const file = ordinary(root, relative), before = fs.lstatSync(file);
  need(Number.isSafeInteger(before.size) && before.size >= 0 && before.size <= maximum, 'Package member exceeds admitted bytes');
  const fd = fs.openSync(file, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW), digest = createHash('sha256');
  const buffer = Buffer.alloc(1024 * 1024); let bytes = 0;
  try {
    for (;;) {
      const count = fs.readSync(fd, buffer, 0, buffer.length, null);
      if (!count) break;
      bytes += count; need(bytes <= before.size, 'Package member grew while hashing');
      digest.update(buffer.subarray(0, count));
    }
    const held = fs.fstatSync(fd), after = fs.lstatSync(file);
    need(bytes === before.size && ['dev','ino','size','mode','mtimeMs','ctimeMs'].every(key =>
      before[key] === held[key] && held[key] === after[key]), 'Package member changed while hashing');
  } finally { fs.closeSync(fd); }
  return {path: relative, bytes, sha256: digest.digest('hex')};
}

export function inventoryPackageOutput(root) {
  const result = []; let total = 0;
  const visit = relative => {
    const directory = ordinary(root, relative, true);
    for (const name of fs.readdirSync(directory).sort()) {
      const child = relative + '/' + name, stat = fs.lstatSync(path.join(root, child));
      need(!stat.isSymbolicLink(), 'Output links are not ordinary retained package files');
      if (stat.isDirectory()) visit(child);
      else {
        need(stat.isFile() && result.length < PACKAGE_OUTPUT_LIMITS.files, 'Unsupported or excessive output inventory');
        const row = streamedPackageFile(root, child); total += row.bytes;
        need(total <= PACKAGE_OUTPUT_LIMITS.total_bytes, 'Package output exceeds transport admission'); result.push(row);
      }
    }
  };
  ordinary(root, 'dist', true);
  need(fs.readdirSync(path.join(root, 'dist')).every(name=>['client','cloudflare','drizzle'].includes(name)), 'Exact Cloudflare output roots required');
  // The regression runner may separately compile dist/drizzle for migration
  // tests. It is not Cloudflare output and is never retained or assembled.
  visit('dist/client'); visit('dist/cloudflare');
  need(result.some(row => row.path === 'dist/client/atlas-geography.json') &&
    result.some(row => row.path === 'dist/cloudflare/index.js') &&
    result.some(row => row.path === 'dist/cloudflare/wrangler.json'), 'Incomplete Cloudflare output');
  return {files: result, bytes: total};
}

const git = (root, args) => execFileSync('git', ['-C', root, ...args], {encoding: 'utf8',
  maxBuffer: 32 * 1024 * 1024, env: {...process.env, GIT_NO_LAZY_FETCH: '1', GIT_TERMINAL_PROMPT: '0'}});
export function committedPackageInputs(root, definition = loadPackageInputs(root), head = 'HEAD') {
  const rows = git(root, ['ls-tree', '-rz', '--full-tree', head]).split('\0').filter(Boolean).map(line => {
    const tab = line.indexOf('\t'), [mode, type, oid] = line.slice(0, tab).split(' ');
    return {path: line.slice(tab + 1), mode, type, oid};
  }).filter(row => containsPackagePath(definition.inputs, row.path));
  need(rows.length > 0 && rows.length <= 20000 && rows.every(row => row.type === 'blob' &&
    ['100644','100755'].includes(row.mode) && commit(row.oid)), 'Complete ordinary package source tree required');
  for (const name of definition.inputs) need(definition.optional_inputs.includes(name) ||
    rows.some(row => containsPackagePath([name], row.path)), 'Declared input absent from original tree');
  return rows.map(({type, ...row}) => row).sort((a, b) => a.path.localeCompare(b.path, 'en'));
}

function readJSON(root, relative) {
  const file = ordinary(root, relative), stat = fs.statSync(file);
  need(stat.size > 0 && stat.size <= MAX_METADATA, 'Bounded whole package metadata required');
  return JSON.parse(fs.readFileSync(file));
}

export function packageBuildConfiguration(env = process.env) {
  return Object.fromEntries(Object.entries(env).filter(([key]) => /^(ATLAS_|VITE_)/.test(key) ||
    ['NODE_ENV','TZ','LANG','LC_ALL','SOURCE_DATE_EPOCH'].includes(key)).sort(([a], [b]) => a.localeCompare(b, 'en')));
}

export const packageProducerPath = name => name !== '.github/package-inputs.json' &&
  (!name.includes('/') || /^(?:scripts|test|src|hosted|\.github)\//.test(name) || /\.(?:mjs|cjs|js|py|sh)$/.test(name));
export function committedPackageProgramme(root, head = 'HEAD') {
  return git(root, ['ls-tree','-rz','--full-tree',head]).split('\0').filter(Boolean).map(line => {
    const tab=line.indexOf('\t'),[mode,type,oid]=line.slice(0,tab).split(' ');
    return {path:line.slice(tab+1),mode,type,oid};
  }).filter(row=>packageProducerPath(row.path)).map(({type,...row})=>{
    need(type==='blob'&&['100644','100755'].includes(row.mode)&&commit(row.oid),'Ordinary complete producer programme required');return row;
  }).sort((a,b)=>a.path.localeCompare(b.path,'en'));
}

export function installedPackageIdentity(root, pythonImports = []) {
  const rows=[];
  const visit=relative=>{
    const file=path.join(root,relative),stat=fs.lstatSync(file);
    if(stat.isSymbolicLink()){
      const target=fs.realpathSync(file),base=fs.realpathSync(path.join(root,'node_modules'));
      need(target.startsWith(base+path.sep),'Installed dependency link escapes installation');
      rows.push({path:relative,link:fs.readlinkSync(file)});
    }else if(stat.isDirectory()){
      for(const name of fs.readdirSync(file).sort())visit(relative+'/'+name);
    }else{
      need(stat.isFile(),'Ordinary installed dependency required');
      rows.push({...streamedPackageFile(root,relative),mode:stat.mode&0o111?'100755':'100644'});
    }
  };
  visit('node_modules');
  const runtime=streamedPackageFile(path.dirname(process.execPath),path.basename(process.execPath));
  const python=pythonImports.length?JSON.parse(execFileSync('python3',['-I','-B','-c',`
import hashlib,importlib.metadata,json,pathlib,re,sys
rows=[]; seen=set(); pending=json.loads(sys.argv[1])
def digest(file,bytecode=False):
 h=hashlib.sha256()
 with open(file,'rb') as source:
  if bytecode: source.read(16)
  while True:
   chunk=source.read(1048576)
   if not chunk: break
   h.update(chunk)
 return h.hexdigest()
while pending:
 name=pending.pop().lower().replace('_','-')
 if name in seen: continue
 seen.add(name); distribution=importlib.metadata.distribution(name)
 for dependency in distribution.requires or []:
  child=re.match(r'[A-Za-z0-9_.-]+',dependency).group()
  try: importlib.metadata.distribution(child); pending.append(child)
  except importlib.metadata.PackageNotFoundError: pass
 for member in distribution.files or []:
  file=pathlib.Path(distribution.locate_file(member))
  if not file.is_file(): raise ValueError('Installed Python member missing')
  # Cache header timestamps are transport metadata; the actual marshalled
  # executable bytecode is still hashed, along with every original source file.
  rows.append([name,str(member),file.stat().st_size,digest(file,str(member).endswith('.pyc'))])
rows.sort(); binary=pathlib.Path(sys.executable).resolve()
print(json.dumps({'executable_sha256':digest(binary),'files':len(rows),'sha256':hashlib.sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()}))
`,JSON.stringify(pythonImports.map(row=>row.name))],{encoding:'utf8',maxBuffer:1048576,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}})):null;
  return {node:{bytes:runtime.bytes,sha256:runtime.sha256},dependencies:{files:rows.length,
    bytes:rows.reduce((n,row)=>n+(row.bytes??0),0),sha256:sha(JSON.stringify(rows))},python};
}

export function snapshotPackageOutputSource(root = process.cwd()) {
  root = fs.realpathSync(root);
  const definition = loadPackageInputs(root), files = committedPackageInputs(root, definition);
  // Match the actual image the full builder will copy, including directory
  // members and optional absence. Git diff alone misses untracked input files.
  const actual=[];
  const visit=name=>{
    const file=ordinary(root,name),stat=fs.lstatSync(file);
    const fd=fs.openSync(file,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW);
    const digest=createHash('sha1').update(`blob ${stat.size}\0`),buffer=Buffer.alloc(1048576);
    let bytes=0;
    try { for(;;){const count=fs.readSync(fd,buffer,0,buffer.length,null);if(!count)break;bytes+=count;digest.update(buffer.subarray(0,count));} }
    finally {fs.closeSync(fd);}
    need(bytes===stat.size,'Source member changed while inventorying');
    actual.push({path:name,mode:stat.mode&0o111?'100755':'100644',oid:digest.digest('hex')});
  };
  const walk=name=>{
    ordinary(root,name,true);
    for(const part of fs.readdirSync(path.join(root,name))){
      const child=name+'/'+part,stat=fs.lstatSync(path.join(root,child));
      if(stat.isDirectory()&&!stat.isSymbolicLink())walk(child);else visit(child);
    }
  };
  for(const input of definition.inputs){
    if(!fs.existsSync(path.join(root,input))){need(definition.optional_inputs.includes(input),'Required original input absent');continue;}
    if(input.endsWith('/'))walk(input.slice(0,-1));else visit(input);
  }
  actual.sort((a,b)=>a.path.localeCompare(b.path,'en'));
  need(same(actual,files),'Actual original source image differs from complete immutable inventory');
  const head = git(root, ['rev-parse','HEAD']).trim(), tree = git(root, ['rev-parse','HEAD^{tree}']).trim();
  return {head, tree, input_definition_sha256: sha(fs.readFileSync(path.join(root, '.github/package-inputs.json'))),
    definition, files, programme: committedPackageProgramme(root), selection: readJSON(root, 'data/ownership-selection.json')};
}

export function createPackageOutputManifest(root = process.cwd()) {
  root = fs.realpathSync(root);
  const receipt = readJSON(root, '.cache/package-input-build.json');
  const head = git(root, ['rev-parse','HEAD']).trim(), tree = git(root, ['rev-parse','HEAD^{tree}']).trim();
  need(receipt.version === 1 && receipt.kind === 'cloudflare' && receipt.preflight?.passed === true &&
    same(receipt.preflight.errors, []) && receipt.preflight.inputs?.head === head && commit(head) && commit(tree),
    'Actual successful original Cloudflare build receipt required');
  need(!receipt.assembly, 'An assembled package cannot be relabelled as an original full build');
  const definition = loadPackageInputs(root), definitionRaw = fs.readFileSync(path.join(root, '.github/package-inputs.json'));
  need(receipt.input_definition_sha256 === sha(definitionRaw), 'Original package definition changed');
  const source = readJSON(root, OUTPUT_SOURCE);
  need(source.head === head && source.tree === tree && source.input_definition_sha256 === sha(definitionRaw) &&
    same(source.definition, definition) && same(source.files, committedPackageInputs(root, definition)) &&
    same(source.programme, committedPackageProgramme(root)),
    'Original pre-build source snapshot differs');
  const output = inventoryPackageOutput(root);
  const manifest = {version: 1, kind: 'original-cloudflare-package-output', source,
    runtime: {installed: installedPackageIdentity(root,receipt.preflight.runtime?.python?.imports??[]), node: process.version, versions: process.versions, platform: process.platform, arch: process.arch,
      dependencies: streamedPackageFile(root, 'package-lock.json', MAX_METADATA).sha256,
      python: {version:receipt.preflight.runtime?.python?.version??null,imports:receipt.preflight.runtime?.python?.imports??[]}},
    configuration: packageBuildConfiguration(), output,
    original_build_receipt: streamedPackageFile(root, '.cache/package-input-build.json', MAX_METADATA),
    semantics: 'Original full package output, retained without claiming a fresh build when reused.'};
  validatePackageOutputManifest(manifest);
  return manifest;
}

export function validatePackageOutputManifest(value) {
  need(value?.version === 1 && value.kind === 'original-cloudflare-package-output' &&
    commit(value.source?.head) && commit(value.source?.tree) && hash(value.source?.input_definition_sha256) &&
    Array.isArray(value.source.files) && value.source.files.length > 0 && value.source.files.length <= 20000,
    'Invalid original package identity');
  validatePackageInputs(value.source.definition);
  need(value.source.selection && typeof value.source.selection === 'object' &&
    value.runtime && typeof value.runtime.node === 'string' && typeof value.runtime.platform === 'string' &&
    typeof value.runtime.arch === 'string' && hash(value.runtime.dependencies) &&
    hash(value.runtime.installed?.node?.sha256) && hash(value.runtime.installed?.dependencies?.sha256) &&
    value.configuration && typeof value.configuration === 'object' && !Array.isArray(value.configuration) &&
    Object.values(value.configuration).every(item => typeof item === 'string'), 'Missing original runtime/configuration');
  const sources = new Set();
  for (const row of value.source.files) {
    need(safePackagePath(row.path) && !sources.has(row.path) && ['100644','100755'].includes(row.mode) && commit(row.oid),
      'Duplicate or invalid original package input'); sources.add(row.path);
  }
  need(Array.isArray(value.output?.files) && value.output.files.length > 0 &&
    value.output.files.length <= PACKAGE_OUTPUT_LIMITS.files && positive(value.output.bytes) &&
    value.output.bytes <= PACKAGE_OUTPUT_LIMITS.total_bytes, 'Invalid original output inventory');
  const outputs = new Set(); let bytes = 0;
  for (const row of value.output.files) {
    need(safePackagePath(row.path) && /^dist\/(client|cloudflare)\//.test(row.path) && !outputs.has(row.path) &&
      Number.isSafeInteger(row.bytes) && row.bytes >= 0 && row.bytes <= PACKAGE_OUTPUT_LIMITS.member_bytes && hash(row.sha256),
      'Duplicate, unsafe or oversized original output'); outputs.add(row.path); bytes += row.bytes;
  }
  need(bytes === value.output.bytes && ['dist/client/atlas-geography.json','dist/cloudflare/index.js',
    'dist/cloudflare/wrangler.json'].every(name => outputs.has(name)), 'Incomplete original package inventory');
  need(Buffer.byteLength(JSON.stringify(value)) <= MAX_METADATA, 'Original package metadata exceeds admission');
  return value;
}

export function verifyPackageOutput(root, manifest) {
  validatePackageOutputManifest(manifest);
  need(same(inventoryPackageOutput(root), manifest.output), 'Retained package complete output bytes differ');
  return true;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  need(process.argv.length === 2 || process.argv.length === 3 && process.argv[2] === '--snapshot',
    'Use node scripts/package-output-artifact.mjs [--snapshot]');
  if (process.argv[2] === '--snapshot') {
    fs.mkdirSync('.cache', {recursive: true});
    fs.writeFileSync(OUTPUT_SOURCE, JSON.stringify(snapshotPackageOutputSource()) + '\n', {flag: 'wx'});
    process.exit(0);
  }
  const manifest = createPackageOutputManifest();
  const raw = Buffer.from(JSON.stringify(manifest) + '\n');
  fs.writeFileSync(OUTPUT_MANIFEST, raw, {flag: 'wx'});
  console.log(JSON.stringify({package_output_manifest_sha256: sha(raw), package_output_manifest_bytes: raw.length,
    package_output_files: manifest.output.files.length, package_output_bytes: manifest.output.bytes,
    original_head: manifest.source.head}));
}

// Original producer -> current selection, independently of PR-base -> head
// classification. New directory members and implicit optional inputs are never
// waved through by an append-only package-definition change.
export function admitPackageOutputTransition(original, current, authorizedAdditions) {
  validatePackageOutputManifest(original); validatePackageInputs(current.definition);
  const before=original.source, allowed=new Set(authorizedAdditions);
  need(Array.isArray(before.programme)&&before.programme.length>0&&same(before.programme,current.programme),
    'Original producer/test/workflow programme changed');
  const {inputs:oldInputs,...oldPolicy}=before.definition,{inputs:newInputs,...newPolicy}=current.definition;
  need(same(oldPolicy,newPolicy)&&newInputs.length>=oldInputs.length&&same(oldInputs,newInputs.slice(0,oldInputs.length)),
    'Package definition is not an append-only selected change');
  const {additive_release:oldAdditive,...oldBase}=before.selection;
  const {additive_release:newAdditive,...newBase}=current.selection;
  need(same(oldBase,newBase)&&oldAdditive&&newAdditive,'Original invariant selection differs');
  const oldFiles=new Map(before.files.map(row=>[row.path,row])),newFiles=new Map(current.files.map(row=>[row.path,row]));
  need(newFiles.size===current.files.length,'Duplicate current input');
  const exceptions=new Set(['.github/package-inputs.json','data/ownership-selection.json']);
  for(const [name,row] of oldFiles) need(newFiles.has(name)&&(exceptions.has(name)||same(row,newFiles.get(name))),
    'Original invariant package input changed: '+name);
  const newDeclarations=newInputs.slice(oldInputs.length);
  need(newDeclarations.every(name=>!name.endsWith('/')&&/^coordination\/engineering\/[^/]+\/.+\.(?:json|jsonl\.gz|json\.gz|log)$/.test(name)&&allowed.has(name)),
    'New package declaration is not explicitly authenticated selected data');
  const added=[];
  for(const [name,row] of newFiles)if(!oldFiles.has(name)){
    need(row.mode==='100644'&&newDeclarations.includes(name)&&allowed.has(name),
      'Unadmitted new invariant/directory/optional package input: '+name);added.push(name);
  }
  need(newDeclarations.every(name=>newFiles.has(name)), 'New selected declaration is absent');
  return {original_head:before.head,current_head:current.head,invariant_files:oldFiles.size-exceptions.size,
    added_selected_inputs:added.sort(),base_selection:oldBase};
}
