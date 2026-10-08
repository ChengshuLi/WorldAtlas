# France #1329 report-integrity correction (#1489)

## Scope and result

This packet makes an additive correction to reporting from the complete retained France comparison run. It preserves the earlier #1310 evidence and does not change any source, identity, run, geography or release pin. The report program binds the captured open #1489 issue contract and accepted claim, its seven direct issue pins, the original complete candidate/family/contact records, the complete retained geoBoundaries source, the original source transport receipt, current Atlas part 8, and the pinned immutable evidence helper.

The frozen original report claimed four candidate pointsets had no intersection. Recalculation across all 48 retained candidate relation records gives **six** with no intersection: 42 intersect, of which eight are whole-feature covers and 34 intersect without cover. The unchanged source-fitness dispositions remain 11 compatible, 24 partial/unbound, 11 no-compatible-intersection, and two outside the original source domain. The nine families and 16 contact identities are complete and exact. Fifteen contact labels are exact-name identity leads; this is not a crosswalk.

The corrected contact-method text states what the retained runs actually record: all 16 complete original 2022 contact geometries and all 16 current Atlas contact geometries were compared against the complete 333-feature 2026 IGN layer; all 16 intersect, and none are whole-feature covered. These are reconciled historical run results, **not a new overlay or independent geometric recomputation**.

## Source meaning, vintage and limits

The complete retained simplified geoBoundaries France ADM3 source has 320 unique `shapeID` features, represented year 2022, registry metadata updated 2023-01-19 and pinned upstream revision `9469f09`. The original corpus transport receipt records retrieval from the pinned media URL between `2026-10-06T22:17:21.962366Z` and `2026-10-06T22:17:22.894497Z`, SHA-256 `318606bceafa5fea93412c66438f333e35bad41079dc756270e961a213a4d6a0` (6,755,489 decoded bytes); retained gzip SHA-256 is `2a4a7cb9a920655771b4c20494460bb6ec18e5454439391898be3122862e1fbb` (2,449,036 bytes). The source feature attributes do not include parent IDs. All 16 issue contact IDs occur both in this complete source and in the pinned current Atlas data part; the report checks both identity rosters. Current Atlas parent metadata is retained in the original run records, not independently reassessed here.

The original catalogue records Etalab Open Licence 2.0 metadata, while geoBoundaries separately records CC BY 4.0 terms for its derivative products. This packet preserves both statements and attribution. The underlying-source rights chain and legal boundary authority remain unresolved. The 320-feature product is verified as the complete retained source product; this does not establish complete legal/territorial coverage for all French territory or a valid historical interval. Neighboring-country granularity was not re-evaluated in this reporting-only scope.

The original run records a complete 333-feature `ADMINEXPRESS-COG.2026` layer, edition 2026-01-01, retrieved 2026-10-07, body size 156,850,437 bytes and SHA-256 `334c34c5a3ba7f1196198843765b208c5ef744cf31c7fc4d59aa9039b90f86f8`. That full layer remains restoration-only because it exceeds the 32 MiB ordinary-file limit. This correction neither fetches a substitute nor reruns the overlay. The source, temporal identity, legal interpretation, parent correspondence, physical authority, physical source license/completeness and surface status remain unresolved as recorded. Original #1329 remains **Incomplete**; this work is not geographic approval, import authority or publication permission.

## Reproduction and controls

Use Python 3.12 with isolated mode and bytecode disabled. Each successful output requires a fresh vintage name and the actual producer SHA:

```sh
EXPECTED=$(shasum -a 256 research/geography/france-source-fitness-reporting-1329-20261008/report.py | awk '{print $1}')
python3.12 -I -B research/geography/france-source-fitness-reporting-1329-20261008/report.py --repo . run --vintage corrected-run-N --expected-code-sha256 "$EXPECTED"
PYTHONDONTWRITEBYTECODE=1 python3.12 -I -B research/geography/france-source-fitness-reporting-1329-20261008/verify_controls.py --repo .
```

The final pair is `corrected-run-07` and `corrected-run-08`; both ran the same producer SHA, used identical complete retained inputs, and produced byte-identical data outputs. `controls-run-03/control-results.json` records 20 checks: three original CLI defects reproduced and 17 corrected controls passed. The original CLI's intact positive case matches all seven frozen report outputs byte-for-byte. Its negative receipt incorrectly passes a false omission control; its hard-coded counts remain 42/8/34/6 when all candidate relations are removed; and it follows a symlink to overwrite its target. The corrected CLI rejects false controls, changed counts/relations, omitted/duplicate/foreign IDs, mismatched runs, changed issue contracts, baseline pins or producer code, output collisions, live/dangling symlinks and reruns. A controlled receipt-write failure retains partial output with `.publication-incomplete` and no accepted `publication.json`.

The earlier attempt `control-harness-attempt-01.json` records a harness setup failure: its collision fixture selected the already preserved `corrected-run-03` directory. That attempt did not write a control receipt or modify the old vintage. The fixture was changed to use a fresh control-only name; the complete corrected suite then passed in `controls-run-03`. Earlier positive vintages, control runs and failed publication attempts are preserved as historical attempts; only 07/08 and controls-run-03 are the final accepted reproductions for this producer version.

The CLI first validates the complete planned output set, then uses the shared immutable `NewVintage` writer's no-follow/exclusive publication safeguards; the final receipt is written last. Failed or superseded attempts are never relabeled as successful.
