import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {runPackageBuild} from './package-build.mjs';
export {cloudflareConfig} from './build-cloudflare-inner.mjs';
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await runPackageBuild('cloudflare');
