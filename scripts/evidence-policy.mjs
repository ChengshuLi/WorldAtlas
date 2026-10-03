import fs from 'node:fs';
import {safeEvidencePath} from './evidence-quality.mjs';

export function loadEvidencePolicy() {
  return JSON.parse(fs.readFileSync(new URL('../.github/evidence-policy.json', import.meta.url), 'utf8'));
}
export function evidenceRequirement(issue, spec, policy = loadEvidencePolicy(), branch) {
  if (policy.version !== 1 || !['report-only', 'enforce-new'].includes(policy.mode)) throw Error('Unsupported evidence policy');
  const created = Date.parse(issue.created_at), activation = Date.parse(policy.activation_time);
  if (policy.mode === 'enforce-new' && (!Number.isFinite(created) || !Number.isFinite(activation))) throw Error('Missing evidence activation/issue timestamp');
  const legacy = policy.mode === 'enforce-new' && created < activation;
  const required = Boolean(spec.evidence_quality) || (policy.mode === 'enforce-new' && !legacy);
  const quality = spec.evidence_quality;
  if (!quality) {
    if (required) throw Error('New work needs evidence_quality v1 in its authoritative issue contract');
    return {required: false, legacy, decision: legacy ? `Original scope preserved; deficiencies tracked in #${policy.legacy_follow_up}` : 'Reporting rollout: no declared evidence contract'};
  }
  if (quality.version !== 1 || !Array.isArray(quality.subject_ids) || quality.subject_ids.some(id => typeof id !== 'string' || !id) ||
      new Set(quality.subject_ids).size !== quality.subject_ids.length || !quality.pins || Array.isArray(quality.pins) || typeof quality.pins !== 'object' ||
      Object.values(quality.pins).some(pin => !/^[a-f0-9]{64}$/.test(pin)) ||
      !['code', 'source', 'geometry', 'release'].includes(quality.review_kind)) throw Error('Invalid evidence_quality issue contract');
  const manifestPath = safeEvidencePath(quality.manifest_path.replaceAll('{job}', branch?.split('/').slice(1).join('/') ?? '{job}'));
  if (!manifestPath.endsWith('/evidence-quality.json')) throw Error('Manifest must be an owned evidence-quality.json');
  return {required, legacy, quality, manifestPath, decision: 'Versioned evidence and independent exact-head review required'};
}
