# Kazakhstan–Russia 19-family source fitness assessment

Issue: [#1322](https://github.com/ChengshuLi/WorldAtlas/issues/1322)

Parent work: [#1202](https://github.com/ChengshuLi/WorldAtlas/issues/1202)

Author branch: `geography/kazakhstan-russia-source-fitness-1322-20261007`

## Scope and limits

This packet assesses the source fitness and mapped physical evidence for the complete assigned cohort: 19 gap families, 52 components, and 41 current Atlas contacts. The routing report contains no numeric-first families. It classifies 28 components as compatible-original coverage candidates and 24 as partial or unbound original-source cases. These are source-relative processing observations. They do not establish dry land, ownership, current physical truth, legal boundary authority, or permission to repair.

This work does not authorize geometry repair, boundary certification, whole-region approval, history import, or completion of parent issue #1202. See [`source-assessment.md`](source-assessment.md) for the source, physical-evidence, and authority assessment; see the generated files in [`executions/run-1/`](executions/run-1/) for the candidate table, family closure, contact lineage, and source metadata.

## Execution custody

- Current issue claim receipt: [`claim-receipt.json`](claim-receipt.json).
- Fresh managed author workspace was allocated from `cbae22cc877f6f8a70650069d91d2b34240582f7`.
- Immutable assigned routing report SHA-256: `2bf401f76aabc30cb9f0120aba958545146ebf37e304d8817d15eed800fa5265`.
- Immutable routing input configuration SHA-256: `7623fa8a61b72c33a1560f0ab612e70c463e8c25beef930043c985fd6657f173`.
- Preparation handoff SHA-256: `2c6cae9dbf4ac28bfe623624a5eab92dcc70ca71d6decc36f6ec8ca204d4d550`; the full handoff is retained as preparation evidence and does not replace committed source-body custody.
- Source IDs in the pinned full and simplified geoBoundaries products were compared by [`compare_source_ids.py`](compare_source_ids.py); see [`source-id-comparison.json`](executions/source-id-comparison.json) and its [execution receipt](executions/source-id-comparison-receipt.json). This is an identity-set comparison, not a geometry-equivalence test.

## Deterministic execution

[`build_assessment.py`](build_assessment.py) validates the frozen input inventory and ordered routing bodies, binds every candidate to the original source-fitness classification, verifies component/contact/family closure, restores and checks the complete physical comparison records against the retained packed and full runs, and emits the candidate, family, contact, and source-product records.

The two full producer runs are retained in [`run-1-receipt.json`](executions/run-1-receipt.json) and [`run-2-receipt.json`](executions/run-2-receipt.json). Their four output files are byte-identical; [`output-comparison.json`](executions/output-comparison.json) records the comparison. The earlier failed/interrupted attempts remain individually marked in `executions/` as superseded attempts and are not treated as successful producer runs.

[`assessment_controls.py`](assessment_controls.py) records successful positive closure and four deliberate negative controls for omitted, duplicated, foreign/rebound component identities, and source-ID drift. Its artifacts and the two-run receipt are under `executions/`. These controls validate the retained result roster and file identity, not the legal or physical truth of any boundary.

## Reproduction and input inventory

[`source-freeze.json`](source-freeze.json) pins the producer, Python runtime, input-manifest digest, source head, and freeze revision. [`input-manifest.json`](input-manifest.json) records each ordinary packet input by path, byte count, and SHA-256. The 120,489,189-byte unsimplified Russian source product exceeds the packet's per-file size limit; it is held in the local preservation cache only, with its release URL, resolved URL, digest, and byte count recorded in [`unsimplified-source-retrieval.json`](inputs/metadata/unsimplified-source-retrieval.json). Its source IDs were checked against the committed simplified Russian product, and the committed result records the external full-source digest. Restore that file from the exact pinned release URL before repeating the full-vs-simplified ID comparison.

## Attribution

The geoBoundaries release files are pinned to commit `9469f09592ced973a3448cf66b6100b741b64c0d`; each country’s metadata and citation/use text are retained under `inputs/metadata/`. The metadata identifies OpenStreetMap and Wambacher as the underlying sources, records ODbL 1.0 for those underlying data, and records a 2017 represented year. geoBoundaries describes gbOpen as CC-BY 4.0-compliant subject to attribution. Cite geoBoundaries and the underlying source attribution when reusing these data. The receipt and metadata are evidence of the source’s own recorded terms, not an independent legal opinion.
