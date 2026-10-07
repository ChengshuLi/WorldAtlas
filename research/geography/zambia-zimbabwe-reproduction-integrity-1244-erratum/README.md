# Zambia–Zimbabwe reproduction integrity erratum

Issue #1385 is a mechanical correction to the bounded #1244 reproduction and recorder. It is scoped to four existing native ADM2 subjects and ten physical component IDs. This packet does not resolve their territorial meaning, physical land/water status, cause, or administrative assignment. The separate #1234 source and water research remains open and is not a dependency for this erratum.

## Identity and parent checks

The immutable inputs identify three Zambian ADM2 features and one Zimbabwean ADM2 feature:

| Atlas subject | Source product ID | Name | Existing Atlas parent |
| --- | --- | --- | --- |
| `gb:ZMB:ADM2:96606910B35256638811207` | `96606910B35256638811207` | Chirundu | `framework:province:lusaka:0a81a8111ef8` |
| `gb:ZMB:ADM2:96606910B48730551364911` | `96606910B48730551364911` | Luangwa | `framework:province:lusaka:0a81a8111ef8` |
| `gb:ZMB:ADM2:96606910B70191271227661` | `96606910B70191271227661` | Kafue | `framework:province:lusaka:0a81a8111ef8` |
| `gb:ZWE:ADM2:62879985B85730198836463` | `62879985B85730198836463` | Hurungwe | `framework:province:mashonaland-west:8faaeddc2c75` |

The parent links are checked against the pinned Atlas feature and hierarchy records; all four subjects retain `semantic_review.status: open`. They are identity/lineage checks only, not a semantic parent adjudication. The complete issue-owned roster is stored in `source-lock.json`; it preserves exactly ten unique original component IDs and all 17 candidate shards.

## Source vintage, licensing, and limits

The two consumed ADM2 datasets are the complete simplified geoBoundaries products at upstream repository revision `9469f09`, as already retained in the #1244 baseline. Zambia has 116 features (3,574,952 bytes; SHA-256 `58e9df3f95bb4c7539e5fb48839b246b2bfb12694cf5db3ed595240156016c60`); Zimbabwe has 91 features (1,042,500 bytes; SHA-256 `3486ef2803574e63db97e2a35b6688bb327cb8d6ff5e439691c1cc3068ddb424`). Their registry metadata reports a 2020 boundary vintage, build date 2023-12-12 and source update date 2023-01-19. Those dates do not establish a legal effective date, survey registration quality, present boundary interpretation, or feature accuracy. Registry license assertions are CC BY 4.0 for Zambia and CC BY 3.0 IGO for Zimbabwe; this packet preserves the prior metadata claim but does not independently validate rights.

The consumed Natural Earth lakes layer contains 1,355 major lakes and reservoirs. It is a broad reference only: absence of an overlay is not evidence of dry land, and the layer does not inventory rivers, small channels, seasonal water, or time-specific hydrology. Its full source hash and the other 52 issue-declared pins are in `source-lock.json`; all 53 original whole-file pins are preserved and verified against the exact pinned commits. The producer additionally pins its preparation helper `scripts/evidence/immutable.py` at fresh-main commit `d51c43e878c797d215ba5bd8285571fa14add443` (17,414 bytes; SHA-256 `a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46`).

Four original regional citations remain restoration-only and unverified in this work: the 2014 ZamStats environment report, ZimParks Lake Kariba page, the Zambia Parliament 2012 committee report, and the 2014 Zimbabwe Surveyor General / technical committee report hosted by UN-GGIM. Their inherited citation URLs, roles, extracts and limits are documented in the preserved #1244 source provenance. This packet did not fetch or reproduce those documents. They are regional or dated context; they do not provide candidate-scale registered boundary maps, current bilateral interpretation, complete hydrology, legal conclusions, or an assignment for these ten components. The 1963 Order reference in the old report does not close those gaps. Neighboring granularity is limited to the source products' ADM2 feature set and the retained candidate shards; no independent finer-scale or neighboring-country boundary source was added.

## Reproduction and controls

Use repository-root paths and Python 3.12 with `pyproj` and the repository's pinned evidence helper. The package environment used for these runs was the Codex workspace Python bundle; ordinary system Python without `pyproj` is insufficient.

```sh
python3 research/geography/zambia-zimbabwe-reproduction-integrity-1244-erratum/reproduce.py --vintage run-one-main-d51
python3 research/geography/zambia-zimbabwe-reproduction-integrity-1244-erratum/reproduce.py --vintage run-two-main-d51
python3 research/geography/zambia-zimbabwe-reproduction-integrity-1244-erratum/record_controls.py --run-one run-one-main-d51 --run-two run-two-main-d51 --vintage controls-main-d51
```

The run entrypoint independently admits bounded semantic phases: the 53-file raw source/code inventory (67,168,474 bytes), custody (116,710,766 bytes), the complete 17-shard fragment family (157,741,530 bytes), and country-source/geometry comparisons (30,080,420 bytes). The maximum is 256 MiB per phase and 32 MiB per file/decompressed file. The complete candidate family contains 96,963 features; all 11 retained component/contact fragments are checked. The three final compressed phase outputs are byte-identical across both fresh runs. Their SHA-256 values are custody `4d170df9ca6d05b2bdf7b4d90d4c7c381e9e7205bc21b879e73a8a9acbb5e703`, fragments `3bf2de62c1773e6ac03b255d9070ecb9e9e6b01ef70165c3a15d6397e692b1fe`, and source/geometry `b4639e3261db981c494c87b275ba4145eca085c0cb2336f16ec6ebbe34332c99`.

The final actual recorder rejects six complete, internally equal false pairs: missing subject, duplicate component, wrong contact kind/geometry, fabricated source identity, wrong parent, and wrong source vintage. It compares 275 substantive output measurements and control fields with the retained #1244 successful run. The full original contact row is `point-only-ambiguous`; it links an in-scope component to an adjacent component outside this issue's ten-ID roster. The recorder verifies the full row and its geometry rather than incorrectly requiring both endpoints to be in scope. It also tests consumed input/code drift before publication; refusal of an existing file, broken symlink, occupied directory and escaped output; and replacement of the output directory during partial publication. The replacement sentinel remains unchanged and no success receipt is written.

Older iteration vintages are intentionally retained as historical attempts. Only `run-one-main-d51`, `run-two-main-d51`, and `controls-main-d51` are the accepted final evidence for the current locked code. Earlier vintages are superseded; in particular, the first early entrypoint had a post-publication JSON/gzip reporting error, and early control/reproduction iterations exposed defects that were corrected. See `attempt-history.json` for the dated provenance and disposition; do not treat earlier outputs as final verification.

## Findings and engineering handoff

The corrected mechanics establish repeatable bounded comparison and exact identity/contact preservation against the pinned historical inputs. They do not make the source data authoritative for current jurisdiction. `water_status` remains `unverified`, `cause_status` remains `unknown`, and no territorial assignment is asserted. The shared GEOS and WGS84 area helper are not an independent second numerical library. The whole old producer was not run as an unbounded single pass; the new producer's separate bounded phases account for the relevant files and outputs.

No geography correction is proposed by this packet. Any future source or parent correction needs independently sourced neighboring coverage, current/legal meaning, provenance, crosswalks and explicit engineering handoff. Engineering owns changes to shared/core geography and any later migration/publication; this issue authorizes none. Preserve #1244, #1264, #1043 and #1048 unchanged, and keep the broader #1234 source/water research distinct.
