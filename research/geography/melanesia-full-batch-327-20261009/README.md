# Melanesia full-batch source and physical handoff — #1646

This packet covers the exact `gap-operational-batch:f94321eb696d00702d30402d`: 327 components in 38 fine families across Fiji, Indonesia, Papua New Guinea, Solomon Islands and Vanuatu. It preserves the global count of 594 operational batches. The 327 IDs and original family locators are copied from the supplied work index and checked against the retained actionability and physical records.

## Results

The `outcomes-327.jsonl.gz` ledger is a disjoint classification of every component:

| Outcome | Count | Treatment |
| --- | ---: | --- |
| Prior Makira source-fitness finding inherited from #1457 | 15 | Retained unresolved/unapproved; no repeat source search |
| Priority source-fitness cases without the inherited assessment | 25 | Prior admin geometry comparison is bundled; source fitness remains unresolved |
| Retained comparison: unique compatible subject covers component | 20 | Original comparison and source feature retained |
| Retained comparison: positive coverage, mixed/partial/unresolved | 171 | Original per-feature intersections and full component-minus-source-union remainder retained |
| Retained comparison: no intersection in literal source domain | 18 | Original comparison retained; not interpreted as absence of other sources |
| Retained prerequisite: engineering numeric closure first | 18 | Exact existing route retained |
| Retained prerequisite: land without admin comparison/source or processing custody | 24 | Exact existing route retained |
| Retained prerequisite: mixed support and whole-source-fitness review | 9 | Exact existing route retained |
| Retained prerequisite: outside source domain, unclassified | 27 | Exact existing route retained |

Four of the 15 inherited Makira IDs are also among the 29 priority IDs; the other 11 are inherited but outside that priority set. The other 25 priority IDs have one compatible recorded administrative subject covering the component in the retained source comparison. That polygon relation does not establish physical/source fitness, boundary authority or cause.

All 327 exact candidate Features are bundled in `candidate-current-target-features.geojson.gz`. Their complete feature and geometry hashes match the actionability ledger and retained source-comparison records; the retained relation identifies each as the complete current target pointset for this work item. Full, deduplicated GeoJSON Features for the 60 referenced administrative source subjects are split by the five original products in `source-features-*.geojson.gz`; `source-feature-index.json` maps each whole feature and geometry hash to its source product. The 249 existing comparison rows retain their literal per-feature intersections, union intersection, component-minus-source-union remainder, source IDs and original joins. The 78 components without an admin-binding row remain assigned their recorded actionability prerequisite; missing comparison rows are not labeled a source mismatch.

`physical-records-327.jsonl.gz`, `actionability-records-327.jsonl.gz`, `admin-binding-records-249.jsonl.gz`, `fine-family-records-38.jsonl.gz` and `operational-batch-record.jsonl.gz` preserve the matching whole existing records. `component-subject-files.json` and the evidence manifest bind every subject to its original whole candidate FeatureCollection custody file. Eleven referenced payloads carry a custody commit that is not an ancestor of the PR base; the assembler verifies those original bytes against byte-identical aliases in the PR base, pins the base aliases for review, and records original commit/blob/hash alongside each alias in `component-custody-origin.json`. The consumed physical `input-config.json` and imported `scripts/evidence/immutable.py` helper are also pinned. The assembly receipt records exact whole-file, feature and row-hash joins.

## Reused evidence and method

The exact 15-row Makira assessment and source-register entries are inherited from #1457 in `inherited-makira-findings-15.jsonl.gz`; the source register and assessment remain pinned in the evidence manifest. Four of those 15 IDs are among this batch’s priority 29. #1424’s retained two-batch, 28-family, 45-component Solomon source/physical context is referenced in `context-reuse.json`; its 45 subjects are disjoint from this batch and are not inserted into the 327 outcomes.

`prior-work-reuse.json` records the exact roster audit: all 363 subjects in #1626/#1639 and all 25 in #1643/#1644 are disjoint from this 327-ID batch, so none are copied into these outcomes. It also records that #1604 remains the separate open checksum-algorithm provenance erratum for the Makira work; it is left untouched. These checks prevent duplicated work while retaining the prior packets as immutable context. The actionability report independently records 594 whole operational batches, and the handoff preserves that count without changing any grouping.

This is extraction and identity reconciliation over already retained products. The source product payloads are the exact original simplified GeoBoundaries files preserved by the source-corpus packet. Existing source-comparison outputs provide intersections and remainders; existing physical outputs provide source-relative support and GSHHG query records. The assembler authenticates original encoded/decoded bytes and whole-row joins, extracts only the requested exact Features, and does not call geometry operators. No browser/provider request, imagery access, native evaluation, source/GIS replay, production write, live geography change or whole-world pipeline replay was performed.

## Limits and next work

The administrative source payloads and physical comparisons are unapproved as authority. Physical observations use the retained GSHHG 2.3.7/2017 source context with heterogeneous observation dates; narrow shoreline/channel truth remains unresolved. The 25 priority rows still need independent source-fitness evidence. The 15 inherited Makira findings remain as #1457 recorded them: no qualifying physical/imagery source was established, and its screening candidates did not provide exact asset bytes, coverage, lineage, rights or component-level fitness. Processing cause, historic water/ice interpretation, territorial/boundary authority and present-day physical truth remain unresolved. These outputs are not native qualification, a proposed repair or a production target.

Rebuild into a new, uniquely named directory under the owned packet path with:

```text
python3 research/geography/melanesia-full-batch-327-20261009/assemble.py --work-index /path/to/geo4-next-full-batch-327.json --out research/geography/melanesia-full-batch-327-20261009/reproductions/run-unique-name
```

Omitting `--out` selects a fresh random run directory. The assembler refuses existing directories, symlink paths and output paths outside the owned packet prefix; it creates each result file exclusively and writes the evidence-quality receipt last.

The evidence manifest pins the baseline input commits and each output byte sequence. The accepted scope is tracked by GitHub issue [#1646](https://github.com/ChengshuLi/WorldAtlas/issues/1646).

## #1647 literal rule fit for the same exact 327 — follow-up

`rule-fit-exceptions-327.jsonl.gz` adds one source-only record per original component. `rule-fit-summary-327.json` gives totals and product splits; `derive-1647-rule-fit.py` deterministically reclassifies only the retained #1650 ledgers and the byte-preserved engineering join files. The generator does no spatial operation or new source/native query. The input engineering join JSON is pinned at SHA-256 `cdf0152a9eaf8ae31e86ec3127c2d2d8f043aad3af7914c44c240c152617631b`; its 607,780-byte original Python full-feature preimages are retained at `engineering-current-target-preimages.json` (SHA-256 `6e4d944707919bdc3ec2d00e904847bd3d3006a49c9b669185a7cec3e497da01`). The join records 43/43 selected owner/parent/year/current-full-feature matches across the 229 source-supported observations; it reports zero operator executions and three JavaScript/Python preimage serialization mismatches. The saved Python preimages are necessary for those three targets.

| Original class | Count | Exact #1647 source-only fit | Handling |
| --- | ---: | ---: | --- |
| Full source cover | 52 | 29 | 23 fail at least one retained physical predicate |
| Single-subject partial | 177 | 64 | 113 fail at least one retained physical predicate; all 177 keep their exact nonempty remainders |
| Multi-subject | 2 | 0 | Retained as exceptions |
| No source intersection in retained literal domain | 18 | 0 | Retained as exceptions |
| No administrative comparison row | 78 | 0 | Retained as exceptions |
| **Total** | **327** | **93** | **98 original exceptions unchanged** |

The literal fit requires one compatible recorded source subject, the whole mapped-land pointset predicate, empty retained mapped-water/outside-L1/contradictory/missing/extra and hierarchy residuals, a checked retained level-1 source-cover query with no chain issues, and exact residual custody. For a full row, the source-union remainder is the retained valid empty Polygon with zero area and length. For a partial row, the retained valid Polygon/MultiPolygon remainder is nonempty with positive area and length and has its original hash. A partial fit remains a partial match; it never means the source covers the entire component.

The 93 fitted rows distribute as follows: SLB 19 full + 49 partial; IDN 5 + 7; PNG 4 + 6; FJI 1 + 1; VUT 0 + 1. The retained source corpus records editions and license claims as SLB 2021/Public Domain, IDN 2020/CC BY 3.0 IGO, PNG 2019/CC BY 3.0 IGO, FJI 2020/CC BY 4.0, and VUT 2017/ODbL 1.0. These are catalogue metadata claims for the consumed simplified products, not verified effective intervals, territorial authority, or fitness findings. The five editions already occur in the existing 363-input roster; this packet does not request a new source edition.

This supports a bounded reusable **source-only prequalification rule** for rows that satisfy those literal predicates, with full-cover and partial outcomes kept separate. It does not certify source fitness, source-product authority, legal status, present-day boundaries, historic water/ice, processing cause, or native eligibility. Engineering still owns the batch registration/native qualification, its downstream owner/parent/year/full-feature joins, and the three Python-vs-JavaScript canonical-preimage cases. Whole-world replay remains outside scope.
