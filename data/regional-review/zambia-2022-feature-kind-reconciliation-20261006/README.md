# Zambia 2022 OSG/GRID3 feature-type source review (#1048)

This bounded packet inventories all 116 source records, crosswalks each district name to the pinned geoBoundaries 2020 ADM2 native ID, and preserves the exact `FEATURE_TY` and `Area_km` values. It is source research only. It does not certify boundaries, change IDs, approve a regional branch, or authorize import/publication.

## Reproduce

From the repository root:

```sh
python3 data/regional-review/zambia-2022-feature-kind-reconciliation-20261006/reproduce.py --run-id run-one
python3 data/regional-review/zambia-2022-feature-kind-reconciliation-20261006/reproduce.py --run-id run-two
```

These commands describe the intended two-run reproduction; they are not currently runnable because the issue-required evidence manifest cannot represent one of its required pins within the active byte limits. A first source comparison did generate the 116-row `feature-type-crosswalk.csv` retained here. It found 116 unique names on both sides, a one-to-one name join, and the four literal source categories. That single investigative run is not the final required reproducibility/control proof.

The issue contract pins the geoBoundaries source GeoJSON at 35,998,492 bytes, above the evidence validator's 33,554,432-byte per-file limit. The validator requires the expected pin to match a whole-file descriptor, so an extracted roster or hash-checking script cannot satisfy the original pin. Do not omit or replace that pin to get a green check. The exact blocker and requested engineering handoff are in `manifest-blocker.json`. The OSG/GRID3 source is 31,192,016 bytes and its exact original remains in the parent #412 packet.

## Scope and method limits

`feature-type-crosswalk.csv` classifies every record by its literal source category and records the source’s province, district code, source-reported `Area_km`, and corresponding geoBoundaries ID. It distinguishes the administrative role asserted by the OSG item (“district boundaries”) from the unexplained meaning of `FEATURE_TY`. No category is normalized into a legal administrative tier.

The one value `District Tiwn` belongs to Shiwang'Andu. It differs from the 100 `District Town` strings by a likely spelling error, but no source correction history or field definition was found. The source value is preserved and the apparent typo remains a handoff, not a silent repair.

`Area_km` is preserved as a source value and explicitly unvalidated. The layer schema supplies no calculation, units, precision, projection, or geometry relationship. Its apparent unit from the field name alone is not evidence. No area is recomputed and no source values are treated as geographic measurements.

All 116 pinned reference IDs have geoBoundaries `shapeType=ADM2`; its metadata calls the units districts and reports a 2020 boundary vintage, source-data update in 2023, and 116 units. The OSG item describes a 2022 district-boundary layer and cites district narratives updated through 2017 and 2021. ZamStats' 2022 census report corroborates ten provinces and 116 districts at census date. These sources establish intended district-layer context and cohort size, not the undocumented `FEATURE_TY` semantics, post-2022 completeness, or any boundary's accuracy.

## Files

- `findings.md`: source claims, uncertainty, and engineering handoffs.
- `SOURCES.md`: original-byte pins, dates, licenses, attributions, citations, and restoration instructions.
- `source/`: fresh 2026-10-09 ArcGIS item/service/layer/resource responses; resource listing is empty.
- `feature-type-crosswalk.csv`: all 116 source rows and exact pinned reference IDs.
- `reproduce.py`: draft two-run producer. `reproduction-controls.json` records observed counts only; it explicitly does not claim negative controls or reproducibility.
- No `evidence-quality.json` is claimed. Add it only after the evidence gate can preserve and validate the issue's original full-source pin under a reviewed partitioning method.
- `claim-receipt.json`: accepted serialized reservation for GEO 1.
