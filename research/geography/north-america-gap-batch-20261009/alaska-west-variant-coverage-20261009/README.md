# Aleutians West retained-source variant coverage

This source-only evidence adds the eight first-time coverage measurements authorized by the amended #1630 work item. It uses the four exact candidates from the merged #1653 handoff and the already-retained full and simplified USA ADM2 variants from release 9469f09.

The first admitted attempt stopped at the shared evidence writer's owned-path check before any spatial comparison. Its failed operating receipt is retained under `execution/coverage-run-20261010-01-operating-receipt.json`; the successful fresh run uses the issue-owned batch namespace.

The unchanged `intersections()` overlay method is used for each candidate/source pair. The literal coverage rule is `status=measured`, `candidate_covered_exactly=true`, `candidate_uncovered_area_projected_m2_exact=0`, and `candidate_coverage_ratio=1`. Per-candidate variant agreement compares measured coverage outputs, including overlap and exact projected areas. It requires no whole-source or clipped-geometry equality.

| Component | Full result | Simplified result | Coverage outputs agree | Literal candidate agreement |
|---|---|---|---:|---:|
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | measured / True | measured / True | True | True |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | measured / True | measured / True | True | True |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | measured / True | measured / True | True | True |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | measured / True | measured / True | True | True |

### Per-variant numeric results

Each value below is bound to the exact scalar in the generated result JSON. Table values display 12 decimal places; exact source numbers remain in the JSON.

| Component | Variant | Measurement | Value | Unit |
|---|---|---|---:|---|
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | full | Projected intersection area | 1220.092140461318 | m² |
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | full | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | full | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | simplified | Projected intersection area | 1220.092140461318 | m² |
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | simplified | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | simplified | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | full | Projected intersection area | 60037.529989798139 | m² |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | full | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | full | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | simplified | Projected intersection area | 60037.529989798139 | m² |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | simplified | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | simplified | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | full | Projected intersection area | 16972.202821057290 | m² |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | full | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | full | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | simplified | Projected intersection area | 16972.202821057290 | m² |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | simplified | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | simplified | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | full | Projected intersection area | 74863.103868637962 | m² |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | full | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | full | Coverage ratio | 1.000000000000 | ratio |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | simplified | Projected intersection area | 74863.103868637962 | m² |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | simplified | Uncovered candidate area | 0.000000000000 | m² |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | simplified | Coverage ratio | 1.000000000000 | ratio |

Summary: 8 overlays across 4 candidates; full coverage premises pass for 4; simplified coverage premises pass for 4; coverage outputs agree for 4; candidate-level source agreement passes for 4; all three literal premises fit for 4.

This result changes no source, geography, physical classification, native relation, roster, conservation, production record or approval. See `vintages/coverage-run-20261010-02/source-variant-coverage.json` and its `publication.json` for the complete exact values and execution pins.
