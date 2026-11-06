# Caucasus expanded watershed audit (research, 2026-11-05)

These are proposals, not selected Neon changes. The selected baseline includes the approved Anapa and Abin changes. We compared it with labeled interfaces from JAXA AW3D30 v4.1 elevation and mapped OSM river/stream networks. Terrain labels are seeded with those mapped networks; the station tests measure consistency with that same model, not independent validation. Segment numbering is analytical: the stored line itself is continuous.

## Eastern section (segment 4)

| Area | Existing natural stream ways crossed | Proposed | Existing / proposed distance | Historical draft163 land centers |
|---|---:|---:|---:|---:|
| Kurdul / Qaraçay | 4 | 0 | 10.8 / 17.1 km | 42 |
| Akhtychay / Şinçay | 5 | 0 | 25.3 / 37.2 km | 132 |
| Qusarçay-area | 1 | 0 | 3.0 / 6.9 km | 51 |

All three candidates are simple, connect to the selected line at both ends and preserve overall endpoints. After all three, the line intersects none of the 265 complete mapped natural river/stream ways in the 12 eastern corridor extracts. It still crosses two mapped canals; those artificial works are not natural drainage divides. The Kurdul model includes JAXA product pixels filled from SRTM; that is the published JAXA product, not an independent JAXA-only check. Counts are illustrative against the historical draft163 physical mask, not a current rebuilt map.

Candidate cut file-byte SHA-256: Kurdul `1a498eb68d0b68d9a0c25aa1c425df3c3294eacf9f07fe45abf761e3abd6a102`; Akhtychay `f8085a0e08ffc7ab5c36e35c98c7e859b3b5d96e0f6264af36a072c8c5f9cdca`; Qusarçay area `da913474dce7c8cc15e077fcdf485e1fa99dad1b2698a9b43df7a3268ed64ab2`.

## Central section and adjoining west

- Jvari: a longer continuous candidate now covers an additional crossing west of the original proposal. It replaces 14.3 km with 19.6 km, crossing zero rather than four natural mapped ways in an extract of 689 complete ways, with 51 draft163 land centers in the changed faces. File SHA `b6e596972d32f3ae500817434f75697445626c8f477ee80e99faf6123160d123`.
- Klukhor: a continuous JAXA interface groups both north-draining headwaters against the south-draining system, eliminating the earlier artificial connector. Its 11.2 km replaces 8.6 km; 21 draft163 centers. SHA `a3c3db2f128add5d8c2fe17f9db2aab41ce5290b310b4313b006530467ef9325`.
- Malaya Laba: 2.1 km becomes 3.1 km, crossings two to zero, 12 draft163 centers. SHA `fbeeba77c976c6340857b3c157371cda7133ac99f02341ca20f2caa3dd739109`.
- East of Jvari / Arthmos: 12.9 km becomes 17.5 km, crossings five to zero, 49 draft163 centers. SHA `a5aab4956a3fbe5b6c57dfcbc36bda6baa06a526c263bad41d22b3ee3da66e7d`.
- Magana: 6.1 km becomes 7.9 km, crossings three to zero among 717 complete mapped ways, 20 draft163 centers. SHA `d6d262770bc0662a3dfe3bde29ef39b091c36999fc41baa3ffccd052e08108f2`.
- Bushuyka / Psikhashkha at the adjoining western edge: 3.4 km becomes 4.4 km, crossings ten to zero, 12 draft163 centers. SHA `02aab37e9711dbff5d2d5f57d8cd0fba3ecb4763e41c02bfed4972082d7e1b47`.

The additional crossing screen flagged further local intersections that still require examination; this report does not claim that the central audit has resolved all of them. Mapped streams do not necessarily include every real stream, and the modeled interface is a terrain-derived estimate. The numeric station checks are not evidence independent of its seeds. Proposals require explicit selection and source-catalog integration before production use.

## Eastern terrain-profile follow-up

A 500 m station screen of the three-proposal line covered 641 stations at 47–49.5 degrees E. Four locations had a center at least 10 m below both side samples at both 250 m and 500 m: approximately (47.16936, 41.50861), (47.43227, 41.27127), (47.74556, 41.19173), and (49.06595, 40.89166). Another 14 stations could not be evaluated with the available valid 3-by-3 samples. A low profile can be a mountain pass, so these are leads to check, not demonstrated boundary errors; no additional correction has yet been established. This is a surface-profile diagnostic, not a complete drainage trace.
