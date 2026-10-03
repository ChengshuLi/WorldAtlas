import {categoryPalette} from './category-palette.js';
export const levels = ['location', 'province', 'area', 'region', 'subcontinent', 'continent'];
export const attributes = ['owner', 'population', 'culture', 'religion', 'rank', 'topography', 'vegetation', 'climate'];
export const ranks = ['unsettled', 'rural settlement', 'town', 'city', 'metropolis'];
// A literal observed zero is evidence; a rounded or modeled zero is not.
export function explicitPopulationZero(value,evidence={}) {
  const m=evidence.metadata||{},status=evidence.status??'sourced';
  return value===0 && evidence.method==='direct' && status==='sourced' && Boolean(evidence.source||evidence.source_id)
    && !['estimate','example'].includes(evidence.source_status)
    && !m.legacy_snapshot && !m.legacy_attributes
    && !['estimate','estimated','is_estimate','modeled','modelled','rounded'].some(k=>Boolean(m[k]))
    && m.rounding==null && m.model==null && !/(round|model|estimate|approx)/i.test(String(m.precision||''));
}
export function validYear(year) { return Number.isInteger(year) && year !== 0 && year >= -3000 && year <= 2026; }
export function parseYear(input) {
  const match = String(input).trim().match(/^(-?\d+)\s*(BC|BCE|AD|CE)?$/i);
  if (!match) return null;
  let year = Number(match[1]);
  if (match[2] && year < 1) return null;
  if (/^BC/i.test(match[2] || '')) year = -year;
  return validYear(year) ? year : null;
}
export const formatYear = year => `${Math.abs(year).toLocaleString('en-US')} ${year < 0 ? 'BC' : 'AD'}`;
// A continuous slider with no year zero: 1 BC is followed by 1 AD.
export const yearToTick = year => year < 0 ? year + 3000 : year + 2999;
export const tickToYear = tick => tick < 3000 ? tick - 3000 : tick - 2999;
export function categoryColor(value) {
  if (value == null) return '#53615c';
  if (Object.hasOwn(categoryPalette,value)) return categoryPalette[value];
  // New/hosted-only display keys retain deterministic identity colors until the
  // offline pinned adjacency audit is refreshed; no contrast guarantee is implied.
  if (String(value).startsWith('[')) {
    try {const pair=JSON.parse(value);if(Array.isArray(pair)&&pair.length===2&&typeof pair[0]==='string')value=pair[0];} catch {}
  }
  return legacyCategoryColor(value);
}
export function legacyCategoryColor(value) {
  if (value == null) return '#53615c';
  let hash = 2166136261;
  for (const char of String(value)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  const n = hash >>> 0;
  return `hsl(${(n / 4294967296 * 360).toFixed(6)} ${36 + (n >>> 9) % 25}% ${44 + (n >>> 17) % 20}%)`;
}
export function populationColor(value, max) {
  if (value == null) return '#53615c';
  const fraction = max > 0 ? Math.log1p(value) / Math.log1p(max) : 0;
  return `hsl(${155 - fraction * 115} 55% ${78 - fraction * 38}%)`;
}
