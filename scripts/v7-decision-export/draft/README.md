# Neon draft evidence exporter

This is a read-only research transport, not a build authority. It exports one existing **draft** decision revision together with its matching **draft** entity revision, features, basin participants, routes, ocean seeds and policies, affiliations, category bindings, and the referenced source records and their transitive dependencies. It deliberately emits `worldatlas-geography-decision-draft-evidence-v1`, which is distinct from the accepted-build export schema, and retains the database's draft status. It cannot prove review, source authenticity, source byte integrity, selected source completeness, geographic correctness, or production readiness. The digest detects later local changes; it does not authenticate who made the decisions.

## Use

Install psycopg 3 in the execution environment. Set standard libpq connection variables securely for a trusted Neon endpoint and SELECT-only role. The client requires TLS `verify-full`; credentials must not be supplied on the command line. Run:

`python3 export_draft.py --revision REVISION --out NEW_FILE.json`

The output file is created exclusively; an existing file is not overwritten. One explicit repeatable-read, read-only transaction runs a single statement and rolls back. The SQL is designed and tested against the existing review-branch schema, not every possible migration history. It does not create a source build, select new inputs, accept a revision, or write to the database. The CLI has not been tested with a real SELECT-only database connection; the same query was executed through the Neon connector against the live review branch. Review server privileges and independently verify every source object and its metadata before use.

The direct pipeline must derive its physical grid from selected, hash-verified raw inputs, then record the output hashes, code and software versions, exact source manifest, and this snapshot's digest in a separate candidate build manifest. This export requires no historical V2 physical-grid hash; V2 may serve as optional validation only. The separate existing accepted-build exporter remains required for any accepted release process. No build is authorized by this file alone.

Features reference `source_id` and `source_version`; `sources` has exact referenced asset hash, byte count and R2 location, while `source_lineage_assets` and `source_lineage_dependencies` carry metadata and ancestral relationships. A draft can be incomplete even if references are structurally consistent. There are no `source_inputs`, build pins or assertions of complete selection here. The underlying source identities and R2 locations must be separately validated. Consumers may opt into draft testing only with a visibly explicit unverified flag and must not relabel status as accepted.

Run synthetic tests: `python3 -m unittest -v test_export_draft.py`. They check transaction handling, draft-only gate, schema separation, representative orphan and lineage failures, and deterministic ordering. They are not an independent security audit.

## Live capture, 2026-11-03

A draft snapshot was captured from `v7-geography-research-draft-1` by running the same query through the Neon connector. At capture it contained 92 draft features and basins, nine routes, four ocean seeds, one ocean-fill policy, one registered source, and no land affiliations. Its SHA-256 is `4c046d2ca7a405a2cf576184fcbbc1fa1860ca355d981644a6b6a420db2ff7fb`. It is a snapshot in time, not a live view. The registered source is the SeaVoX archive; its registration records a prior R2 readback, but this capture did not verify the object bytes. Current land source geometry, complete affiliations, and source-backed partition decisions are not present. Existing ocean route/seed and basin tie records are also draft and need geographic review. There is no accepted revision or locked build in this branch.
