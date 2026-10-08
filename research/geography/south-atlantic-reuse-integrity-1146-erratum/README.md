# South Atlantic #1146 source-integrity erratum

Research date: 2026-10-07 (America/Los_Angeles). Work item: [#1369](https://github.com/ChengshuLi/WorldAtlas/issues/1369). Affected producer merge: `1f971fef3ed24f4ddc3e3c41caac00db567caea5`; geographic/source baseline: `dab6ef29468eb97226f642783127720444f299c9`. The accepted serialized reservation and exact owned path are recorded in `reservation.json`.

This packet adds an integrity and safe-reproduction handoff for the exact 268 existing South Atlantic county subjects. It does not amend the original #1143/#1146 packet or its historical results. The new verifier reads that material as immutable input. No geometry, hierarchy, source catalog, legal determination, production data, regional approval or neighboring cohort is changed.

## Finding and bounded result

The original producer checks the 12 historical baseline issue pins, but consumes `cb_2018_us_county_500k.zip` before checking its full-file hash. It computes that hash only in the output summary after joining. In an isolated replay of the exact merged code, swapping `COUNTYFP` and `GEOID` for Lancaster and Beaufort, South Carolina, leaves names and state unchanged and retains valid `GEOID = STATEFP + COUNTYFP` values. The original producer accepts the mutated archive and emits Lancaster (Atlas ID `gb:USA:ADM2:52423323B10055621117527`) with GEOID `45013` instead of `45057`; both original controls still pass. A ZIP-comment-only change also passes and is recorded after use.

The original producer replaces five existing evidence files in place. Its optional receipt destination check occurs after those writes; the isolated invalid `.txt` receipt case raises after replacing all five sentinel predecessors. The exact old program, fixtures and generated files existed only in disposable temporary packet trees linked to the repository object store. No old evidence file in the worktree was written.

`reproduce_integrity.py` binds all 36 issue-declared whole-file pins (13 baseline and 23 original-merge inputs), including the actual complete Census archive (11,530,479 bytes, SHA-256 `aaa866af327754e1b80aa87bfb97b04a7209f4f871075aef84affb8f0b3afe67`) and original producer code. It checks each immutable Git blob's commit, path, length and SHA-256 before opening the Census DBF or creating an owned output. It enforces 32 MiB per input/member and 256 MiB aggregate pinned/expanded/output bounds, rejects duplicate, encrypted and excessively expansive ZIP members, and requires the expected 2018 DBF/CPG inventory. It recomputes the original 268-row crosswalk through the exact pinned producer validation functions and compares every output byte with the retained crosswalk. Every run is a new direct child of `runs/`; existing paths, unsafe output names and invalid receipt destinations are rejected before a write. Files use exclusive creation.

Two independent fresh output vintages, `runs/run-eleven/` and `runs/run-twelve/`, were produced with bundled Python 3.12.14. Each contains the full pin ledger, independently recomputed crosswalk, run summary, controls and receipt. Both crosswalks byte-match the retained #1146 crosswalk at SHA-256 `e69458d74688645a3fdde4a7dfba15cf2b13310bb2cb15df13860d566ebb15f3`. The final controls exercise duplicate, missing and ambiguous joins, changed source bytes, invalid/existing output destinations, and actual old-main mutation/overwrite behavior. The complete wrong-output crosswalk and full invalid-receipt error are retained in `legacy-controls.json` for each vintage. The exact 36-pin inventory is authenticated by SHA-256 `a6b40dd3f1161d32dea5d0559f517158b4a58af509a668539f514be007f4d2b2`.

## Reproduction

Use Python 3.12 or later with the standard library from the repository root. Choose a fresh run name each time; the output path must not already exist. The completed runs used the bundled Python 3.12.14 runtime.

```sh
python3 research/geography/south-atlantic-reuse-integrity-1146-erratum/reproduce_integrity.py run-20261007-a
python3 research/geography/south-atlantic-reuse-integrity-1146-erratum/reproduce_integrity.py run-20261007-b
```

A run executes all source-pin, identity and control checks before it creates the output vintage. To verify the saved outputs and manifest without executing packet code:

```sh
node scripts/evidence-quality.mjs research/geography/south-atlantic-reuse-integrity-1146-erratum/evidence-quality.json
```

## Geographic and source limits

The inherited subject assessments identify the 268 records as US county-level ADM2 units with state parents; the exact four parent states in the retained assessment are Florida, North Carolina, South Carolina and West Virginia. The 2018 Census cartographic-boundary archive is a simplified, small-scale thematic product. The complete byte check proves which archive was consumed; the name/state/component join and crosswalk reproduce identity evidence for this roster. They do not compare polygon coordinates, prove legal boundaries, establish current validity, or establish national completeness. County subdivisions are an adjacent lower tier and are outside this 268-subject scope. The 57 coastal boundary candidates remain the separate #975 work.

The pinned provider metadata reports the underlying Census source as Public Domain. The retained geoBoundaries project license separately describes CC BY 4.0 for code and project-generated derivative works; its product citation asks for product attribution and citation of the per-file source. The precise application of derivative terms to this particular 2018 USA ADM2 product remains unresolved in the prior source assessment. This erratum makes no legal conclusion and does not relabel the source. Keep both Census and geoBoundaries attribution, the exact vintage and any Atlas changes in downstream reuse, pending source-owner clarification if a definitive derivative-rights determination is needed.

The issue's source-pin inventory records original commit/path/byte/hash values for every input. Research metadata, source provenance and restoration/retention terms remain in the preserved #1146 packet; this packet adds no duplicated upstream source bytes. The source and output digest manifest links all 268 IDs to the three pinned Atlas geography parts and preserves the prior row-level role/parent assessments. The manifest's research stage does not mean geography has been approved or published.
