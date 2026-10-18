# Original held-cell exception evidence packet

Status: **0 accepted, 3 pending independent review, 0 otherwise resolved**. The three rows remain in their original selected package with their existing owner, source ID, land class, diagnostic hold reason and zero repair credit. This packet adds traceable evidence and finite questions only. It does not qualify, clear, accept, reassign, select or deliver a cell.

`original_land_class` records the source-backed physical class (`mapped_land_support`). `diagnostic_hold_reason` records the existing `territorial_exclusion_cells` veto. They are separate facts: a mapped-land observation does not resolve territorial/source applicability.

## Liberia — Buu-Yao, one original key

Original key `(y=126219, x=124938, owner=26987)`, source `gb:LBR:ADM2:62588387B45934307689461`, package `gb-LBR-ADM2--repair-evaluation`. Its original physical class is `mapped_land_support`; its existing hold reason is `territorial_exclusion_cells`.

The normative center is `(-8.43747854412851, 6.663368865472858)`. The exact pinned Buu-Yao target geometry has no center hit. The matching whole-target physical report's `mapped_land_support` geometry contains this center and adjacent center `x=124939`; that run-level geometry is not source-target membership. The retained one-cell causal query also finds one interior hit in CIV ADM1 Montagnes. The complete eight-operand CIV negative set has one such interior hit and seven no-hit results. The exact original result and complete operands remain in `liberia-causal-result.json`; the pinned-source recheck is reproduced in `reproduced-native-centre-queries.json`.

This is a candidate for a documented no-repair exception under the original contract, not a repair candidate. The contract requires every original interval to be either a qualified additive repair at its recorded location or a documented exception, plus selected-native conservation and source/physical witness checks. The finite question is whether the original target/physical geometry difference is explained by the original source vintage and whether the package's exception clause applies after review. Keep the hold until that is answered and the ordinary package process adopts a disposition.

The exact contract body is `liberia-original-package-contract.json`. Its extraction is reproducible from the pinned stock `source-batch-intervals.mjs` and `source-package-queue.json` at commit `252f2aa1e6309b6990985dec73611d6df0e11c70`:

```sh
node coordination/engineering/global-current-cell-work-queue-20261014/source-batch-intervals.mjs gb-LBR-ADM2--repair-evaluation OUTPUT_DIRECTORY
```

The immutable output SHA-256 and extractor/manifest Git object IDs are recorded in `input-pins.json`. Re-running extraction would reproduce the original package operands; it is not needed to repeat the completed physical observation.

## Egypt — Nakhl, one original key

Original key `(y=108405, x=156464, owner=18676)`, source `gb:EGY:ADM2:37247803B50825531526089`, package `gb-EGY-ADM2--repair-evaluation`. Its original physical class is `mapped_land_support`; its existing hold reason is `territorial_exclusion_cells`.

The exact center `(34.85326091102584, 29.711429740592195)` is interior to the complete retained Egypt Nakhl ADM2 target and Israel Southern District ADM1 reference geometry. It is outside the retained Israel Be'er Sheva ADM2 and Saudi Tabuk ADM1 polygons. Separately, the complete foreign-bounds report records overlapping/touching feature-part **bounding boxes** for three foreign operands. This is a conservative bounds screen, not a polygon-intersection result and not proof of a foreign cell hit.

The source evidence pin is the full original `source-evidence-003` body at `f988605570667858062905c04c31231564882d11`, blob `586cd44911608aa0f5c97e43de742b5deb656d78`, SHA-256 `90fbec8419b072ce254dc4b61df790274b999c7bb5e2d9bda0dd692e8b50d4f9`. It contains Nakhl, its owner, complete territorial-exclusion references and source membership. The previously cited `supported-inputs-001` source body is a narrower supported subset and does not replace it.

The complete foreign-bounds report body is at accepted-main commit `07c74ff101d4ab5e679255ed85c402356aa54a42`, blob `791ee8996bba9ecf7d3711bc6eb5deb68e5358cc`, path `coordination/engineering/egypt-original-repair-20261017/source-review/foreign-bounds-001/complete-foreign-bounds.json`, 478,761 bytes, SHA-256 `80597b0392fdafe5d5939dd8ed5c4f8f38a12c3b367a5af168468e781a192768`. Its distinct report baseline is commit `21984e9ec4ec7370bc807e2da23cea2228747698`, and its method is pinned at `e62784211144e01fead91ef1c50b7c9db9f5595e`, path `coordination/engineering/egypt-original-repair-20261017/method/screen-whole-foreign-bounds.mjs`, blob `c624d9caec99b1e07b26511d3f96651a8909ca41`, 9,338 bytes. The method is a bounds screen; it does not calculate polygon intersections.

The finite question is whether an authoritative, applicable boundary/source record resolves this exact point and how the retained Israeli and Saudi administrative products apply. If not, an independently reviewed unresolved exception can be considered under the package contract. No legal status is inferred here.

## Egypt — Sharm el-Sheikh, one original key

Original key `(y=109906, x=156358, owner=18637)`, source `gb:EGY:ADM2:37247803B39887765706268`, same Egypt package. Its original physical class is `mapped_land_support`; its existing hold reason is `territorial_exclusion_cells`.

The exact center `(34.70770427896829, 27.905508542964288)` is interior to the Egypt Sharm ADM2 target, Egypt South Sinai ADM1 and Saudi Tabuk ADM1 reference polygons. It is outside the retained Saudi Tabuk ADM2 polygon. Separately, the complete foreign-bounds report retains overlapping/touching feature-part bounding boxes for both Saudi levels. This is not polygon-intersection proof or a center hit.

No complete authoritative Sanafir/island coastline polygon was found in the public materials previously inspected. The finite question is whether a complete, authoritative and applicable terrestrial geometry identifies the land surface at this exact center. A maritime boundary segment, general map or representative island coordinate cannot substitute for that geometry. Keep every existing contact and the territorial hold while unresolved.

## Reproducible native-center query

`reproduce-native-centres.mjs` re-runs all 18 retained numerical center queries using `native-grid-pinned.mjs`, the exact repository source file pinned at commit `0005013ac140835fd35af6a2665973250118f118`, path `src/native-grid.js`, blob `3e1d3e7e6012b5b571345caad029ab7d124c07fd`, 50,250 bytes, SHA-256 `66b453bbb2e001b9ff56bd754d55087f5919845dceeefd886016494cefa1d3e0`. It loads every source evidence, whole-family payload, physical report and native latitude table by immutable commit/path, verifies Git blob IDs, byte lengths and SHA-256 values, and does not fetch. If a partial checkout lacks a tree entry but has the corresponding pinned file in its working tree, the script accepts it only after exact object/hash checks.

Run with Node.js 20 or newer:

```sh
node coordination/engineering/original-held-cell-exceptions-20261018/reproduce-native-centres.mjs /path/to/WorldAtlas /tmp/held-cell-native-centres.json
```

The checked run in `reproduced-native-centre-queries.json` reproduced all 18 retained hit lists. This executor used its exact-hash-verified working-tree fallback for the EGY ADM1 gzip body because that file is present in the partial checkout but absent from its local `07c74ff` tree object; the output records that one fallback. A complete clone with the pinned tree object uses `git show` for it as well. The Liberia historical causal result reports scanner SHA-256 `81ebf5207b2f0127ed8bdacf2f50f02c01d4be80b7586b470d049def3156faee`; the later repository-pinned recheck uses SHA-256 `66b453bbb2e001b9ff56bd754d55087f5919845dceeefd886016494cefa1d3e0`. Those are different hashes. The packet does not claim byte identity or erase the historical result; the runnable recheck explicitly reports that distinction and compares its numerical hits to each retained result. Both pin the same decoded normative latitude table SHA-256 `66db3d02ede56a75e9c58426ad1388552be3bf7e5e4477476f198983b7436d23`.

The numeric queries establish only native contact against the pinned geometry. They do not establish source applicability, legal sovereignty, dry land, land truth beyond the cited physical class, qualification, acceptance, selected state or repair credit.

## Disposition and acceptance boundary

The partition in `disposition-partition.json` is explicit: accepted `[]`; three pending cases; zero otherwise resolved. Original held class, source, owner and holds remain unchanged. The finite follow-up questions are: (1) Liberia source-vintage/physical-geometry reconciliation; (2) Nakhl applicable boundary/source evidence; and (3) Sharm complete authoritative island/land geometry with date, datum and accuracy. Until evidence and independent review resolve those questions, all three remain held.

No exception is accepted by this packet. Any later selected delivery must still pass the original package's owner-zero, conservation, source/physical-witness and emitted-output checks. No owner reassignment or repair credit is claimed.
