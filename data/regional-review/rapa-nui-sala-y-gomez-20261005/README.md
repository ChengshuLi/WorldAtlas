# Salas y Gómez in the Isla de Pascua commune footprint

**Issue:** #1052  
**Scope:** exactly `gb:CHL:ADM3:31580391B33082267781919`, keeping its existing Atlas ID and parent.  
**Baseline:** merged main `249e396178cfc160fd547ec4487c5d94832fc9af`.  
**Disposition:** research complete; a narrow same-ID geometry correction is supported. No Atlas geography, release pin, history or production data was changed; this packet does not approve any region or authorize imports.

## Finding

Chile's Law 16,441 article 1 defines one Isla de Pascua commune-subdelegation and places Easter Island and Salas y Gómez in the same department. Decree 324 (1991) explicitly identifies the island as part of the Isla de Pascua commune and province, fixes its location at 26°28′17″S 105°21′55″W, and directs official use of the name **Isla Salas y Gómez**. These legal texts establish administrative meaning, not shoreline vertices. The current BCN 2024 commune report identifies the Isla de Pascua commune under Valparaíso Region and Isla de Pascua Province.

The retained geoBoundaries feature is `Isla de Pascua`, 2020 `ADM3` / `Communes`, shapeID `31580391B33082267781919`. Its 166-part MultiPolygon contains a separate island component covering the decree coordinate. Metadata credits BCN Chile and OCHA ROLAC, reports source-data update 2023-01-19 and build 2023-12-12, and assigns CC BY 3.0 IGO. The raw one-feature extract SHA-256 is `fb0ea671f05a6334ec7a867ca5cb46fcedb63c5b3cc25a39115f5879c73986cb`.

The current Atlas feature is a single Polygon stored in `data/geography/part-2.json`, not `part-28.json` as declared in the issue pin. The current representative point remains inside the Rapa Nui polygon. The decree coordinate lies 402,952.804 m from that point. The Salas y Gómez source component measures 162,819.521 m² under the pinned WGS84 helper and has zero intersection with the current footprint. The large Rapa Nui source component intersects the current geometry positively; that comparison is only a control, not a coastline score. See `geometry-results.json` and `geometry-controls.json`.

The official 2022 IDE MINAGRI/ODEPA 1:50,000 line archive contains a coastal line record whose geographic bounds include the decree coordinate; the separate DPA polygon archive has one polygon record with `codcom=05201`, `nom_com=Isla de Pascua`, and covers that coordinate. This is independent mapping corroboration. The portal describes the polygon layer as district-level, while the downloaded row carries commune fields, so it is not treated as an unambiguous legal commune-tier definition. The two small RAR archives were fetched and hashed for this check. The portal does not state redistribution terms; the archives and extracted shapefiles are not included. Exact restoration links, hashes and this limit are in `source/provenance.json`.

## Engineering handoff

Add only the geoBoundaries component covering the decree coordinate to the existing location geometry for `gb:CHL:ADM3:31580391B33082267781919`. Preserve its present Rapa Nui geometry, stable ID, `framework:province:easter-island-province:56a8d02c6b29` parent, prior history and current release pins. Keep the representative point at `[-109.35103245892952,-27.130499999999998]`; it represents the existing Rapa Nui focus, not a centroid of the two remote land components. Do not create another location for Salas y Gómez: no separate Atlas entry under Salas y Gómez / Salas y Gomez / Motu Motiro Hiva was found in committed `data/geography` at the pinned baseline, and the law groups the physical island with this commune.

The exact component is approximately 403 km from Rapa Nui. Engineering should confirm that any downstream polygon/grid consumer accepts the resulting MultiPolygon and that no representative-point or region-release pin is implicitly recomputed. Do not replace the rest of the source shoreline from this evidence: the broader 2020 source/current overlap is not a boundary-accuracy score, and this issue did not reconcile all 166 source components or the remaining 2020 coastal differences.

## Preserved uncertainty

- geoBoundaries is a dated 2020 boundary source with the source/vintage and license stated above; its reported origin and geometry are not a current survey of every shoreline.
- IDE MINAGRI's official DPA archive has no stated reuse license on the cited page. It is used as an inspected reference only; restoration and exact archive hashes are provided, not redistributed bytes.
- The province parent has one child and its semantic and boundary review remains open. This work preserves it and makes no province/area/region approval.
- The issue machine block pins `part-28.json` even though its exact subject is in `part-2.json`. Both hashes and the mismatch are preserved in `geometry-results.json`, `baseline-inputs.json`, and the manifest; no ownership scope or ID was altered.
- No regional certificate, publication or historical import follows from this packet.

## Reproduction

Use Python 3.12 with the existing pin file `data/regional-review/regional-review-14a242c4cb0781a7/requirements-review.txt`; the script imports the repository's `worldatlas-evidence-geometry-v1` helper. Standard retained-source reproduction:

```sh
PYTHONPATH=scripts:scripts/evidence:/path/to/pinned-python-target python3.12 data/regional-review/rapa-nui-sala-y-gomez-20261005/verify.py
```

For the supplemental official DPA check, restore each archive from the exact URLs and verify its SHA-256 from `source/provenance.json`, extract each with `bsdtar -xf`, then run:

```sh
PYTHONPATH=scripts:scripts/evidence:/path/to/pinned-python-target python3.12 data/regional-review/rapa-nui-sala-y-gomez-20261005/verify.py --official-dpa-dir /path/to/extracted/chile-dpa-2022
```

This script reads immutable baseline Git blobs and writes only into this owned packet. It never changes Atlas geography or calls a mutation API.
