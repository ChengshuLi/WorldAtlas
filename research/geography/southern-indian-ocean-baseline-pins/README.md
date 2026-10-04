# Southern Indian Ocean baseline reproduction correction

Issue: [#654](https://github.com/ChengshuLi/WorldAtlas/issues/654). This packet repairs how the four subjects from [issue #439](https://github.com/ChengshuLi/WorldAtlas/issues/439) are reproduced. It does not repeat the island research, recalculate geometry or canonical-grid counts, change the inherited assessment, approve a region, or enable imports.

## Immutable sources and scope

The assigned IDs are `atlas:coverage:ATF-5916`, `atlas:coverage:ATF-5917`, `atlas:coverage:ATF-5918` and `atlas:coverage:HMD+00?`. The exact issue scope, pin values, acceptance text and body digest are recorded in `scope.json`.

The old review was evaluated against baseline commit [`ff171e1dd1998684d9b3549943d5725817a7aef4`](https://github.com/ChengshuLi/WorldAtlas/commit/ff171e1dd1998684d9b3549943d5725817a7aef4). Its original source/review packet remains at merge commit [`4909f04e6e035ffc003d237db68323d005ccdb89`](https://github.com/ChengshuLi/WorldAtlas/commit/4909f04e6e035ffc003d237db68323d005ccdb89), under `data/regional-review/regional-review-2fe7597eb9014901/`. The new packet verifies all 16 ordinary files at that exact source commit against current main and records their byte counts, SHA-256 hashes and Git blob IDs. It verifies the original packet's baseline manifest, all 15 generated output descriptors and source records before constructing any new output.

The original packet preserves 65 baseline file descriptors, including canonical-grid inputs. This reproduction pins 44 ordinary files from the exact baseline: the 8 non-grid whole-file inputs needed from the original evidence manifest, every part named by the frozen world index, and the region's frozen v5 envelope (deduplicated). The original canonical-grid descriptors and extracts remain untouched in the archived source packet; this correction does not reopen those large files because no grid counts are recomputed. It reads those bytes with the shared [`worldatlas-evidence-preparation-v1`](https://github.com/ChengshuLi/WorldAtlas/blob/2663a852ca911d059f4a764a7b84b70f94635d81/scripts/evidence/immutable.py) helper, never from the mutable working tree. It verifies the four IDs occur once at the actual containing-file paths from the old manifest; rechecks full parent chains, province/area/region membership, projection rows, the hierarchy and macro-certificate hashes, and the frozen region-envelope geometry/member hashes; then compares those results to the preserved extract. Any changed commit, byte pin or source snapshot fails before output creation.

## Original sources and reuse limits

The original packet records source URLs, dates, licenses, lawful retention status, hashes and restoration instructions. This correction embeds those source records unchanged in `vintages/20261004-pinned-geography-inputs/source-snapshot-manifest.json`; it performs no new external retrieval and adds no raw geographic source bytes.

| Source | Recorded vintage/access | Recorded reuse and limit |
| --- | --- | --- |
| [Natural Earth 10m Admin-1](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/) | v5.1.1 source commit `ca96624a56bd078437bca8184e78163e5039ad19` (2022-06-02); retrieved 2026-10-03 | Recorded public domain; original packet keeps hashes and restoration instructions, not the full source files. Admin-1 classification does not establish atlas tier. |
| [GSHHG](https://www.soest.hawaii.edu/pwessel/gshhg/) | 2.3.7 high-resolution GSHHS_f_L1; retrieved 2026-10-03 | Original release states LGPL 3.0; archive bytes are not retained. Mixed lineage and scale make it a diagnostic screen, not administrative authority. |
| [TAAF Austral Islands](https://taaf.fr/collectivites/presentation-des-territoires/les-iles-australes/) | Page modified 2025-02-19; captured 2026-10-03 | Page reuse license unknown; original response bytes were not retained. Narrative inventory and approximate areas do not resolve every small-island crosswalk. |
| [UNESCO French Austral Lands and Seas](https://whc.unesco.org/en/list/1603/) and [Heard and McDonald Islands](https://whc.unesco.org/en/list/577/) | Sites inscribed in 2019 and 1997; pages retrieved 2026-10-03 | Original packet records CC BY-SA IGO 3.0 for cited text; page bytes were not retained. Conservation descriptions are not political boundaries or exact per-island geometry. |
| [Australian Antarctic Program: territory](https://www.antarctica.gov.au/about-antarctica/australia-in-antarctica/the-territory-of-heard-island-and-mcdonald-islands/), [Heard operations](https://www.antarctica.gov.au/antarctic-operations/stations-and-field-locations/heard-island/) and [regional locator map](https://www.antarctica.gov.au/site/assets/files/116632/heard_and_mcdonald_islands_region_a4_16159.pdf) | Web pages and PDF retrieved 2026-10-03; metadata dates remain as in the original receipt | Reuse terms for the pages/map are unknown and bytes were not retained. Territorial title is political context; station and map evidence does not define settlement or exact boundaries. |

These statements are inherited citations, not fresh source verification. The correction leaves the original source receipt, source-role assessments, settlement caveats, limits and unresolved findings unchanged. Island-source restoration remains with #635; inter-region routing remains with #636.

## Reproduction

From the repository root:

```sh
python3 research/geography/southern-indian-ocean-baseline-pins/build_packet.py --check
python3 research/geography/southern-indian-ocean-baseline-pins/build_packet.py --check --vintage 20261004-pinned-geography-inputs
python3 research/geography/southern-indian-ocean-baseline-pins/verify_packet.py
python3 research/geography/southern-indian-ocean-baseline-pins/test_negative_cases.py
node scripts/evidence-quality.mjs research/geography/southern-indian-ocean-baseline-pins/evidence-quality.json
```

The default is read-only. The check independently builds the full receipt twice and compares canonical output bytes. A new output set requires an explicit unused vintage, for example:

```sh
python3 research/geography/southern-indian-ocean-baseline-pins/build_packet.py --create --vintage 20261004-pinned-geography-inputs
```

Creation uses the shared exclusive-write helper and refuses any existing target. Re-running `--check --vintage` verifies the saved files without overwriting them. The actual generated summaries and positive, negative and reproducibility controls are retained under `vintages/20261004-pinned-geography-inputs/`.

## Interpretation

The output verifies that the original four-subject summary can be recreated from its declared historical commit and matches its preserved location summaries, complete parent chains, membership rows, projection rows, actual containing files and frozen region context. The old screen results remain baseline evidence; the script does not call them current or independently establish their geographic truth. No shared hierarchy, boundary, grid, certificate, application or live data changes are proposed.
