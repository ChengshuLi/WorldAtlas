// Exact original full-regression producers. Current acceptance is separate.
const complete = v => v?.status === 'completed' && v.conclusion === 'success';
const positive = v => Number.isSafeInteger(v) && v > 0;
export function originalFullRegressionJobs(jobs, {run, attempt, head}) {
  if (!Array.isArray(jobs) || !positive(run) || !positive(attempt) || !/^[a-f0-9]{40}$/.test(head ?? '')) return null;
  const required = new Map([
    ['profile', ['Validate ownership and focused CI applicability']],
    ['package', ['Use full-regression package verification']],
    ...[0, 1, 2].map(shard => [`regression (${shard})`, [
      'Checkout reviewed head', 'Install Node dependencies', 'Install Python dependencies',
      'Install browser dependencies only for tests that use Playwright', 'Complete regression shard',
      ...(shard === 0 ? ['Verify full-regression package controls', 'Build hosted assets',
        'Read back qualified native build outputs when selected', 'Verify full-regression package receipt',
        'Retain full-regression package receipt'] : [])]])
  ]);
  if (jobs.filter(j => /^regression(?: \(\d+\))?$/.test(j.name)).length !== 3) return null;
  const selected = [];
  for (const [name, steps] of required) {
    const matching = jobs.filter(j => j.name === name);
    if (matching.length !== 1) return null;
    const job = matching[0];
    if (!positive(job.id) || !complete(job) || job.run_id !== run || job.run_attempt !== attempt || job.head_sha !== head) return null;
    if (!steps.every(name => {
      const m = job.steps?.filter(s => s.name === name) ?? [];
      // The approved full/evidence checkout branches share this literal label.
      // Exactly one full checkout executes; its evidence counterpart is skipped.
      if (name === 'Checkout reviewed head') return m.length === 2 &&
        m.filter(complete).length === 1 && m.filter(s => s.status === 'completed' && s.conclusion === 'skipped').length === 1;
      return m.length === 1 && complete(m[0]);
    })) return null;
    selected.push({name, job_id: job.id});
  }
  // Original scope/evidence are not current acceptance. No skipped execution
  // or recursively reused producer can satisfy the ordinary required steps.
  return selected;
}

