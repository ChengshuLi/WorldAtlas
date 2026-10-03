// Keep the existing location resolver's precedence in one shared function.
// Source validation and supported dates are the caller's responsibility.
export const evidencePriority = record => record.is_example
  ? 40 + (record.evidence_priority || 0)
  : record.method === 'direct' ? (record.evidence_priority || 0)
    : record.method === 'majority-area' || record.method === 'derived' ? 10
      : record.method === 'reference' ? 20 : 30;
