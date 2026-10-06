# New Caledonia official province source review

Research packet for [issue #911](https://github.com/ChengshuLi/WorldAtlas/issues/911). It covers exactly `NCL-559` (Nord), `NCL-1259` (Sud) and `NCL-1258` (Îles Loyauté), pinned to baseline `1f971fef3ed24f4ddc3e3c41caac00db567caea5`.

## Finding

The official DITTT BDADMIN-NC geodatabase contains a valid, detailed `PROVINCES` layer with exactly the three named subjects. Each feature is a valid multipolygon. Its companion `COMMUNES` layer has 33 names matching the current legal list. The product documents a 1:10,000 reference scale and says administrative limits are positioned from applicable regulations.

The measured official geometry is very close to a diagnostic MakeValid clone of the preserved invalid GeoReP response, but differs substantially from the Atlas's Natural Earth fallback. This supports an engineering proposal to use the official layer as the candidate boundary source. It does not certify line-level legal accuracy, coastline completeness or topological relationships.

The source archive is **not retained here**. Its ArcGIS/catalogue metadata says Open License 2.0, while the same archive contains a 2020 read-me specifying CC BY-NC-SA 4.0 and a 2017 non-commercial CGU; DITTT's current page also links a different CC license. Treat the source as `restoration-only` until DITTT confirms the release-specific terms and permission to distribute derived geometry. The exact URL, byte size and SHA-256 needed to restore it are in [source-acquisition.json](source-acquisition.json).

## Subject comparison

The equal-area overlay below uses the same recorded method for each pair. It compares the official source with the pinned Atlas fallback and with a disposable MakeValid diagnostic clone of the preserved GeoReP source. The latter is never saved over the original or treated as a boundary correction.

| Subject | Official source parts | Official vs Natural Earth Jaccard | Symmetric difference (km²) | Official vs GeoReP diagnostic Jaccard | Symmetric difference (km²) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nord (`NCL-559`) | 822 | 0.917411 | 815.686 | 0.999951 | 0.465 |
| Sud (`NCL-1259`) | 666 | 0.911026 | 665.088 | 0.999755 | 1.714 |
| Îles Loyauté (`NCL-1258`) | 386 | 0.819125 | 394.075 | 1.000000 | 0.000038 |

These are diagnostic set-overlap screens in a local WGS84 Lambert azimuthal equal-area projection. The source vertices were transformed without densification; the result does not resolve which side of the Natural Earth discrepancy is legally correct. `source-area-results.json` separately records WGS84 ellipsoidal land areas from the shared WorldAtlas geography helper; those are not area totals from the source database's `Shape_Area` attribute.

## Administrative and parent scope

Organic Law 99-209 Article 1 lists the three provinces and their commune membership and says Poya is split between Nord and Sud by decree. The 1989 Poya decree is the referenced legal instrument. The 2025 census decree independently reports 16 communes plus Poya's northern part for Nord, 13 plus Poya's southern part for Sud, three for Îles Loyauté and 33 total. These establish tier/membership context, not coordinates.

In the pinned hierarchy, all three locations point to their matching province nodes, each beneath `framework:area:new-caledonia:42bf5323d811`. Those nodes still have open semantic/boundary review. This packet does not certify the New Caledonia area, Southern Melanesian Islands, Southwestern Pacific region or any release.

## Engineering handoff

1. Ask DITTT to resolve the BDADMIN-NC release license conflict and confirm that its 2022 `PROVINCES` layer may be retained and used in a distributable Atlas.
2. If authorized, assess this exact layer as the source for the three existing IDs, preserving the old Natural Earth source and GeoReP originals. Do not silently run MakeValid on, overwrite, or relabel the GeoReP bytes.
3. Before any implementation or release decision, inspect province-to-province and province-to-commune seams, the 1989 Poya decree's line, offshore/islet coverage, and the intended product scale. The DITTT CGU does not promise strict topological structure or systematic completeness.

## Reproduction

The archive must be obtained under terms confirmed by the user/reviewer; it is not downloaded automatically by the scripts.

```sh
PYTHONPATH=/path/to/fiona-wheel python3 data/regional-review/new-caledonia-valid-province-source-20261005/reproduce.py \
  --repo . --archive /path/to/authorized/BDADMINNC.zip \
  --area-export-dir /tmp/ncl-area-exports \
  --output data/regional-review/new-caledonia-valid-province-source-20261005/comparison-results.json

/path/to/python3.12 data/regional-review/new-caledonia-valid-province-source-20261005/measure-geodesic-area.py \
  --exports /tmp/ncl-area-exports \
  --comparison data/regional-review/new-caledonia-valid-province-source-20261005/comparison-results.json \
  --output data/regional-review/new-caledonia-valid-province-source-20261005/source-area-results.json

node scripts/evidence-quality.mjs data/regional-review/new-caledonia-valid-province-source-20261005/evidence-quality.json .
```

The first command verifies the archive byte count/hash and ZIP CRC, source layer names, exact 3-feature/33-commune scope, all feature identities, geometries and comparison controls. The second verifies the hashes of local temporary GeoJSON exports and uses the versioned WorldAtlas ellipsoidal-area helper. Use Fiona with its OpenFileGDB driver and Shapely 2; record the versions used when reproducing.
