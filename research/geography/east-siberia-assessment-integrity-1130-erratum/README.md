# East Siberia assessment integrity erratum

**Issue:** #1356 — preserve and authenticate PR #1130's East Siberia inputs and provenance claims.
**Scope:** the exact 207 issue subjects plus the six pre-existing province-parent records.
**Evidence baseline:** PR #1130 merge `90d5309c6497073a039099241360ba807d0c3722`; final evaluation checkout `fb61cf6cfd40523d7e4448d677db047d80d49f16`.
**Owned packet:** `research/geography/east-siberia-assessment-integrity-1130-erratum/`.

## Result

The pinned feature records have an `administrative_level` metadata claim, while the old analyzer requested `source_level`. As a result, the old assessment and table omitted that field for all 207 subjects. The guarded reproduction reads the actual pinned field and checks every value against the corresponding unique feature. It records 185 `ADM2` claims and 22 `Named physical region portion` claims. These are source metadata claims, not approved legal or geographic classifications.

The guarded entry point authenticates all 61 issue-declared whole-file pins at the immutable PR #1130 merge. It scans all 36 files in that baseline's world index, joins all 207 subjects exactly once, and checks the inventory's 15 current/source fields against the matching feature and parent records. The two current subject-bearing files, `data/geography/part-20.json` and `part-21.json`, still match their exact issue pins. Two other parts changed on later main; scope-wide uniqueness is therefore established from the immutable baseline Git objects rather than silently reading those newer files.

Two actual runs of the pinned analyzer and renderer, with the source-level field corrected and both outputs redirected to new, exclusive packet paths, are byte-identical. All assessment fields other than the 207 missing provenance values, every numeric measurement, all 185 `insufficient-evidence` and 22 `correction-needed` dispositions, and all six province records match the retained outputs. The old assessment and table remain at their original hashes. The current v7 pair was regenerated after rebasing this PR onto `e6a81f6ab6da318e015cd697f3b19956e8bb8cc7`; its outputs match the prior v6 bytes exactly. The v6 receipt remains preserved.

The control suite also reproduces the old false-positive name binding: the unguarded pinned analyzer accepts a complete inventory with one fabricated current name, emits that name, and reports that the actual feature name matches its source. It separately confirms that both original writers replace private sentinel files. The new entry point rejects altered inventory, code, or source bytes before admitting outputs and uses exclusive file creation inside an exclusively admitted fresh run directory.

## Reproduction

Use Python 3.12 with Shapely 2.1.2, GEOS 3.13.1, pyproj 3.7.2 / PROJ 9.5.1, and Node 24.19.0. From the repository root:

```sh
python3.12 research/geography/east-siberia-assessment-integrity-1130-erratum/reproduction/reproduce_guarded.py --vintage 2026-10-08-integrity-v7
python3.12 research/geography/east-siberia-assessment-integrity-1130-erratum/reproduction/test_integrity.py
node scripts/evidence-quality.mjs research/geography/east-siberia-assessment-integrity-1130-erratum/evidence-quality.json
```

Each vintage is a one-use name. The runner authenticates the captured GitHub issue contract, all 61 baseline files, the actual issue roster, unique feature identities, source-member joins, current part files, and exact producer-code pins before output admission. It then admits both fresh run directories before either producer writes. It runs the original producer code from its pinned checkout bytes with only exact, asserted substitutions for the missing metadata key and output paths; each output uses exclusive creation. The failing v1 orchestration attempt and completed v2/v3/v4/v5/v6 reproducibility receipts are retained as history; their byte-identical raw v6 outputs were pruned only after two fresh v7 runs matched all four output files exactly.

The test suite exercises the actual guarded CLI against name, identity, roster, parent, source-member, code, source, existing-output, broken-symlink, partial-output and path-escape controls. It also retains the result of running the pinned original producers against private sentinels to demonstrate their unsafe existing writers, without opening historical output paths. The adapters use repository-relative destinations and are reproducible from isolated checkouts; a path-portability assertion protects against checkout-specific paths returning. All fixtures and outputs remain inside this issue-owned packet.

## Research limits and handoffs

The original #393 packet remains the geographic source record. Its 2017 geoBoundaries Russia ADM2 vintage (ODbL 1.0), RESOLVE ecoregion lineage (CC BY 4.0), Natural Earth lake source (public domain), retrieval dates, hashes, original feature extracts and restoration notes remain pinned at the immutable baseline; this erratum does not duplicate or alter them. The full 120,489,189-byte raw Russia source remains restoration-only. Constitution Article 65 source bytes and the Rosstat primary classifier contents remain unverified. The 2,327-feature versus 2,328-metadata discrepancy remains assigned to #1133.

The per-subject #393 findings remain bounded: 185 2017 ADM2 source-ID matches have unresolved legal/current status and country completeness; 21 ecoregion fragments and one Lake Baikal fragment remain correction-needed source/parent semantics; six province-parent records retain unresolved frozen-boundary and membership evidence. Neighboring tier/parent, administrative suitability, overlay semantics and source-count questions remain with #392, #1125, #1126 and #1133. No boundary, parent, legal, license, completeness or publication conclusion is added here.

This packet changes no canonical geography or historical evidence. It does not authorize import, regional publication, deployment, boundary approval or legal determination. The original producer files are outside #1356's owned path and remain preserved; this packet supplies a guarded, immutable-input, fresh-output execution path. Any future change to the legacy producer defaults requires separate engineering ownership and review.
