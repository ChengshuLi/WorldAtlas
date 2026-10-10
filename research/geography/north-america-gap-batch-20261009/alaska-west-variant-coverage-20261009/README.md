# Aleutians West retained-source variant coverage

This source-only evidence adds the eight first-time coverage measurements authorized by the amended #1630 work item. It uses the four exact candidates from the merged #1653 handoff and the already-retained full and simplified USA ADM2 variants from release 9469f09.

The first admitted attempt stopped at the shared evidence writer's owned-path check before any spatial comparison. Its failed operating receipt is retained under `execution/coverage-run-20261010-01-operating-receipt.json`; the successful fresh run uses the issue-owned batch namespace.

The unchanged `intersections()` overlay method is used for each candidate/source pair. The literal coverage rule is `status=measured`, `candidate_covered_exactly=true`, `candidate_uncovered_area_projected_m2_exact=0`, and `candidate_coverage_ratio=1`. Per-candidate variant agreement compares measured coverage outputs, including overlap and exact projected areas. It requires no whole-source or clipped-geometry equality.

| Component | Full: status / covered / uncovered m² / ratio | Simplified: status / covered / uncovered m² / ratio | Coverage outputs agree | Literal candidate agreement |
|---|---|---|---:|---:|
| `physical-component:18bde5cda8660806ef3cf9f851a006be827c80bc6ebf9cc5a92abdfc3f2249d0` | measured / True / 0.0 / 1.0 | measured / True / 0.0 / 1.0 | True | True |
| `physical-component:6941aa6f88a5581bf95d63718e554f6f37fb1d9fa70db7636b3b3f2914d49f6a` | measured / True / 0.0 / 1.0 | measured / True / 0.0 / 1.0 | True | True |
| `physical-component:ac95cb3b778a830c88ed69150c06716eed6014ab0c067331c3196fb79c274df4` | measured / True / 0.0 / 1.0 | measured / True / 0.0 / 1.0 | True | True |
| `physical-component:baf74325795539a3fcc7d27feb2a04c376a0e1d3c3287eba435ea85b99607be6` | measured / True / 0.0 / 1.0 | measured / True / 0.0 / 1.0 | True | True |

Summary: 8 overlays across 4 candidates; full coverage premises pass for 4; simplified coverage premises pass for 4; coverage outputs agree for 4; candidate-level source agreement passes for 4; all three literal premises fit for 4.

This result changes no source, geography, physical classification, native relation, roster, conservation, production record or approval. See `vintages/coverage-run-20261010-02/source-variant-coverage.json` and its `publication.json` for the complete exact values and execution pins.
