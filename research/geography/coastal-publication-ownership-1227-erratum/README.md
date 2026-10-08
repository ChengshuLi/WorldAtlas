# #1381 coastal comparison integrity erratum

This additive packet addresses only publication/failure ownership and actual executed-code provenance for the original eight-county comparison. It does not change the comparison method, geographic facts, source material, identities, parents, or prior packets.

## Reproduce

Use Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2. From the repository root, run the actual entry point with a new, unused vintage name each time:

```sh
python3.12 research/geography/coastal-publication-ownership-1227-erratum/fresh_reproduce.py --run-id erratum-20261008-a
python3.12 research/geography/coastal-publication-ownership-1227-erratum/fresh_reproduce.py --run-id erratum-20261008-b
python3.12 research/geography/coastal-publication-ownership-1227-erratum/fresh_reproduce.py --verify-pair erratum-20261008-a erratum-20261008-b
python3.12 research/geography/coastal-publication-ownership-1227-erratum/fresh_reproduce.py --controls-only
```

Each run verifies the retained 57-input inventory, all eight historical product files, the complete indexed geography parts and the historical reproduction program at immutable Git commit `a37ad37b94168f9b458617489a702bbb72afbd3d`. It authenticates and executes the captured bytes for `coastal-reference-reproduction-980/reproduce.py`, `scripts/evidence/geometry.py`, and `scripts/ellipsoidal_area.py`. It loads the shared immutable reader from its verified Git blob at `de506f51100568e150e51f2926a5259b71e55272` (SHA-256 `a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46`). The current runner hash, code closure, runtime and product hashes are recorded in each execution file.

Output files are written exclusively beneath `vintages/<run-id>/`. The run is complete only after every product is flushed and `publication.json` is installed as the final, fully written receipt. On failure, cleanup unlinks only exact file inodes created by that invocation and removes a directory only if its device/inode still matches the directory it created and it is empty. `validation/fixtures/code-drift-checkout/scripts/evidence/geometry.py` is the complete altered-helper fixture; it appends a unique harmless marker. The runner executes the immutable captured helper bytes instead, and the marker does not appear in the loaded module. The control result retains the fixture hash and the complete directory-replacement failure evidence, including the partial write and both directory identities.

Admission bounds each original/decoded file to 32 MiB and each full input/code/fixture/output phase to 256 MiB. The original gzip source bytes and decoded byte counts are charged together. Every run uses its own fresh destination. Failed evidence is not overwritten or presented as a passing vintage.

## Original scoped subjects and retained context

The exact identity roster is inherited from the prior issue and retained comparison. All eight Atlas records identify USA ADM2 county subjects with Georgia parent `framework:province:georgia:99c5fb82481b` and a 2018 geoBoundaries source/reference vintage. Census county GEOID, state code, name and LSAD values provide a scoped county-tier identity crosswalk. Five subjects are coastal screen cases; three are interior comparison controls.

| Census GEOID | County | Atlas identity suffix | Comparison role |
| --- | --- | --- | --- |
| 13039 | Camden | `52423323B71362647483761` | Coastal screen |
| 13051 | Chatham | `52423323B68249799438553` | Coastal screen |
| 13127 | Glynn | `52423323B35006791438696` | Coastal screen |
| 13179 | Liberty | `52423323B31615661575159` | Coastal screen |
| 13191 | McIntosh | `52423323B58673559392327` | Coastal screen |
| 13231 | Pike | `52423323B93853380479562` | Interior control |
| 13249 | Schley | `52423323B40186233786127` | Interior control |
| 13273 | Terrell | `52423323B62158301450735` | Interior control |

This is exactly the issue roster, not a full Georgia county inventory. The 2018 and 2025 TIGERweb sources cover the retained Georgia/Kentucky comparisons; the 2026 Census TIGERweb request contains these eight GEOIDs only. None proves neighboring county coverage, municipal granularity, shoreline completeness, or a legal line.

## Preserved sources and limitations

The original source bytes, request receipts, retrieval dates, vintage metadata, license notices and prior numerical outputs stay in their original packets. The 2018 Census county source and 2025 Census county source remain pinned in `data/regional-review/regional-review-528e53393a4376b4/`; the 2026 eight-county response, layer metadata, retrieval receipt, Census boundary-change notes, LSAD table and TIGER/Line technical document remain in `data/regional-review/coastal-reference-check-428/`. Their exact whole-file hashes are in the retained original input inventories and evidence manifest at their original baselines. No source is re-downloaded or substituted here.

The Census comparison uses statistical county/equivalent features, not a legal boundary determination. The 2026 AREAWATER unit remains conditional; its quotient is not certified as an area share. Invalid Census comparison geometries are repaired only in memory. The inherited geoBoundaries 2018 reuse terms remain unresolved; no variant is silently selected or copied into this packet. Lower coastal overlap does not identify whether water, marsh, islands, generalization or another representation choice explains the difference. The packet does not adjudicate those questions and proposes no geographic correction, regional approval, import, production write or publication.

## Evidence and unresolved merge-contract issue

`source-assessment.md` carries forward the source/parent and per-subject limits. `engineering-follow-up.md` records a separately verified constraint in the issue's current evidence pins: the required evidence-v1 manifest accepts only one baseline commit, but the exact pins combine the pre-#1227 source vintage and #1227's later original outputs. This packet does not alter shared evidence gates or claim that the incompatible pin set passed them.

`validation/github-issue-1381.json` is the complete issue JSON returned by the GitHub API on 2026-10-07 19:13:04 America/Los_Angeles (50,128 bytes, SHA-256 `00348c02b894e8d242945adb79d41540884afe97729271451619598dd90baa63`). It preserves the exact issue acceptance and pin map used for the compatibility check.

## Latest fresh-main reproduction (2026-10-07 19:17 PDT)

After refreshing the isolated branch to current `origin/main` `97291daccaa44e9c67bba9ae87ceaada641226da`, two additional actual CLI runs (`current-main-a`, `current-main-b`) completed with Python 3.12.14, Shapely 2.1.2 and pyproj 3.7.2. `--verify-pair current-main-a current-main-b` passed. All four scientific products match the retained originals byte-for-byte: admission `1e2a4d71f1badcae12ed1f71e102c132ff6a30be12ca7b35f3e36eecc4dd3e47`, comparison `2c2fe3fd099df52623226597fa98b27b3eac23c0febed3b6d82aa1cb16d85251`, positive control `a339194e98f952d122c03504c33e52b95c888b3ce808c64573be976f7e5013e9`, and negative control `4225c2cd188ac41de8032926c1c5eb34d42af7baa58e7438ddf58abbd8cbf0c8`. `--controls-only` also passed from this base. These runs update reproduction confidence only; the separate evidence-v1 baseline pin failure remains.
