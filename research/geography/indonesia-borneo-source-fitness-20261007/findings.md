# East Kalimantan physical-gap source fitness

## Scope and result

This assessment covers the complete routing family `gap-source-batch:8875fd920e43656b5f36e704`: 45 unique component identities, roster SHA-256 `88831aad22806bf4f461197a12cb8309bf9a0139e5bd82b967a55e8255ad26ec`. The family row and roster were extracted from the pinned routing report and all 14 source chunks; the retained extraction record includes successful exact-roster and missing, duplicate, and fabricated-ID controls.

All 45 component geometries resolve exactly once in the pinned custody-v3 shards. The current Atlas reference has eight relevant admin features. An exhaustive 45×519 source-feature search (23,355 pairs) yields 51 nonempty, positive-area unbuffered polygon intersections, covering all 45 components; the remaining 23,304 pairs are empty and no component is coordinate-identical to a source feature. Separately, exact component-boundary/admin-boundary overlays confirm seven positive-length neighbors and one point-only contact (Kota Bontang). Exact source fragments, contact geometries, and each computed intersection are preserved in the run GeoJSON. No source geometry was repaired or buffered.

ESA WorldCover 2021 v200 and JRC Global Surface Water v1.5 source values were sampled for every component with all-touched pixel masks. The run output retains every component-by-raster histogram, so values can be examined without treating class counts as a land-area estimate. The WorldCover histogram has nine observed class codes. JRC occurrence and seasonality have observations for every component. These are source detections only: WorldCover classes and JRC open-water presence or non-detection do not prove dry land, physical cause, boundary authority, or positional accuracy.

The assessment includes a disposition for each of the 45 components: positive-area source feature IDs, any current admin boundary contacts, raster products with observations, and explicit unresolved values for physical cause, dry-land status, authority, and local positional accuracy. Follow-up evidence is stated per component.

The route-family source marks 21 components with numeric-closure flags and reports an existing mapped-fragment area sum of 1,078,088,489.3853252 m². The IDs and value are retained as inherited source-relative route outputs, not fresh land measurements; this work does not recompute their land areas or assign a cause. The boundary classification identifies Kota Bontang as the sole point-only contact.

## Source fitness and limits

- geoBoundaries is suitable here for a reproducible, source-relative geometric correspondence check. The retained 2020 derivative declares CC BY 4.0 with geoBoundaries and individual-source attribution; its underlying Indonesia ADM2 source metadata records CC BY 3.0 IGO and OCHA/HDX. This does not establish current Indonesian legal authority, effective dates, or local accuracy.
- ESA WorldCover 2021 v200 is suitable for a broad 10 m land-cover context screen. ESA reports 76.7% global overall accuracy for that product, which is not a local East Kalimantan estimate. The data page specifies CC BY 4.0 and required attribution.
- JRC Global Surface Water occurrence is a water-detection signal derived from Landsat observations; it can miss vegetated, small, obscured, or otherwise undetected water. JRC XML metadata and the current download page disagree on Seasonality temporal coverage. This packet labels it Seasonality 2024 and does not claim a full historical series.
- The retained official BIG 2022 KSP layer metadata identifies the service as a 2022 edition revised December 2022, in WKID 4326, and describes RBI, adjudication, Kemendagri, and Permendagri inputs. It also explicitly reports `ADMINISTRASI_LN` overshoot/topology errors. The service metadata has an empty `copyrightText` and does not provide an open redistribution license; no BIG polygon geometry was downloaded or used. BIG reuse and legal authority remain unresolved.
- The issue's source-only scope grants no authority to change, approve, import, or publish boundaries. All 21 numeric-closure flags and every physical or legal explanation remain unresolved.

## Reproducibility

The producer authenticates and reads the pinned custody, current-admin, source-corpus, BIG metadata, and retained raster bytes through the repository evidence helper. Its complete consumed phase is about 168 MB, within the 256 MiB limit. Earlier complete outputs are retained as superseded, immutable development runs and are not used for final metrics. The final fresh runs and their comparison receipt are retained under `vintages/run-twenty-three`, `vintages/run-twenty-four`, and `vintages/run-twenty-five`; both runs have identical bytes for all four outputs and complete `publication.json` receipts.

The retained rasters and receipts are in `sources/v1/`. Source URLs, product terms, retrieval precision, original bytes/checksums, and extraction scope are documented there. In particular, the oversized western WorldCover tile is represented by a bounded all-touched crop, not a claimed full-tile copy.
