# Mauritania–Senegal two-component source-fit assessment

## Scope and disposition

This packet assesses complete family `gap-source-batch:4c735331be01be152eda6db6` (operational batch `gap-operational-batch:ade3f99f475181e3f9ac2694`), the rank-2 eligible family of 711, containing both subjects:

- `physical-component:0083c01969242c7ff7bd7169be50cb52f58156add0cd4229dccb556a3f0469a6`
- `physical-component:99cae6efa6335e68990e353f15940b4bda47276e159af4214919b932b232df4f`

The prior routing ranks are source locator 176, measured impact 94,888, and coordination complexity 52,034. The first-ranked family has three numeric-closure members, so this is the highest-ranked complete family with no numeric-closure prerequisite. Both contact references remain in scope: Mauritania `gb:MRT:ADM2:47542326B95460333313215` (Keur Macene; recorded represented-year claim 2020) and Senegal `gb:SEN:ADM2:50182788B94177495754038` (Dagana; recorded represented-year claim 2019).

The pinned, original-consumed simplified ADM2 products were fetched at geoBoundaries commit `9469f09592ced973a3448cf66b6100b741b64c0d`. They match the retained source-corpus original bytes exactly: MRT is 124,489 bytes / SHA-256 `1902199c8a95554f6fc671b72445584e6b511a79223e0cd30399de2da6fb69da` (57 valid, uniquely identified features); SEN is 424,564 bytes / SHA-256 `cb9aa64a7c8d1302527dd97e85acccafefe28b63e2a3f550c2218ed9a22ba335` (45 valid, uniquely identified features). Same-commit full, non-simplified products are retained separately and excluded from this calculation.

## Calculation and result

The entrypoint verifies whole source hashes and counts, every feature's stable `shapeID`, polygonal geometry validity, both candidate physical IDs, the complete two-member roster, and both candidate feature bindings against the immutable physical component payloads. It compares both candidate polygons against every feature in each complete simplified product in unmodified GeoJSON longitude/latitude coordinates, retaining each bounding-box candidate as well as actual topological intersections. No geometry repair, projection, normalization, buffer, or edit is made.

- Component `0083…469a6` is topologically covered by MRT Keur Macene. Three source-feature bounding boxes overlap its bounds: that MRT feature and two Senegal features. Neither Senegal feature has a topological intersection with it.
- Component `99ca…2df4f` is topologically covered by MRT Keur Macene and also intersects SEN Dagana. It is not covered by Dagana. The reported coordinate-space intersection fraction is 0.03782.

These rings are near-degenerate: their coordinate-space areas are about `5.63e-19` and `1.27e-19` square degrees, while the inherited source-relative fragment area diagnostics are about `5.97e-9` and `1.35e-9` m². The second component's computed MRT intersection fraction is slightly greater than 1, an explicit numerical-instability signal. Fractions and square-degree intersection areas are diagnostic only. The topological source-fit observations do not establish the polygons' physical surface.

**Decision:** retain both members and their original geometry unchanged, with physical surface and source authority unverified. This screen confirms fit with the named administrative source features but does not independently support the inherited mapped-land versus mapped-inland-water distinction, establish effective source dates, or justify a physical repair. The exact missing fact is a date-matched, independently authoritative land-versus-inland-water observation with spatial resolution and positional accuracy stated well enough to resolve each component. Without that evidence, no safe classification or repair recommendation can be made.

## Provenance and limits

The administrative products are GeoJSON longitude/latitude coordinate data (WGS 84 / RFC 7946 axis order); the calculation uses angular coordinates as supplied. Source metadata records represented-year claims of 2020 (MRT) and 2019 (SEN), product build date 2023-12-12, and CC BY 3.0 IGO. Attribution recorded for MRT is World Food Programme and OCHA ROWCA; for SEN it is Government of Senegal and OCHA ROWCA. These records and retrieval time are not proof of boundary effective dates or legal authority. The component source records identify GSHHG 2.3.7 (2017-06-15 release), but provide no date-matched independent dry-land/water determination for these features.

Two independent fresh output directories produced byte-identical final result JSON (SHA-256 `140462711cd8112fcc6a61b03bb27a730bc3063fcf9bd162d84d71c6f3238f42`). Controls accepted the complete pinned input and rejected an incomplete family roster and a one-byte source alteration through the same calculation entrypoint. The earlier `first`/`second` receipts predate the bbox-candidate output; `final-a`/`final-b` predate runtime enforcement. `final-c`/`final-d` are the authoritative pinned-runtime reproductions.

Storage admission passed immediately before the focused materialization and again before the second reproduction and controls. The expected remaining source/output/control scratch for this work is under 20 MiB; no second global graph or GIS corpus was generated.

## Reproduction

From the repository root, with the pinned Python 3.12.14, Shapely 2.1.2, and GEOS 3.13.1 environment:

```sh
python3 research/geography/mauritania-senegal-gap-source-fitness-20261007/scripts/source_fit.py --repo . --output research/geography/mauritania-senegal-gap-source-fitness-20261007/reproduction/final-c/source-fit.json
python3 research/geography/mauritania-senegal-gap-source-fitness-20261007/scripts/source_fit.py --repo . --output research/geography/mauritania-senegal-gap-source-fitness-20261007/reproduction/final-d/source-fit.json
cmp research/geography/mauritania-senegal-gap-source-fitness-20261007/reproduction/final-c/source-fit.json research/geography/mauritania-senegal-gap-source-fitness-20261007/reproduction/final-d/source-fit.json
python3 research/geography/mauritania-senegal-gap-source-fitness-20261007/scripts/controls.py --output research/geography/mauritania-senegal-gap-source-fitness-20261007/reproduction/controls-validation.json
```

The shown destinations document the runs preserved here. The entrypoints require fresh destinations and deliberately refuse to overwrite them; for another local execution, choose two unused source-fit output paths and a new controls output filename.

The complete source-fit receipts, source retrieval receipt, controls, and evidence-quality manifest accompany this note. The result is a source-fit assessment only; it is not a geography approval or publication request.
