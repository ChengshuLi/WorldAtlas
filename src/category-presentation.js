import {displayCategoryKey} from './color-perception.js';

// A display distinction never rewrites the category identity in evidence. Fixed
// environmental classes, hierarchy IDs and numeric scales keep their semantics.
export function categoryPresentationKey(mode, shown, value = shown.value) {
  if (value == null) return mode==='owner'&&shown.category_id!=null?displayCategoryKey(shown.category_id):null;
  const identity = shown.category_id ?? value;
  return ['owner','culture','religion'].includes(mode)
    ? displayCategoryKey(identity, value) : String(identity);
}
