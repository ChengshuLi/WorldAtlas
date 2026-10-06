# Argentina ADM2 interior-ring flag correction

Research date: 2026-10-06 (America/Los_Angeles). This additive packet addresses only the false `has_interior_rings` flags in the exact 214-subject #953 comparison table. It leaves the original #953 packet, its renderer, measurements, source files, Atlas IDs, parent assignments, boundaries, and all other table fields unchanged.

## Reproduction and result

The pinned #953 table contains 214 detail rows and marks every row `yes`. The retained 2020 geoBoundaries extract has the same exact 214 native `shapeID` values as the issue scope. Recounting interior rings directly from each Polygon/MultiPolygon coordinate array finds 213 subjects with no interior rings and one subject, Itatí (`61730980B76052784863315`), with five. The corrected table changes only those 213 false flags; Itatí remains `yes`. All IDs, names, parent IDs, candidate hits, overlay fields, and other categorical columns are compared row by row with the pinned input before the output is accepted.

`corrected-renderer.py` runs the scoped measurement and render twice, requires byte-identical outputs, and writes a corrected table, individual ring measurements, positive/negative controls, a regression control, a two-run receipt, and a concise reproduction report. The regression control imports and executes the exact pinned #953 `category_row` function: CSV string `"0"` becomes `yes` under the old truthiness test, while the new strict non-negative integer parser yields `no`. The new renderer rejects malformed, signed, fractional, non-finite, whitespace-padded, and non-canonical counts.

Run from the repository root with Python 3:

```sh
python3 data/regional-review/argentina-ring-classification-953-20261006/corrected-renderer.py \
  --scope data/regional-review/argentina-ring-classification-953-20261006/scope.json \
  --source data/regional-review/argentina-adm2-source-revalidation-443/source/geoBoundaries-2020-scoped-214.geojson \
  --table data/regional-review/argentina-adm2-source-revalidation-443/findings/scoped-2020-to-current-georef-overlay.csv \
  --baseline-renderer data/regional-review/argentina-adm2-source-revalidation-443/categorize-tabular-findings.py \
  --out-dir data/regional-review/argentina-ring-classification-953-20261006/output
```

The original renderer, comparison table, scoped source, and spatial measurement code match the issue's four whole-file SHA-256 pins at baseline commit `4877ef4e99528615daf657a376b7605d1657f817`. The scoped geometry was retrieved and retained in the parent #443 packet on 2026-10-05 from geoBoundaries commit `9469f09`; its metadata describes a 2020 ADM2/departments vintage, names Instituto Geográfico Nacional and UNHCR/OCHA ROLAC as source agencies, and declares CC BY 3.0 IGO. The retained exact extract and source metadata are pinned as baseline files in this packet's evidence manifest. The source packet reports that the full geometry feature total differs by one from the metadata's national ADM2 count; this remains unresolved and the 214-subject extract cannot establish national completeness.

The neighboring current Georef collection retained by #443 is an official statistical/normalization comparison source with a different vintage and mixed `Departamento`, `Partido`, and `Comuna` granularity. It is not used to count source rings or validate legal boundaries. The original overlay and current-source comparison fields are carried through unchanged. Neither ring presence nor the overlay establishes the territorial or physical meaning of a hole, current legal boundaries, island identity, regional completeness, or import readiness.

## Evidence limits and handoff

This fixes the categorical renderer output for the retained source vintage only. It does not reinterpret any parent relationship or recommend a geographic correction. The prior source packet's unresolved current-source, legal-boundary, national count, and neighboring-unit questions remain open in their existing records. Do not replace or repin the original #953 packet with this additive correction.
