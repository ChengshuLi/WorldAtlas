import { levels } from './model.js';

export function validateHierarchy(units, locations) {
  const byId=new Map(units.map(u=>[u.id,u]));
  if(byId.size!==units.length)throw new Error('Duplicate hierarchy IDs');
  for(const node of [...units,...locations.map(l=>({...l,level:'location'}))]) {
    const expected=levels[levels.indexOf(node.level)+1];
    const parent=byId.get(node.parent_id);
    if(!levels.includes(node.level) || (expected ? !parent || parent.level!==expected : node.parent_id!==null))
      throw new Error(`Incomplete hierarchy for ${node.id}: expected ${expected || 'root'}`);
  }
}

