# Lydekker Figure 8.1 review line

`derive_lydekker.py` reconstructs the reviewed continuous, smoothed line from external research inputs. It does not download the source, publish records, change selections, or rebuild a map. No source PDF, source imagery, input trace or generated geographic data is stored in Git.

## Provenance and interpretation

Source: Dylan Gaffney et al., *West New Guinea*, Terra Australis 58, chapter 8, Figure 8.1, printed page 172 (PDF page 2), [ANU Press PDF](https://press-files.anu.edu.au/downloads/press/n13144/pdf/ch08.pdf), DOI 10.22459/TA58.2024.08. The original PDF SHA-256 is `4bcc38d0da4f8062ebdc49c10af8e14c640215a249417700f7254526d45b8fec`. The book states CC BY-NC-ND 4.0; assess the license separately before redistribution or derivative use.

The inset dashed segments were manually digitized from a 300-dpi crop. Calibration inferred an equator at crop y=112, 0.5 degrees per 202 pixels and 130°E at x=199. Three named islands were cross-checks. A coarse affine fit registered the ungridded overview to an archived land mask. The code combines those visible segments with overview strokes and explicitly chosen inferred bridges across missing or obscured portions. It then interpolates longitude by latitude at roughly 0.001° intervals, applies a Gaussian filter with sigma 0.08° latitude, and preserves endpoints using a smooth four-sigma taper. There is no extrapolation beyond the selected overview endpoints.

This is a schematic, approximate geographic interpretation, not a surveyed line or legal maritime boundary. The gap and arrow-crossing bridges are choices, not source-visible geometry; the calibration and fit are approximate and have no quantified accuracy. Smoothing does not add source information. Separately measured diagnostics found no physical land-center side changes on the particular pinned grid and no crossing of the archived land polygons; neither establishes independent geographic accuracy. The largest same-latitude displacement was about 3.96 km, not an uncertainty bound.

## Inputs and usage

Use Python 3 with NumPy and SciPy. The original run used NumPy 2.3.5 and SciPy 1.17.0. Export the inset observation from Neon research `atlas.geographic_line_observations`, line ID `lydekker-anu-figure81-inset-trace-v1`, as JSON with its `geometry` field, and store it outside the repository. The code checks the SHA-256 of that geometry serialized with sorted keys and compact JSON separators: `fce7c71b71666d70dae5265eb1fee7102beffdbc37837d93266e8b96c65c1c1e`. The fitted overview transform is recorded directly in the derivation code so a separate local file is not needed. The original source PDF is registered in `atlas.source_assets` under `anu-west-new-guinea-lydekker-ch08`, version `2025-4bcc38d0da4f-official`, and archived in R2 at `worldatlas/sources/anu-press/west-new-guinea/2025/official-ch08-4bcc38d0da4f.pdf`.

```sh
python scripts/raw-to-structured/lydekker/derive_lydekker.py \
  --observation /external/line-observation.json \
  --output /external/lydekker-review.geojson
python -m unittest discover -s scripts/raw-to-structured/lydekker -p 'test_*.py'
```

On the original inputs and software versions, the generated 10,703 coordinate pairs exactly match `smoothed-candidate-v2.json` (file SHA-256 `8b6fb89e0e329095a1cb6a45c1c24de431f29b93b9a238311d3fcd2cd6a8392f`), although this program emits a different GeoJSON wrapper. The original candidate and its diagnostics remain external. Floating-point results may differ across dependency versions; review such changes rather than treating file hashes as geographic accuracy claims.

The resulting smoothed geometry is registered for research in `atlas.geographic_line_observations` as `lydekker-anu-figure81-regional-smoothed-v1`; its canonical geometry SHA-256 is `0c3ada39efe778e42808a112d8cf264703b1966cf0dab1df8a002fcc0f2df94a`. Registration is not a map rebuild or acceptance of a geography partition.

## Boo adjustment used by V8

The project shifted the line smoothly west to put Boo Besar on the Oceania side. The displacement is centered at 1.17°S, extends 0.45° latitude on each side, and peaks at 0.30° longitude. Export the smoothed Neon observation with its `geometry` field, or use the matching GeoJSON from the smoothing command.

```sh
python scripts/raw-to-structured/lydekker/apply_boo_adjustment.py \
  --observation /external/lydekker-review.geojson \
  --output /external/lydekker-boo-east.geojson
```

The implementation was reconstructed from the recorded method. Its 10,703 coordinates match `lydekker-anu-figure81-regional-boo-east-v2` in Neon and V8's pinned geometry SHA-256 `87514ff08498fa2e2a27bfe2f0a1026511b3c5f01acfbaecbf1f753392c33655`. The output uses a new GeoJSON wrapper.
