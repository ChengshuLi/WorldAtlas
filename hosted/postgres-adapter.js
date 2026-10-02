import {neon} from '@neondatabase/serverless';

const knownIndexes=new Set(['entities_kind_id','attributes_location_dates','names_entity_dates']);
const sqliteOnlyFunctions=new Set(['json_object','typeof']);
const numericDateFields=new Set(['valid_from','valid_to','supported_from','supported_to','source_from','source_to']);
const ingestionLock={query:'SELECT pg_advisory_xact_lock(807245315,1)',params:[]};

export class PostgresAdapterError extends Error {
 constructor(message,{code=null,status=503,retryable=false,commitStatus}={}){
  super(message);this.name='PostgresAdapterError';this.code=code;this.sqlstate=/^[0-9A-Z]{5}$/.test(code??'')?code:null;this.status=status;
  if(retryable)this.retryable=true;if(commitStatus)this.commit_status=commitStatus;
 }
}
const invalid=message=>{throw new PostgresAdapterError(message,{status:400});};

/** SQL lexer protects strings, quoted identifiers, dollar bodies and comments.
 * This adapter translates only a short reviewed set of service-query syntax;
 * PostgreSQL metadata expressions belong in explicit dialect-specific queries.
 */
function tokens(sql){
 if(typeof sql!=='string'||!sql.trim()||sql.length>256*1024)invalid('Invalid PostgreSQL service statement');
 const result=[];let i=0;
 while(i<sql.length){
  const start=i,c=sql[i];let type='punct';
  if(/\s/.test(c)){type='space';while(i<sql.length&&/\s/.test(sql[i]))i++;}
  else if(sql.startsWith('--',i)){type='comment';i=sql.indexOf('\n',i+2);if(i<0)i=sql.length;}
  else if(sql.startsWith('/*',i)){type='comment';i+=2;let depth=1;while(i<sql.length&&depth){if(sql.startsWith('/*',i)){depth++;i+=2;}else if(sql.startsWith('*/',i)){depth--;i+=2;}else i++;}if(depth)invalid('Unterminated SQL comment');}
  else if(c==="'"||c==='"'){
   type=c==="'"?'literal':'identifier';const escapes=c==="'"&&start>0&&/[eE]/.test(sql[start-1])&&(start<2||!/[\w$]/.test(sql[start-2]));i++;let closed=false;
   while(i<sql.length){if(escapes&&sql[i]==='\\'){i+=2;continue;}if(sql[i]===c){if(sql[i+1]===c){i+=2;continue;}i++;closed=true;break;}i++;}if(!closed)invalid('Unterminated SQL quoted value');
  }
  else if(c==='$'&&/^\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$/.test(sql.slice(i))){type='literal';const tag=sql.slice(i).match(/^\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$/)[0],end=sql.indexOf(tag,i+tag.length);if(end<0)invalid('Unterminated SQL dollar quote');i=end+tag.length;}
  else if(c==='$'&&/^\$\d+/.test(sql.slice(i))){type='native_parameter';i+=sql.slice(i).match(/^\$\d+/)[0].length;}
  else if(/[A-Za-z_]/.test(c)){type='word';while(i<sql.length&&/[A-Za-z0-9_$]/.test(sql[i]))i++;}
  else {i++;if(c==='?')type='parameter';if(c==='`')invalid('SQLite quoted identifiers require a PostgreSQL query variant');}
  result.push({type,text:sql.slice(start,i)});
 }
 return result;
}

function compile(sql){
 const stream=tokens(sql),meaningful=stream.map((token,index)=>({...token,index})).filter(t=>!['space','comment'].includes(t.type));
 if(!meaningful.length)invalid('Empty PostgreSQL service statement');
 const upper=token=>token?.type==='word'?token.text.toUpperCase():'';
 if(upper(meaningful[0])==='PRAGMA')invalid('SQLite PRAGMA is unavailable on PostgreSQL');
 const semicolons=meaningful.filter(t=>t.text===';');if(semicolons.length>1||semicolons.length===1&&semicolons[0].index!==meaningful.at(-1).index)invalid('Service statements must contain exactly one SQL command');
 for(let i=0;i<meaningful.length;i++){
  const t=meaningful[i];
  if(t.type==='word'&&sqliteOnlyFunctions.has(t.text.toLowerCase())&&meaningful[i+1]?.text==='(')invalid(`PostgreSQL query variant required for ${t.text.toLowerCase()}`);
  if(upper(t)==='BLOB')invalid('PostgreSQL query variant required for SQLite BLOB casts');
  if(upper(t)==='INDEXED'){
   const name=meaningful[i+2];if(upper(meaningful[i+1])!=='BY'||name?.type!=='word'||!knownIndexes.has(name.text))invalid('Unreviewed SQLite index hint');
   for(let j=t.index;j<=name.index;j++)stream[j].text='';
  }
 }
 const ignored=upper(meaningful[0])==='INSERT'&&upper(meaningful[1])==='OR'&&upper(meaningful[2])==='IGNORE';
 if(ignored){
  if(upper(meaningful[3])!=='INTO')invalid('Unsupported SQLite insert syntax');stream[meaningful[1].index].text='';stream[meaningful[2].index].text='';
  let depth=0,insertAt=stream.length;
  for(const t of meaningful){if(t.text==='(')depth++;else if(t.text===')')depth--;else if(depth===0&&upper(t)==='CONFLICT')invalid('Insert already declares a conflict policy');else if(depth===0&&(upper(t)==='RETURNING'||t.text===';')){insertAt=t.index;break;}}
  // Trailing line comments must not swallow the added conflict policy.
  if(insertAt===stream.length)insertAt=meaningful.at(-1).index+1;
  stream.splice(insertAt,0,{type:'space',text:' ON CONFLICT DO NOTHING '});
 }
 let count=0;const native=new Set();for(const token of stream){if(token.type==='parameter')token.text=`$${++count}`;else if(token.type==='native_parameter')native.add(Number(token.text.slice(1)));}
 if(count&&native.size)invalid('Mixed SQL parameter conventions are not supported');
 if(native.size){count=Math.max(...native);if(native.has(0)||count!==native.size)invalid('PostgreSQL parameters must be numbered consecutively');}
 return {query:stream.map(t=>t.text).join(''),parameterCount:count,operation:upper(meaningful[0]),ingestion:ignored&&meaningful.some(t=>t.type==='word'&&t.text==='atlas_ingestions')||upper(meaningful[0])==='INSERT'&&meaningful.some(t=>t.type==='word'&&t.text==='atlas_ingestions')};
}

function parameters(values,count){
 if(!Array.isArray(values)||values.length!==count)invalid('SQL binding count does not match the statement');
 return values.map(value=>{if(value===undefined||typeof value==='number'&&!Number.isFinite(value))invalid('Invalid PostgreSQL bound value');return value;});
}
export function translatePostgresSql(sql,values=[]){const compiled=compile(sql);return {query:compiled.query,params:parameters(values,compiled.parameterCount)};}

function safeInteger(value){
 const numeric=typeof value==='bigint'?Number(value):typeof value==='string'&&/^-?\d+(?:\.0+)?$/.test(value)?Number(value):value;
 if(!Number.isSafeInteger(numeric))throw new PostgresAdapterError('PostgreSQL numeric result exceeds the supported integer contract');
 return numeric;
}
function normalized(result,operation){
 if(!result||!Array.isArray(result.rows))throw new PostgresAdapterError('Invalid PostgreSQL result');
 const bigintFields=new Set((result.fields??[]).filter(f=>f.dataTypeID===20).map(f=>f.name));
 const rows=result.rows.map(row=>Object.fromEntries(Object.entries(row).map(([key,value])=>[key,value!=null&&(typeof value==='bigint'||bigintFields.has(key)||numericDateFields.has(key))?safeInteger(value):value])));
 const affected=result.rowCount??result.affectedRows??0,command=String(result.command??operation).toUpperCase();
 if(!Number.isSafeInteger(affected)||affected<0)throw new PostgresAdapterError('Invalid PostgreSQL affected-row count');
 return {success:true,results:rows,meta:{changes:['INSERT','UPDATE','DELETE','MERGE'].includes(command)?affected:0}};
}
function safeError(error,timeout=false){
 if(error instanceof PostgresAdapterError)return error;
 if(timeout||error?.name==='AbortError')return new PostgresAdapterError('PostgreSQL request timed out; an idempotent retry may be required',{code:'ATLAS_DB_TIMEOUT',retryable:true,commitStatus:'unknown'});
 const code=typeof error?.code==='string'&&/^[0-9A-Z]{5}$/.test(error.code)?error.code:null;
 // Never retain cause/detail/query/parameters/server payloads: a driver error
 // can contain a complete connection URL or sensitive claim text.
 return new PostgresAdapterError(code?`PostgreSQL operation rejected (SQLSTATE ${code})`:'PostgreSQL service is temporarily unavailable',{code,retryable:['40001','40P01','57014','53300','57P03'].includes(code)});
}

/** Inject a real Neon HTTP driver or an isolated PostgreSQL test driver. */
export function createPostgresDatabase(driver,{timeoutMs=15000}={}){
 if(!driver||typeof driver.query!=='function'||typeof driver.transaction!=='function')invalid('PostgreSQL driver must support queries and atomic transactions');
 if(!Number.isFinite(timeoutMs)||timeoutMs<=0)invalid('Invalid PostgreSQL timeout');timeoutMs=Math.max(100,Math.min(30000,Math.floor(timeoutMs)));
 const statements=new WeakMap();
 async function execute(run){
  const controller=new AbortController();let timer,timedOut=false;
  const timeout=new Promise((_,reject)=>{timer=setTimeout(()=>{timedOut=true;controller.abort();reject(safeError(null,true));},timeoutMs);});
  try{return await Promise.race([run({fullResults:true,arrayMode:false,fetchOptions:{signal:controller.signal}}),timeout]);}
  catch(error){throw safeError(error,timedOut);}finally{clearTimeout(timer);}
 }
 function statement(compiled,values=[]){
  const get=()=>({query:compiled.query,params:parameters(values,compiled.parameterCount)});
  const object={
   bind(...bound){parameters(bound,compiled.parameterCount);return statement(compiled,[...bound]);},
   async all(){const prepared=get();return normalized(await execute(options=>driver.query(prepared.query,prepared.params,options)),compiled.operation);},
   async first(column){const result=await this.all(),row=result.results[0]??null;if(column==null||row==null)return row;if(!Object.hasOwn(row,column))invalid('Requested result column does not exist');return row[column];},
   async run(){return this.all();},
  };
  statements.set(object,{get,compiled});return object;
 }
 return {
  dialect:'postgres',
  prepare(sql){return statement(compile(sql));},
  async batch(batch){
   if(!Array.isArray(batch)||batch.length>1000)invalid('PostgreSQL batch must contain at most 1000 statements');if(!batch.length)return [];
   const items=batch.map(s=>{const item=statements.get(s);if(!item)invalid('Batch statement belongs to a different database adapter');return item;});
   const locked=items.some(item=>item.compiled.ingestion),prepared=items.map(item=>item.get());
   if(locked)prepared.unshift(ingestionLock);
   const results=await execute(options=>driver.transaction(prepared,{...options,isolationLevel:'Serializable'}));
   if(!Array.isArray(results)||results.length!==prepared.length)throw new PostgresAdapterError('Invalid PostgreSQL transaction result');
   return results.slice(Number(locked)).map((result,i)=>normalized(result,items[i].compiled.operation));
  },
  async databaseBytes(){const result=normalized(await execute(options=>driver.query('SELECT pg_database_size(current_database()) AS bytes',[],options)),'SELECT');const value=result.results[0]?.bytes;if(value==null)throw new PostgresAdapterError('PostgreSQL storage measurement is unavailable');return safeInteger(value);},
 };
}

/** Existing Site handlers keep credentials server-side and the API unchanged. */
export function createNeonDatabase(connectionString,{queryFactory=neon,timeoutMs=15000}={}){
 try{const url=new URL(connectionString);if(!['postgres:','postgresql:'].includes(url.protocol)||!url.hostname||!url.username)invalid('Invalid PostgreSQL connection configuration');}
 catch{invalid('Invalid PostgreSQL connection configuration');}
 let sql;try{sql=queryFactory(connectionString,{fullResults:true,arrayMode:false});}catch(error){throw safeError(error);}
 return createPostgresDatabase({
  query:(query,params,options)=>sql.query(query,params,options),
  transaction:(batch,options)=>sql.transaction(tx=>batch.map(item=>tx.query(item.query,item.params)),options),
 },{timeoutMs});
}
