# West Siberian source-versus-Atlas component-count erratum

Research snapshot: 2026-10-06 (America/Los_Angeles). Issue #1315; exact review scope is the 199 native subjects in the captured issue contract. The immutable Atlas evaluation baseline is `42937b066c28eab0c5a53f94c0f5aee7b3d5aae3`.

## Finding

The old #1089 `assess-members.mjs` stored the Atlas part geometry's type and component count under unqualified `geometry_type` / `component_count` fields. Its rationale then described those numbers as being in the pinned original source. #1098 `reproduce-followup.py` copied those Atlas-derived fields into `source_geometry_type` / `source_component_count`; its README consequently called nine numbers “2017 source component counts.” This is a provenance-label error: the old scripts are reproducible, but their field names do not describe the geometry vintage they actually count.

This erratum separately reports `original_source_geometry_type` and `original_source_component_count` from the retained 2017-source feature, and `atlas_geometry_type` and `atlas_component_count` from the Atlas feature at the exact evaluation commit. The 199-member roster matches the captured #1315 work contract exactly. Each Atlas ID maps one-to-one through the prior assessment's source ID to an original `shapeID`; all 199 source and Atlas names match. The reproducer also checks the two actual Atlas geography-part files recorded in the pinned lineage inventory and confirms that the old assessment fields are Atlas-derived. The output retains parent ID/name as Atlas context; it is not an independent legal-parent crosswalk.

| Subject | Source type / parts | Atlas type / parts | In #1092 45-row handoff |
| --- | --- | --- | --- |
| `gb:RUS:ADM2:50074027B1024572337800` — городской округ Бийск | MultiPolygon / 3 | MultiPolygon / 2 | Yes |
| `gb:RUS:ADM2:50074027B10379539839705` — Tazovsky Rayon | MultiPolygon / 32 | MultiPolygon / 12 | Yes |
| `gb:RUS:ADM2:50074027B19808785107388` — Berdsk municipality | MultiPolygon / 3 | Polygon / 1 | No |
| `gb:RUS:ADM2:50074027B30864735873510` — Nadymsky Rayon | MultiPolygon / 8 | MultiPolygon / 6 | Yes |
| `gb:RUS:ADM2:50074027B53792659884597` — городской округ Омск | MultiPolygon / 5 | MultiPolygon / 3 | Yes |
| `gb:RUS:ADM2:50074027B56233113775442` — Priuralsky Rayon | MultiPolygon / 9 | MultiPolygon / 6 | Yes |
| `gb:RUS:ADM2:50074027B57421544908828` — Yamalsky Rayon | MultiPolygon / 107 | MultiPolygon / 45 | Yes |
| `gb:RUS:ADM2:50074027B58811812536316` — Cherepanovsky District | MultiPolygon / 2 | Polygon / 1 | No |

Of all 199 native subjects, 191 have matching geometry type and coordinate-array component count and eight differ. In the related #1092 handoff, 34 of 45 subjects are native administrative features: 28 match and six differ. The other 11 are ecoregion fragments, not whole native administrative units, and are excluded from this comparison. Berdsk and Cherepanovsky are the two additional differences outside the 45-row handoff. Their source multipart geometry failed to enter its multipart-review subset because the selection used Atlas-derived counts; this is a diagnostic omission only. It does not demonstrate legally missing area or require geometry restoration.

## Sources, vintage, and limits

The original source is geoBoundaries Open Data RUS ADM2, represented boundary year 2017; its metadata records a 2023-03-03 source update, 2023-12-12 build, ODbL 1.0, and OpenStreetMap/Wambacher attribution. The exact official Git LFS pointer was fetched at upstream commit `9469f09592ced973a3448cf66b6100b741b64c0d` via the GitHub connector and is retained at `sources/geoboundaries-rus-adm2-2017-lfs-pointer.txt`: raw object SHA-256 `74012237384e53061aa63b6e20b9be24f94facfe615b52bbe72e62a81fa68ff0`, 120,489,189 bytes. Restore from:

`https://media.githubusercontent.com/media/wmgeolab/geoBoundaries/9469f09592ced973a3448cf66b6100b741b64c0d/releaseData/gbOpen/RUS/ADM2/geoBoundaries-RUS-ADM2.geojson`

The complete national object is not retained in this campaign. The lawful, exact 203-feature scoped original extract remains in its predecessor packet at `data/regional-review/regional-review-626fdf640aab94e2/sources/geoboundaries-rus-adm2-2017-scoped-original-features.geojson`, SHA-256 `7eb4cba61f0d17bfacb634c08aff3ec4873ece62734d518b51614bf061a5a129`; it contains 199 direct native subjects and four source districts associated with the separately typed ecological portions. The retained Atlas scoped extract is separately pinned at `data/regional-review/regional-review-626fdf640aab94e2/sources/current-scoped-features.geojson`, SHA-256 `44aa8bed8c6d3f6b7f4c553007efbaa82d39ff384790e95c06d1e3615ad4f070`. Predecessor assessment, lineage, and follow-up hashes are bound in the evidence manifest; their bytes and producer code are read from the immutable baseline, not overwritten or copied.

The predecessor source register records retrieval of the national object on 2026-10-05 22:51:01 PDT and its raw hash above. That register reports 2,327 features in the full object although the source metadata declares 2,328 units. This campaign preserves that reported discrepancy and the exact restoration recipe, but does not download the large object to re-count it. The source extract proves only the selected 199 source rows and four supporting districts; it cannot prove the national archive is complete.

GeoJSON component count here means one for a Polygon or the number of top-level coordinate-array members for a MultiPolygon. It does not count legally separate units, verify islands, establish polygon validity, or show which pieces are water or land. No current statute annex or current official polygon source was obtained for all subjects. Neither vintage is asserted to be current, authoritative, complete, or legally correct. The 2017/source-versus-Atlas differences do not establish which representation is right, that area is missing, or that boundaries should be changed. No geometry, ID, source pin, or predecessor finding is changed.

## Reproduction and controls

From the repository root, with Node 24, the script reads the captured issue body and immutable baseline files with `git show`, performs the one-to-one source join and independent geometry counts, verifies the old mislabeled fields, and writes only to a new output path using exclusive-create mode:

```sh
node research/geography/west-siberia-source-atlas-components-2026/reproduce-components.mjs research/geography/west-siberia-source-atlas-components-2026/findings/NEW-RUN.json
```

The final full-input executions are `findings/run-one.json` and `findings/run-two.json`. Their raw bytes and hashes are identical; the manifest records the digest. The script includes a known-positive mismatch, missing- and duplicate-subject rejection, a wrong-count mutation that changes the mismatch total, and refuses to replace an existing output. Result rows are stored one per line so the exact-199 ledger stays reviewable within the repository's normal PR review budget.

## Engineering handoff

Corrected diagnostic labels are available for #1092's current-source/legal research to use within its existing owned scope. In particular, its 34 native rows should not use `source_component_count` to mean current-source or original-source counts: those existing values reproduce the Atlas counts described above. The two omitted native mismatches are explicit candidate subjects for further *source-backed* review if that worker's scope and evidence permit. Share this finding with the #1092 owner; do not edit their packet, change Atlas geometry, expand their issue scope, or treat the old 45 rows as legal completeness evidence. Any current-law/island component determination requires separately retrieved authoritative boundary evidence.
