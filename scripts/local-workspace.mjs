import {assertAuthorWorkerIdentity} from './worker-identity.mjs';
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash, randomUUID} from 'node:crypto';
import {fileURLToPath} from 'node:url';

export const GiB = 1024 ** 3;
export const policy = {minimumFree: 10 * GiB};
const support = ['docs', 'scripts', 'test', 'src', 'hosted', 'drizzle', '.github', '.agents', 'coordination/templates'];
const id = value => typeof value === 'string' && /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$/.test(value);
const safeInclude = value => typeof value === 'string' && /^(data|research|coordination)\/[a-zA-Z0-9_./-]+$/.test(value)
  && value.split('/').every(part => part && part !== '.' && part !== '..');

// No shell, background mutations, timeout retries, or automatic lock breaking.
export function workspaceManager(repo, {limits = policy, freeBytes} = {}) {
  const git = (...args) => execFileSync('git', ['-C', repo, ...args], {encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
  const common = fs.realpathSync(git('rev-parse', '--path-format=absolute', '--git-common-dir').trim());
  const registry = path.join(common, 'worldatlas-local-workspaces');
  const root = path.resolve(common, '../../.worldatlas-workspaces', createHash('sha256').update(common).digest('hex').slice(0, 16));
  const stateFile = path.join(registry, 'state.json');
  const lock = path.join(registry, 'lock');
  const state = () => {
    if (!fs.existsSync(stateFile)) return {version: 1, entries: []};
    if (!fs.lstatSync(stateFile).isFile() || fs.lstatSync(stateFile).isSymbolicLink()) throw Error('Registry must be an ordinary file');
    const value = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
    if (value.version !== 1 || !Array.isArray(value.entries)) throw Error('Unknown workspace registry; inspect manually');
    for (const entry of value.entries) {
      if (!id(entry.worker) || !['work', 'review'].includes(entry.slot) || !id(entry.token)
        || entry.path !== slotPath(entry.worker, entry.slot) || !Number.isSafeInteger(entry.reservation)
        || entry.reservation < 0 || !/^[a-f0-9]{40}$/.test(entry.head)) throw Error('Invalid workspace registry; inspect manually');
    }
    if (new Set(value.entries.map(entry => entry.path)).size !== value.entries.length) throw Error('Duplicate workspace registry entries');
    return value;
  };
  const save = value => {
    const temporary = `${stateFile}.${randomUUID()}.tmp`;
    fs.writeFileSync(temporary, JSON.stringify(value, null, 2) + '\n', {flag: 'wx'});
    fs.renameSync(temporary, stateFile);
  };
  const slotPath = (worker, slot) => path.join(root, createHash('sha256').update(worker).digest('hex'), slot);
  const ordinaryDirectory = directory => {
    for (let current = directory; current !== path.dirname(current); current = path.dirname(current)) {
      if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw Error(`Symlink directory refused: ${current}`);
    }
  };
  const locked = operation => {
    ordinaryDirectory(registry);
    fs.mkdirSync(registry, {recursive: true});
    try { fs.mkdirSync(lock); } catch (error) {
      if (error.code === 'EEXIST') throw Error('Workspace allocation is locked; retry later. Never break a lock without operator inspection.');
      throw error;
    }
    try { return operation(); } finally { fs.rmdirSync(lock); }
  };
  const worktrees = (measure = true) => git('worktree', 'list', '--porcelain').trim().split('\n\n').map(block => {
    const lines = block.split('\n');
    const directory = lines.find(line => line.startsWith('worktree '))?.slice(9);
    if (!directory) throw Error('Incomplete worktree inventory');
    ordinaryDirectory(directory);
    if (!measure) return {path: directory};
    // Missing/prunable paths need explicit inspection; they are not zero-cost proof.
    const bytes = Number(execFileSync('du', ['-sk', directory], {encoding: 'utf8'}).split(/\s/)[0]) * 1024;
    if (!Number.isSafeInteger(bytes) || bytes < 0) throw Error('Unknown checkout usage');
    return {path: directory, bytes};
  });
  const report = () => {
    const value = state();
    const inventory = worktrees();
    let checkoutBytes = 0;
    for (const item of inventory) {
      const entry = value.entries.find(entry => entry.path === item.path);
      checkoutBytes += Math.max(item.bytes, entry?.reservation ?? 0);
      item.managed = Boolean(entry);
    }
    for (const entry of value.entries) {
      if (!inventory.some(item => item.path === entry.path)) checkoutBytes += entry.reservation;
    }
    const stats = fs.statfsSync(common);
    const available = freeBytes ? freeBytes() : stats.bavail * stats.bsize;
    return {root, registry, freeBytes: available, checkoutBytes, limits, entries: value.entries, worktrees: inventory};
  };
  const allocate = ({worker, slot = 'work', branch, commit, profile = 'sparse', include = [], reserveGiB = 1}) => locked(() => {
    if (!id(worker) || !['work', 'review'].includes(slot)) throw Error('Supply a safe unique worker ID and work/review slot');
    if (!['sparse', 'full'].includes(profile) || !Array.isArray(include) || !include.every(safeInclude)) throw Error('Use sparse/full profile and literal data/research/coordination paths without traversal or globs');
    if (!Number.isFinite(reserveGiB) || reserveGiB <= 0 || !Number.isSafeInteger(Math.ceil(reserveGiB * GiB))) throw Error('Reserve must be positive and represent a safe finite byte count');
    if (slot === 'work' && (!/^(engineering|geography|research)\/[a-z0-9][a-z0-9-]{0,63}$/.test(branch ?? '') || commit)) throw Error('Work needs a fresh lane branch; main is fetched by the allocator');
    if (slot === 'review' && (branch || !/^[a-f0-9]{40}$/.test(commit ?? ''))) throw Error('Review needs an exact detached 40-character commit');
    const value = state();
    if (value.entries.some(entry => entry.worker === worker && entry.slot === slot)) throw Error('Slot occupied; finish and release it before allocating another checkout');
    const destination = slotPath(worker, slot);
    ordinaryDirectory(destination);
    if (fs.existsSync(destination)) throw Error('Unregistered checkout directory exists; inspect instead of overwriting');
    if (slot === 'work') git('fetch', 'origin', 'main');
    const head = git('rev-parse', '--verify', `${slot === 'work' ? 'origin/main' : commit}^{commit}`).trim();
    const selected = [...support, ...include];
    const tree = git('ls-tree', '-rlz', head).split('\0').filter(Boolean);
    let estimated = 0;
    for (const line of tree) {
      const separator = line.indexOf('\t');
      const name = line.slice(separator + 1);
      if (profile === 'full' || !name.includes('/') || selected.some(prefix => name === prefix || name.startsWith(prefix + '/'))) {
        const size = line.slice(0, separator).trim().split(/\s+/)[3];
        if (size === '-') throw Error('Submodule inputs need a separate bounded plan');
        if (!Number.isSafeInteger(Number(size))) throw Error('Unknown input size');
        estimated += Number(size);
      }
    }
    const reservation = Math.max(Math.ceil(reserveGiB * GiB), estimated);
    if (!Number.isSafeInteger(reservation)) throw Error('Reserve and selected inputs must represent a safe finite byte count');
    const usage = report();
    if (usage.freeBytes - reservation < limits.minimumFree) throw Error('Insufficient disk headroom; release completed workspaces before allocation');
    const entry = {worker, slot, path: destination, token: randomUUID(), head, branch: branch ?? null,
      profile, include, reservation, status: 'preparing', createdAt: new Date().toISOString()};
    value.entries.push(entry);
    save(value); // Preserve interrupted attempts for inspection, even if Git fails below.
    fs.mkdirSync(path.dirname(destination), {recursive: true});
    git('worktree', 'add', '--no-checkout', ...(slot === 'work' ? ['-b', branch] : ['--detach']), destination, head);
    if (profile === 'sparse') {
      execFileSync('git', ['-C', destination, 'sparse-checkout', 'set', '--no-cone', '--stdin'], {
        input: ['/*', '!/*/', ...selected.map(prefix => `/${prefix}${tree.some(line => line.slice(line.indexOf('\t') + 1).startsWith(prefix + '/')) ? '/' : ''}`)].join('\n') + '\n', encoding: 'utf8'});
    }
    execFileSync('git', ['-C', destination, 'read-tree', '-mu', 'HEAD']);
    entry.status = 'ready';
    save(value);
    return entry;
  });
  const release = ({worker, slot = 'work', token}) => locked(() => {
    const value = state();
    const entry = value.entries.find(entry => entry.worker === worker && entry.slot === slot);
    if (!entry || entry.token !== token) throw Error('Exact current slot ownership token required');
    if (entry.status !== 'ready') throw Error('Interrupted workspace needs operator inspection; automatic release refused');
    ordinaryDirectory(entry.path);
    const inventory = worktrees(false);
    if (!inventory.some(item => item.path === entry.path)) throw Error('Managed checkout missing; inspect registry');
    const localGit = (...args) => execFileSync('git', ['-C', entry.path, ...args], {encoding: 'utf8', maxBuffer: 32 * 1024 * 1024});
    if (localGit('rev-parse', '--path-format=absolute', '--git-common-dir').trim() !== common) throw Error('Checkout Git identity changed');
    for (const row of localGit('ls-files', '-vz').split('\0').filter(Boolean)) {
      // Git status/remove can trust assume-unchanged and skip-worktree bits.
      // Absent uppercase S entries are normal sparse omissions, not dirty work.
      if (/[a-z]/.test(row[0]) || row[0] === 'S' && fs.lstatSync(path.join(entry.path, row.slice(2)), {throwIfNoEntry: false})) {
        throw Error('Index trust flags can hide edits; inspect materialized files and clear flags before cleanup');
      }
    }
    if (localGit('status', '--porcelain', '--untracked-files=all') || localGit('ls-files', '--others', '--ignored', '--exclude-standard')) throw Error('Workspace contains uncommitted, untracked or ignored files; preserve unique work and remove only verified generated artifacts first');
    const head = localGit('rev-parse', 'HEAD').trim();
    const preservedRef = `refs/worldatlas-local-recovery/${entry.token}`;
    git('update-ref', preservedRef, head);
    // Git's own dirty/in-use worktree guards remain enabled; no --force.
    git('worktree', 'remove', entry.path);
    value.entries = value.entries.filter(item => item !== entry);
    save(value);
    return {released: true, path: entry.path, preservedRef, head};
  });
  const check = () => {
    const usage = report();
    if (usage.freeBytes < limits.minimumFree) throw Error('Local storage budget breached; stop new generation/installations and inspect report');
    return usage;
  };
  const ownedEntry = directory => state().entries.find(entry => entry.path === directory && entry.slot === 'work');
  return {report, check, allocate, release, ownedEntry};
}

// Called only after the queue verifies its accepted receipt against actual GitHub
// merged state. Local cleanup is separate from successful remote integration.
export function cleanupCompletedWorkspace(repo, expectedHead) {
  try {
    const manager = workspaceManager(repo);
    const current = fs.realpathSync(execFileSync('git', ['-C', repo, 'rev-parse', '--show-toplevel'], {encoding: 'utf8'}).trim());
    const entry = manager.ownedEntry(current);
    if (!entry) return {status: 'unmanaged', reason: 'No owned managed author slot; legacy checkout retained'};
    const head = execFileSync('git', ['-C', repo, 'rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
    const branch = execFileSync('git', ['-C', repo, 'symbolic-ref', '--short', 'HEAD'], {encoding: 'utf8'}).trim();
    if (head !== expectedHead || branch !== entry.branch) return {status: 'retained', reason: 'Checkout advanced or changed branch since reviewed merge'};
    return {status: 'released', ...manager.release({worker: entry.worker, slot: entry.slot, token: entry.token})};
  } catch (error) {
    return {status: 'pending', reason: error.message};
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [action, ...args] = process.argv.slice(2);
    const options = {include: []};
    for (let index = 0; index < args.length; index += 2) {
      const key = args[index]?.replace(/^--/, '');
      if (!['worker', 'slot', 'branch', 'commit', 'profile', 'include', 'token', 'reserve-gib'].includes(key) || !args[index + 1]) throw Error('Use report, allocate or release with documented --key value arguments');
      if (key === 'include') options.include.push(args[index + 1]);
      else if (Object.hasOwn(options, key)) throw Error(`Duplicate ${key}`);
      else options[key] = args[index + 1];
    }
    if (options['reserve-gib']) options.reserveGiB = Number(options['reserve-gib']);
    if (action === 'allocate' && (options.slot ?? 'work') === 'work') assertAuthorWorkerIdentity(options.worker);
    const manager = workspaceManager(process.cwd());
    if (!['report', 'check', 'allocate', 'release'].includes(action)) throw Error('Choose report, check, allocate or release');
    console.log(JSON.stringify(manager[action](options), null, 2));
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
