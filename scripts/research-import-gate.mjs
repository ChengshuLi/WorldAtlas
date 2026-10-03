import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
export {assertResearchImportsReady,assertResearchBundleApproved} from '../src/regional-import-gate.js';
export function readResearchImportGate(){return JSON.parse(fs.readFileSync(fileURLToPath(new URL('../data/research-geography-gate.json',import.meta.url)),'utf8'));}
