import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {environmentClassifications} from '../src/environment-classifications.js';

const marker='-- Fixed environmental classification guards: generated from src/environment-classifications.js.';
const quote=value=>`'${value.replaceAll("'","''")}'`;
const values=attribute=>[...new Set(environmentClassifications[attribute].flatMap(entry=>[entry.id,entry.label,...entry.aliases]))];
const allowed=attribute=>values(attribute).map(quote).join(',');
const exactRetry=(table,columns)=>`NOT EXISTS(SELECT 1 FROM ${table} retained WHERE ${columns.map(column=>`retained.${column} IS NEW.${column}`).join(' AND ')})`;
const classificationGuard=(attribute,expression,extra='')=>` SELECT RAISE(ABORT,'Invalid fixed ${attribute} classification') WHERE ${extra}${expression} IS NOT NULL AND ${expression} NOT IN (${allowed(attribute)});`;
const recordGuards=()=>Object.keys(environmentClassifications).map(attribute=>classificationGuard(attribute,"json_extract(NEW.value,'$')",`NEW.attribute=${quote(attribute)} AND json_type(NEW.value)='text' AND length(trim(json_extract(NEW.value,'$'),char(9,10,11,12,13,32,160,5760,8192,8193,8194,8195,8196,8197,8198,8199,8200,8201,8202,8232,8233,8239,8287,12288,65279)))>0 AND `)).join('\n');
const snapshotGuards=(history=false,update=false)=>Object.keys(environmentClassifications).map(attribute=>{
 const expression=history?`json_extract(NEW.value,'$.${attribute}')`:`NEW.${attribute}`;
 const previous=history?`json_extract(OLD.value,'$.${attribute}')`:`OLD.${attribute}`;
 return classificationGuard(attribute,expression,update?`(${history?"OLD.field!='attributes' OR ":''}${expression} IS NOT ${previous}) AND `:'');
}).join('\n');

export function hostedEnvironmentGuardSql(){return `${marker}
-- Retained legacy claims are not rewritten. Identical-ID retries continue through
-- the existing byte-exact collision guard; genuinely new values use this registry.
CREATE TRIGGER atlas_environment_classification BEFORE INSERT ON atlas_attribute_records
WHEN NOT EXISTS(SELECT 1 FROM atlas_attribute_records WHERE id=NEW.id)
BEGIN
${recordGuards()}
END;
`;}

export function localEnvironmentGuardSql(){return `${marker}
-- Existing free-form evidence remains retained; guard new claims and changed values.
DROP TRIGGER IF EXISTS attribute_environment_classification;
CREATE TRIGGER attribute_environment_classification BEFORE INSERT ON attribute_records
WHEN ${exactRetry('attribute_records',['id','location_id','attribute','value','category_id','valid_from','valid_to','method','status','source','is_example','metadata'])}
BEGIN
${recordGuards()}
END;
DROP TRIGGER IF EXISTS states_environment_classification;
CREATE TRIGGER states_environment_classification BEFORE INSERT ON states
WHEN ${exactRetry('states',['id','location_id','valid_from','valid_to','owner','population','culture','religion','topography','vegetation','climate','rank','is_example','source'])}
BEGIN
${snapshotGuards()}
END;
DROP TRIGGER IF EXISTS states_environment_classification_update;
CREATE TRIGGER states_environment_classification_update BEFORE UPDATE OF topography,vegetation,climate ON states
BEGIN
${snapshotGuards(false,true)}
END;
DROP TRIGGER IF EXISTS entity_history_environment_classification;
CREATE TRIGGER entity_history_environment_classification BEFORE INSERT ON entity_history
WHEN NEW.field='attributes' AND ${exactRetry('entity_history',['id','entity_id','field','valid_from','valid_to','language','name_role','value','source','is_example'])}
BEGIN
${snapshotGuards(true)}
END;
DROP TRIGGER IF EXISTS entity_history_environment_classification_update;
CREATE TRIGGER entity_history_environment_classification_update BEFORE UPDATE OF field,value ON entity_history
WHEN NEW.field='attributes'
BEGIN
${snapshotGuards(true,true)}
END;
`;}

export function compileEnvironmentGuards({check=true}={}){
 const migration=new URL('../drizzle/0007_fixed_environment_classifications.sql',import.meta.url),schema=new URL('../data/schema.sql',import.meta.url);
 const current=fs.readFileSync(schema,'utf8'),start=current.indexOf(marker),base=(start===-1?current:current.slice(0,start)).trimEnd();
 const outputs=[[migration,hostedEnvironmentGuardSql()],[schema,`${base}\n\n${localEnvironmentGuardSql()}`]];
 for(const [target,sql]of outputs){if(check){if(!fs.existsSync(target)||fs.readFileSync(target,'utf8')!==sql)throw Error(`Environmental SQL registry is stale: ${fileURLToPath(target)}`);}else fs.writeFileSync(target,sql);}
 return {migration:fileURLToPath(migration),attributes:Object.fromEntries(Object.keys(environmentClassifications).map(attribute=>[attribute,environmentClassifications[attribute].length]))};
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 if(process.argv.slice(2).some(arg=>arg!=='--check'))throw Error('Usage: node scripts/compile-environment-classification-guards.mjs [--check]');
 // Published migrations are immutable: CLI invocation only verifies parity.
 console.log(JSON.stringify(compileEnvironmentGuards({check:true})));
}
