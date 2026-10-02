import fs from 'node:fs';
import { openDatabase, seedDatabase, importRecords } from '../database.mjs';
const path = process.argv[2];
if (!path) { console.error('Usage: npm run data:import -- records.json'); process.exit(1); }
const db = openDatabase();
try { seedDatabase(db); importRecords(db, JSON.parse(fs.readFileSync(path, 'utf8'))); console.log('Import committed. Restart the server to reload geography.'); }
catch (error) { console.error(`Import rejected: ${error.message}`); process.exitCode = 1; }
finally { db.close(); }
