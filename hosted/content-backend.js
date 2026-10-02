import {createNeonDatabase} from './postgres-adapter.js';

const cached=new WeakMap();
const unavailable=()=>{throw Object.assign(new Error('Historical database configuration is unavailable'),{status:503});};

/** Explicit cutover only. Selecting PostgreSQL never falls back to stale D1. */
export function contentDatabase(env,{createPostgres=createNeonDatabase}={}){
 const backend=env.ATLAS_CONTENT_BACKEND??'d1';
 if(backend==='d1'){if(!env.DB)unavailable();return env.DB;}
 if(backend!=='postgres'||typeof env.DATABASE_URL!=='string'||!env.DATABASE_URL.trim())unavailable();
 const previous=cached.get(env);
 if(previous?.url===env.DATABASE_URL&&previous.factory===createPostgres)return previous.db;
 let db;try{db=createPostgres(env.DATABASE_URL);}catch{unavailable();}
 cached.set(env,{url:env.DATABASE_URL,factory:createPostgres,db});return db;
}

export function storageReadOnly(env){return env.ATLAS_READ_ONLY==='1';}
