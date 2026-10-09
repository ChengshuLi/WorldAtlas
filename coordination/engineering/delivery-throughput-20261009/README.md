# Delivery throughput coordination change

Refs #1636. This implements the human-requested removal of unnecessary bookkeeping
and repeated proof work; it does not claim that the global gap campaign is complete.

- PR count is a planning estimate. Actual scope, ownership, dependencies, source
  authority and acceptance still bound work. Old v1 issues/claims remain compatible.
- The complete Git diff and exact-head review bind implementation changes. New
  manifests need not copy that diff into change_receipts or hash code/docs as outputs.
  Scientific inputs/results, source preservation, metrics and record checks remain.
- Passed-control JSON files and blanket two-run generator proofs are no longer
  mandatory. Declared controls still validate. Actual checks cover changed behavior;
  applicable retained results/tests can be reused without pretending they ran again.
- Campaign workers finish supported batches through integration, keep unresolved cases
  independent, and correct approaches that keep expanding support without delivery.
  Audit follow-ups are urgent only for demonstrated impact, not automatically.

The focused tests in tests.txt exercise continuation, ownership/dependency rejection,
legacy and minimal manifests, wrong result/record/source rejection, stale or incomplete
review, partial API reads, current contract binding and trusted transport. They use
fixtures, not production or new geographic approvals. Initial local testing lacked
one sparse input (data/research-geography-gate.json); restoring that tracked input
resolved the environment failure. The retained final run passes without skips.

This PR itself retains the old complete output/change receipts because trusted main
still requires them until this change merges. That is rollout compatibility, not the
new recommendation. No new schema, ledger, schedule or helper framework is introduced.
Actual batch throughput and adoption must be observed in ENG gap closer's subsequent
handoff; passing these tests alone does not establish repair delivery.
