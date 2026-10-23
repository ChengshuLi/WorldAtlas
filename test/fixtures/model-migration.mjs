import {openDatabase,importRecords} from '../../database.mjs';

const levels=['continent','subcontinent','region','area','province'];
const units=levels.map((level,index)=>({id:level,name:level,level,parent_id:levels[index-1]??null,metadata:{}}));
export const geometry={type:'Polygon',coordinates:[[[0,51],[.01,51],[.01,51.01],[0,51]]]};
export const location=(id,metadata={})=>({id,name:id,parent_id:'province',geometry,metadata});

export function migrationDatabase(locations,states=[]){
  const db=openDatabase(':memory:');
  importRecords(db,{units,locations,states});
  return db;
}

export function migrationRead(locations,reports={}){
  const files={
    'hierarchy.json':units,
    'world-index.json':{parts:['fixture.json']},
    'fixture.json':{features:locations.map(({geometry,...properties})=>({type:'Feature',id:properties.id,properties,geometry}))},
    ...reports
  };
  return name=>{
    if(!Object.hasOwn(files,name))throw Error(`Unexpected migration input: ${name}`);
    // Production reads fresh JSON; migrateReference sorts its hierarchy input.
    return structuredClone(files[name]);
  };
}
