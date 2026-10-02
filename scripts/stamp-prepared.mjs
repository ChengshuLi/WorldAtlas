import fs from 'node:fs';
import {footprintHash} from './check-prepared.mjs';
const features=JSON.parse(fs.readFileSync('data/world-index.json')).parts.flatMap(p=>JSON.parse(fs.readFileSync('data/'+p)).features),hash=footprintHash(features),args=process.argv.slice(2);
if(args[0]==='--hash'){console.log(hash);process.exit(0);}
if(args[1]&&args[1]!==hash)throw Error('Footprints changed during preparation; rerun the stage');
for(const name of args[0]?[args[0]]:['ownership-history','reference-attributes']){const path=`data/${name}/index.json`,index=JSON.parse(fs.readFileSync(path));if(index.locations&&index.locations!==features.length)throw Error('Prepared location count changed');index.footprints_sha256=hash;index.locations=features.length;fs.writeFileSync(path,JSON.stringify(index));}
