// Standalone entry for the same mandatory package wrapper preflight.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {preflightPackageBuild} from './package-build.mjs';
export {inspectPackageInputs, inspectPackageAncestry, inspectPackageExecutionInputs, inspectPackageRuntime, inspectPackageBrowser, preflightPackageBuild, requirePackagePreflight} from './package-build.mjs';

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const options = {}, args = process.argv.slice(2);
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i]?.replace(/^--/, ''), value = args[i + 1];
    if (!['root', 'kind', 'browser', 'python', 'out', 'ancestor'].includes(key) || !value) throw Error('Use --root DIR --kind static|hosted|cloudflare --browser probe|required|off --python EXE --ancestor COMMIT --out NEW_FILE');
    if (key === 'ancestor') (options.requiredAncestors ??= []).push(value); else if (Object.hasOwn(options, key)) throw Error('Duplicate option'); else options[key] = value;
  }
  if (options.out) {
    try { fs.lstatSync(options.out); throw Error('Preflight output already exists'); } catch (error) { if (error.code !== 'ENOENT') throw error; }
    for (let parent = path.dirname(path.resolve(options.out)); parent !== path.dirname(parent); parent = path.dirname(parent)) {
      const stat = fs.lstatSync(parent); if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error('Preflight output has nonordinary parent');
    }
  }
  const report = await preflightPackageBuild(options);
  const raw = JSON.stringify(report, null, 2) + '\n';
  if (options.out) fs.writeFileSync(options.out, raw, {flag: 'wx'});
  console.log(raw); if (!report.passed) process.exitCode = 1;
}
