# Maldives ADM1 original-package evidence proposal

This is an evidence-only, unaccepted proposal for `gb-MDV-ADM1--repair-evaluation`, based on exact queue/data commit `7fc7fae5d0caa4153dad87537097591249193117` and frozen queue source commit `a61b6f9e7f88b1da380e3a834f89d7509132ed71` (queue blob `9c9a9bc83627afd3e8435ff4009e39530543bf54`). It retains all 850 original cells and all 228 intervals as held/proposed unresolved. New accepted repair, exception, or historical-key credit is zero; prior exact-key credit remains unknown pending receipt reconciliation.

## Exact checks

The stock `scripts/observe-selected-owners.mjs` ran once on data and code commit `7fc7fae5d0caa4153dad87537097591249193117`. Its complete 850-key output is `selected-owner-observation.json` (182,428 bytes; SHA-256 `93f348c76499c464afcb545bdea3f570e51606419d4a65e88a8ad458ec91b658`). It reports 0 nonzero base owners, 0 nonzero additive owners, 0 nonzero effective owners, and 0 overlaps. This is a selected-product ownership observation, not source qualification or acceptance.

`reconcile-mdv-evidence.mjs` is the committed reproducible exact-key join driver (code commit `f2659d0329732c8cf4ea193d9b308a132476ad0f`, blob `8632b4f54655b6778841d80ecdb703663faf560d`, SHA-256 `880447000ca41a73aef2138d2d6d0e6c7a156849faed741cb99d8b547dbee70b`). From the repository root run:

```sh
node coordination/engineering/mdv-original-repair-evaluation-20261021/reconcile-mdv-evidence.mjs
```

The resulting `proposed-disposition.json` has 228 exact interval rows totaling 850 unique keys. It binds each interval's queue owner/feature to the same retained source-candidate block contact and lineage row, then joins physical support, inland-water support, physical unknown-envelope/residual blocks, and the exact observation rows. The result is 850/850 archived land-support keys, 0 water-support keys, 0 unknown-envelope/residual hits, and no source-candidate feature outside the package's six listed features in these retained block runs. Per-feature counts are 42130→159, 42131→380, 42133→1, 42136→15, 42138→5, 42148→290. Per-owner cell/interval counts are 27463→380/95, 27464→290/59, 27465→5/4, 27472→1/1, 27476→15/11, and 27478→159/58.

The disposition artifact is 345,448 bytes (SHA-256 `53390d30b36b09911df7d8c4b28e123d533e9375c385ea3f5b1251e73b41fc4e`). It records all 228 intervals and their 850 unique keys as proposed, held, unaccepted, and not repair-qualified. No interval is asserted to have an accepted documented exception.

## Source and limits

The retained source catalogue identifies `gb:MDV:ADM1` as a 21-feature product with a 2017 represented-year claim, recorded source “OpenStreetMap, Wambacher,” `boundaryCanonical: Unknown`, and Open Data Commons Open Database License 1.0. Its retained compressed payload is 5,927 bytes (SHA-256 `abdabbb643f6b8acf1df4c85083a4f77bdb471e1caad65030446584d6e8b713c`); decoded payload is 20,566 bytes (SHA-256 `834d5c1f8bcaf9cb3733b5faed95a238e9efe6f4986b6197642aea094c6e4ef2`). Rights compliance was not assessed. The roster, candidates and lineage identify the six package features and owners but do not prove current applicability.

The retained source-candidate runs show the listed feature contacts per exact key; they do not establish a complete current alternative-source competitor inventory. The package's retained physical unknown-envelope/residual blocks are empty for blocks 030–032, but no separate current territorial-exclusion dataset was demonstrated. Archived raster support is not a current legal boundary or water determination. Current authority, current boundary, unique applicability, sovereignty, rights compliance, complete competitor coverage and historical accepted-key overlap remain unresolved. No source geometry was rerun, and no source-center or whole-cell geometry claim is made here.

Issue #131 remains a separate 50-location source/semantic review. It is not a native-key repair receipt and was not changed by this work. Every interval remains held, repair qualification is false, and documented-unresolved acceptance is false pending independent review and the normal package acceptance process.
