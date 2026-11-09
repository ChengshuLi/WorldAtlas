# Caucasus expanded watershed audit (research, 2026-11-05)

The user approved the nine proposed changes, and they are selected in the Neon research revision. The baseline includes the approved Anapa and Abin changes. We compared it with labeled interfaces from JAXA AW3D30 v4.1 elevation and mapped OSM river/stream networks. Terrain labels are seeded with those mapped networks; the station tests measure consistency with that same model, not independent validation. Segment numbering is analytical: the stored line itself is continuous.

## Eastern section (segment 4)

| Area | Existing natural stream ways crossed | Proposed | Existing / proposed distance |
|---|---:|---:|---:|
| Kurdul / Qaraçay | 4 | 0 | 10.8 / 17.1 km |
| Akhtychay / Şinçay | 5 | 0 | 25.3 / 37.2 km |
| Qusarçay-area | 1 | 0 | 3.0 / 6.9 km |

All three candidates are simple, connect to the selected line at both ends and preserve overall endpoints. After all three, the line intersects none of the 265 complete mapped natural river/stream ways in the 12 eastern corridor extracts. It still crosses two mapped canals; those artificial works are not natural drainage divides. The Kurdul model includes JAXA product pixels filled from SRTM; that is the published JAXA product, not an independent JAXA-only check.

Candidate cut file-byte SHA-256: Kurdul `1a498eb68d0b68d9a0c25aa1c425df3c3294eacf9f07fe45abf761e3abd6a102`; Akhtychay `f8085a0e08ffc7ab5c36e35c98c7e859b3b5d96e0f6264af36a072c8c5f9cdca`; Qusarçay area `da913474dce7c8cc15e077fcdf485e1fa99dad1b2698a9b43df7a3268ed64ab2`.

## Central section and adjoining west

- Jvari: a longer continuous candidate now covers an additional crossing west of the original proposal. It replaces 14.3 km with 19.6 km, crossing zero rather than four natural mapped ways in an extract of 689 complete ways. File SHA `b6e596972d32f3ae500817434f75697445626c8f477ee80e99faf6123160d123`.
- Klukhor: a continuous JAXA interface groups both north-draining headwaters against the south-draining system, eliminating the earlier artificial connector. Its 11.2 km replaces 8.6 km. SHA `a3c3db2f128add5d8c2fe17f9db2aab41ce5290b310b4313b006530467ef9325`.
- Malaya Laba: 2.1 km becomes 3.1 km, crossings two to zero. SHA `fbeeba77c976c6340857b3c157371cda7133ac99f02341ca20f2caa3dd739109`.
- East of Jvari / Arthmos: 12.9 km becomes 17.5 km, crossings five to zero. SHA `a5aab4956a3fbe5b6c57dfcbc36bda6baa06a526c263bad41d22b3ee3da66e7d`.
- Magana: 6.1 km becomes 7.9 km, crossings three to zero among 717 complete mapped ways. SHA `d6d262770bc0662a3dfe3bde29ef39b091c36999fc41baa3ffccd052e08108f2`.
- Bushuyka / Psikhashkha at the adjoining western edge: 3.4 km becomes 4.4 km, crossings ten to zero. SHA `02aab37e9711dbff5d2d5f57d8cd0fba3ecb4763e41c02bfed4972082d7e1b47`.

The additional crossing screen flagged further local intersections that still require examination; this report does not claim that the central audit has resolved all of them. Mapped streams do not necessarily include every real stream, and the modeled interface is a terrain-derived estimate. The numeric station checks are not evidence independent of its seeds. The selected line and its source bundle are recorded in the research revision. The source gate and actual-generation closure proofs require updates before production use.

## Eastern terrain-profile follow-up

A 500 m station screen of the three-proposal line covered 641 stations at 47–49.5 degrees E. Four locations had a center at least 10 m below both side samples at both 250 m and 500 m: approximately (47.16936, 41.50861), (47.43227, 41.27127), (47.74556, 41.19173), and (49.06595, 40.89166). Another 14 stations could not be evaluated with the available valid 3-by-3 samples. A low profile can be a mountain pass, so these are leads to check, not demonstrated boundary errors; no additional correction has yet been established. This is a surface-profile diagnostic, not a complete drainage trace.

## Expanded Arthmos continuation and residual screen

Extending the east-of-Jvari OSM and JAXA window to 44.82°E pulls the divider candidate through the two streams near 44.722°E. The longer cut replaces about 30.9 km of the current proposed route with 36.1 km, removes four crossings (ways 73017061, 73017252, 73026732 and 73027855) in a complete 680-way local extract, remains simple, and joins the proposed line at both ends. Candidate cut SHA-256 `a16266c4464126b80486e65ebb04c3f7b6ee3da9a24baab381556b6dfdf4ef61`.

After adding that extended cut, remaining central mapped stream crossings in the screened windows are at approximately 39.989°E (two unnamed streams), 45.364°E (two unnamed streams), 45.813°E (two stream ways, one crossed twice), 46.610°E (Goredabor), and 46.868°E (Dakkichay). The current evidence does not yet identify a connected, source-supported alternative with defensible outlet seeds for these locations. They are open audit items, not proposed geometry changes. Nearby streams at the 40.475°E window are over 2 km from the terrain-flag point and are not treated as a direct pass crossing.

The four eastern terrain flags likewise do not prove a divide error. The nearest mapped streams are 335 m, 265 m, 2.9 km and 1.6 km away; the first two deserve targeted headwater tracing. The station screen sampled 641 points, with four low-profile flags and 14 invalid sample neighborhoods. A line-only overview is saved as `caucasus-seg3-4-overview.png`; detailed local before/after images show the drainage and each cut.

## User-approved proposal bundle and segment 1 geodesic recheck

The nine approved proposed cuts were first recomposed in source order into a simple 10,084-vertex Caucasus LineString with both original endpoints preserved, SHA-256 `5e8d3ab116112881d7bc515f197cbe980933e0a8ac673deb0bfb0af5fd900beb`. The WGS84 source regeneration below supersedes that earlier geometry.

The PR4 WGS84-distance follow-up was checked against the Anapa source assembly. Ranking the 56 exact intersections between the pinned baseline and author route by coordinate-linear station and by WGS84 geodesic station produced the identical order and identical fifth join at 37.42406995874469°E, 44.84168781056519°N. Reassembling the Anapa opening at that join produced the same 2,320 vertices and the same canonical geometry SHA-256 `e3dd7f326c0247f4d9f4c4c61b7c31782a5fc1b9e850d164cf46e729cbb60929`. That preliminary test reused the old selector-derived baseline and was insufficient to claim the full boundary was unchanged. A later WGS84 selector replay rebuilt the baseline from the pinned raw HydroBASINS and author data: 142 baseline vertices moved at most 0.000243 m. The exact coastal intersection and fifth join remained unchanged; the assembled Anapa line changed 48 coordinates, at most 0.000188 m. The full selected-boundary replay is documented in `scripts/caucasus-audit/CAUCASUS-WGS84-REPLAY.md`.

The 41 raw OpenStreetMap API responses used by these proposals are bundled in R2 at `sources/osm/caucasus-approved/20261105/source-responses-116d078c59a6.zip`. Full R2 readback matched SHA-256 `116d078c59a6fc46786ec369450483d809c187bcaa632f01c5081c63f04e5706`; its manifest pins each original response. Its Neon source reference is `osm-caucasus-approved-drainage` version `20261105-116d078c59a6`.

A complete replay of the nine approved changes from fresh R2 readbacks produced WGS84 geometry SHA-256 `3be87f6ec29be709a07c07c04ce62b6fb00e33f6b35020781a088be5b2d8e8b9`. This regenerated line is selected in the editable Neon revision `v8-mainland`, with recipe SHA-256 `9c90e4432a538b62bd0409802fb678a59d777863748fea20a4659ad813d72215`. The full selected geometry and recipe were read back and compared equal to the replay inputs; exporting the recipe as canonical JSON reproduced its hash. All eight JAXA original-tile source relationships are now labeled as boundary derivation inputs. Code is pinned in Neon to PR4 commit `a1ec3746753bb19467ae730dc3ab6b0f3ad327e2`. The earlier preliminary Anapa invariance claim was incorrect.

A second complete replay used the canonical recipe exported from Neon and freshly verified R2 source readbacks. It reproduced the selected GeoJSON byte for byte. All 16 source inputs have matching R2 catalog records and boundary-source links.
