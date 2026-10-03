# Issue #496 — Ecuador, Galápagos and Peru interior batch 7

## Scope and status

This is an evidence packet for the exact 228 location IDs pinned in `scope.json`: 110 Ecuador, all 3 Galápagos and 115 Peru. It is a research tranche inside the published continent/subcontinent/region baseline, not a new partition or regional approval. The source row for every ID, its complete current parent chain, geometry summary, administrative crosswalk, uncertainty and individual decision are in `assessment.json`. The snapshot is dated 2026-10-03 and pins the current release fingerprints there. The machine-readable issue spec, exact body digest and reservation receipt are retained in `issue-metadata.json` and `claim-receipt.json`.

Current tally: 228/228 individually assessed; 228 administrative identities crosswalked; 1 source-role/effective-date conflict requiring correction follow-up; 227 insufficient evidence for full geography approval. “Insufficient” is explicit: settlements, named/disconnected physical land and full source-to-current geometry topology were not proved. No row is silently accepted by example or quota. EU5 counts are scale references, and Antarctica is excluded.

## Findings and proposed action

* Ecuador 2019 geoBoundaries ADM2 declares 224 administrative units but its pinned feature file has 223. The independent INEC/OCHA 2023 ADM2 roster has 224 records. The 2024 gazetteer has 223 rows but is not directly comparable: it omits the old `Zona No Delimitada` ADM2 codes and also contains different special features. All 113 Ecuador IDs in this issue crosswalk to official 2023 identities; 112 have a same-name/current-parent match in the newer gazetteer.
* Las Golondrinas (`gb:ECU:ADM2:8360857B1829680752404`) is the one correction-needed finding. The 2019 source treats it as a canton under Imbabura; INEC/OCHA 2023 lists EC9001 under `Zona No Delimitada`, and the 2024 ADM2 gazetteer has no matching row. This is a dated role/source conflict, not evidence to change the parent or geometry. Obtain the current effective administrative source and whole-area physical coverage before proposing integration.
* Manga del Cura is outside this issue (#495), and the 2019 source feature collection also lacks it despite the metadata count. The official 2023 table identifies EC9003 as `Zona No Delimitada`. Coordination was requested on #495 with #489. Do not infer physical or legal assignment to Manabí from the current parent.
* Peru's 115 assigned source IDs all crosswalk to the 196-province INEI roster at 2019-12-31. Three geoBoundaries name strings have mojibake; INEI confirms the canonical names. Name-only joins are unsafe: Ecuador has two Bolívar units, and the pinned Carchi parent selects EC0402. Lima/Municipalidad Metropolitana de Lima and the combined Callao province/department need role/extent interpretation. The full Peru-area review is 89 members in merged #497 plus 115 here; #497 identifies 11 ecological fragments and leaves exact partition alignment open for #489.
* Current assigned geometries contain 225 Polygons and 3 MultiPolygons; Galápagos Isabela, Santa Cruz and San Cristóbal have 2, 7 and 5 components respectively. Five interior rings are inventoried in the row records. NOAA GSHHG 2.3.7 full-resolution level-1 land records provide a screening comparison only; the retained Galápagos candidate set and method are in `gshhg-screen.json`. Candidate centroids fall in the current component counts, but that does not prove named island or shoreline completeness. No authoritative complete settlement inventory or whole-scope island/coast/hydrography roster was established. All 228 rows therefore retain explicit unresolved settlement and physical-land assessments.
* Parent/province/area inventory (33 entries) records full ancestry and workload context. Parent roles and neighboring scales remain review questions. No shared boundary changes are made here. The focused #495 comment requests coordinated treatment of the Ecuador remainder and #489 alignment; no unilateral boundary conclusion is proposed.

## Sources, licenses and restoration

`sources.json` is the canonical source register: publishers, dates/vintages, URLs, licenses, attribution, retained-byte locations, sizes, SHA-256 hashes, exact extracts, and restoration steps are recorded there. Source bytes are retained only where lawful and useful. The Peru geoBoundaries and INEI bulletin bytes are referenced in the already merged sibling #497 packet, left unchanged. The Ecuador source GeoJSON and metadata, INEC/OCHA 2023 and 2024 workbooks, official fact extracts, INEI province roster extract, and GSHHG selected records are retained under `sources/`.

To reproduce the administrative inventory from a fresh checkout, first ensure merged sibling PR #565's packet sources are available, then run:

```sh
python3 data/regional-review/regional-review-a1f74bfb55fcb8c1/build_assessment.py
```

The script validates every retained and peer-source digest and rebuilds only `assessment.json`. To reproduce the GSHHG screen, download `gshhg-bin-2.3.7.zip` from the pinned URL in `sources.json`, verify the archive SHA-256 there, extract `gshhs_f.b`, verify its recorded member digest, and run:

```sh
python3 data/regional-review/regional-review-a1f74bfb55fcb8c1/inspect_gshhg.py /path/to/gshhs_f.b
```

That script writes only selected complete source records and the screening report into this packet. It does not change atlas geography. It requires Python's standard library only. XLSX extraction facts are retained as JSON; the workbook source bytes and extraction method are pinned in `sources.json`.

## Limitations and next bounded work

This packet does not establish current settlement coverage, identify every island/component, certify coastlines or lakes, prove every source/current geometry correspondence, resolve provincial semantic tiering, or approve the regional branch. The 2019/2020 administrative boundary datasets are identity crosswalk references and not a complete physical-land standard. Geographic evidence is kept separate from political ownership and historical sovereignty. Follow-up should acquire dated, authoritative national settlement, island/shoreline and current administrative sources; exhaustively reconcile each issue ID, all disconnected geometry and neighbor consistency; and coordinate any inter-region findings with the affected owner and #489 before engineering integration. Content imports remain gated until engineering publishes a complete regional branch.

## Checks

`verify.py` checks exact scope accounting, row completeness and decisions, source hashes/restoration metadata, cross-reference scope separation and the retained GSHHG subset digest without editing baseline data. The actual GitHub issue metadata and declared `owned_paths` must also pass `scripts/check-handoff-scope.mjs` before PR submission.
