# Issue #491 — Colombia interior batch 2

## Scope and decisions

This packet accounts for every one of the 190 exact pinned member IDs in `scope.json`. It covers seven complete department cohorts (Cauca 42, Putumayo 13, Valle del Cauca 42, Risaralda 14, Córdoba 30, Quindío 12 and Huila 37); Colombia itself is partial (190 of 1,122 current members). `assessment.json` gives each assigned location its exact parent chain, exact source ID/name crosswalk, source and current component/ring/vertex/bbox descriptors, decision and unresolved findings. All 190 decisions remain `insufficient_evidence` for full geographic approval. This acknowledges source identity where established while retaining open questions about current validity, semantic role, settlements and physical completeness.

Every assigned `original_id` matched a unique geoBoundaries 2020 Colombia ADM2 source `shapeID` (190/190), and every current display name exactly matches the matched source label (190/190). Source metadata names DANE as the underlying source and declares 1,122 ADM2 units, 2020 vintage, CC BY 4.0. The source metadata's canonical-role field is blank; DANE MGN 2024 feature rows and their license were unavailable in the prior source investigation. Thus the crosswalk supports traceable administrative identity, not current official status or tier suitability. Repeated/near-repeated names must be resolved with IDs and parent chains, never name-only joins.

The assigned locations comprise seven complete department cohorts as enumerated above. Every row has its province → Colombia area → Western South America region → subcontinent → continent chain from the pinned Atlas hierarchy. Department parent roles, footprints, combined area purpose and all current official rows remain insufficiently verified. No structure count, ADM number or EU5 count is treated as semantic proof or quota.

## Exhaustive geographic screens and findings

- **Location granularity and source role:** All 190 source features are uniquely matched ADM2 features. The present-day DANE municipality/department roster and exact source role still require an authoritative current crosswalk. No municipality is promoted or demoted from size alone.
- **Parent chains:** Every location has a complete recorded hierarchy chain and belongs to one of the seven issue-pinned full department cohorts. The full list of descendants is the scope, not an extrapolation to other Colombia packets.
- **Settlements:** No complete current official settlement point inventory was obtained. The DANE Centros Poblados DIVIPOLA 2013I service is an older lead with inaccessible rows and unstated license in retained item metadata; it cannot support a present-day complete settlement decision.
- **Remainders, islands and disconnected territory:** Source and current component/ring/vertex descriptors are recorded for all rows. No exhaustive DANE register of unnamed remainder units, island list, hydrography or physical-territory inventory was joined. These remain explicit unresolved scope gaps; component counts alone are not conclusions.
- **Physical land:** GSHHG 2.3.7 full-resolution 2017 level-1 polygons were screened against all 190 pinned source representative points; every point falls within a physical-land polygon. Four source level-1 polygon centroids fall inside an assigned current municipality. Full source and selected-record hashes are in `sources.json`; the 30 complete matched records are retained under the stated LGPLv3+ terms. These are point screens, not boundary, island-name, settlement, hydrographic or administrative proof.
- **Neighbor consistency:** `neighbor-screen.json` compares exact consecutive coordinate segments in all 1,122 source features and all current Atlas features. It finds 459 assigned internal source adjacency pairs and 458 current pairs, with one source-only edge: San Miguel (La Dorada) ↔ Puerto Asís, both in Putumayo. The source shared line is 8,261.93 m. An OGR overlay in EPSG:32618 finds zero exact shared-line length in the current simplified polygons, but 8,185.22 m of the source edge falls within 5 m of each current boundary. This is consistent with a small representation/precision difference. See reproducible `investigate_putumayo_pair.py` and `putumayo-pair-investigation.json`. It does not justify moving either boundary. Verify source precision and complete geometry before any correction; no geometry changed.
- **Political/historical distinction:** Current reference polity and past sovereignty/ownership are not inferred from municipal source membership. Historical attributes need separate dated evidence.

## Sources and lawful retention

`sources.json` records canonical URLs, publisher/source attribution, dates, vintage, stated license, retained byte sizes/hashes, access status and restoration steps. The 210,605,856-byte 2020 ADM2 raw source and its 974-byte metadata were lawfully retained with CC BY 4.0 attribution in the already merged #492 packet; this packet references those exact hashed bytes to avoid another 74.8 MB copy. Reproduction checks both gzip and raw digest. DANE service metadata records are likewise retained and hashed in #492; no service feature rows are copied because the layer queries were blocked and item `licenseInfo` was blank. GSHHG 2.3.7 (LGPLv3+) was downloaded and screened for this packet’s full 190-ID scope; the 30 relevant full records are retained with hashes. No source evidence is silently treated as contemporary when its vintage is historical.

## Reproduction

From the repository root in a fresh checkout containing merged #492 source bytes:

```sh
python3 data/regional-review/regional-review-58ad57d566ac2b50/screen_gshhg_colombia.py /path/to/gshhs_f.b
python3 data/regional-review/regional-review-58ad57d566ac2b50/investigate_putumayo_pair.py
python3 data/regional-review/regional-review-58ad57d566ac2b50/audit_neighbors.py
python3 data/regional-review/regional-review-58ad57d566ac2b50/build_assessment.py
python3 data/regional-review/regional-review-58ad57d566ac2b50/verify.py
```

The scripts read the pinned Atlas baseline and hash-verified sources, and write only within this issue's owned directory. Restore the archive from the exact URL and verify both the archive and `gshhs_f.b` digests in `sources.json` before running the physical screen. They do not edit geography data. Neighbor equality is a conservative exact-segment screen, not a polygon overlay or regional boundary certification.

## Bounded follow-up

Create/link a source-restoration issue for these exact 190 IDs to obtain licensed DANE MGN 2024 department/municipality rows, the available dated settlement points with a lawful reuse basis, and current authoritative physical/island/remainder sources. Investigate the Putumayo source-only exact-edge pair with overlay/precision evidence. These findings do not approve Western South America or enable historical imports; engineering integrates accepted findings and validates/publishes the full regional branch first.

Source restoration is tracked in bounded child issue [#587](https://github.com/ChengshuLi/WorldAtlas/issues/587), blocked on lawful current DANE service evidence and pinned to this exact 190-ID membership digest. The Putumayo exact-edge lead remains for source-coordinate overlay review under #491/#489 integration; it is not an inter-region conclusion.
