# Saravan–Panjgur execution-authentication erratum

Issue #1341 adds an authenticated reproduction boundary to the existing source-only assessment for exactly these subjects:

- `gb:IRN:ADM2:26516999B17111396986996` (Saravan)
- `gb:PAK:ADM2:60131773B78019453337506` (Panjgur)

The earlier measurements and crosswalk are not alleged to be wrong. The defect was that the archived comparison executed `reproduce.py` from the materialized checkout, while reporting only a Git commit and source-file hashes. A changed assembly function could therefore change both overlap ratios without changing those receipts. This erratum preserves the earlier packet and adds a separate, additive execution record. It does not change geometry, IDs, parent records, source files, release pins, production data, or the prior source disposition.

## How the successor authenticates execution

`compare.py` and `shared_edge.py` read input and project-code bytes from their declared immutable Git commits through the current shared `scripts/evidence/immutable.py` helper. The helper itself is captured and verified as commit `696d1eadd9afdff8267ef3166c4c6b8b849011f5`, SHA-256 `a3667cecd88b2862e61a3ce72778e179535d92fbf19b5cd7c5b112722926da46`. The issue originally pins the old reconstruction closure by its exact file hashes. Those same bytes are all present at ancestor commit `39eff6e40063a4a22bfc4e6655487404c35c54c4`, so that merge commit supplies the executable `(path, commit, bytes, SHA-256)` bindings for `reproduce.py`, `scripts/evidence/immutable.py`, `scripts/evidence/geometry.py`, and `scripts/ellipsoidal_area.py`. The older producer commit `2ed630f9aef42b54a75f12fdae1f0c8caad9b1e3` remains in the preserved archived result; it is not an ancestor of current main, so the hosted evidence manifest does not falsely use it as a baseline. The prior assessment's `source-claims.json`, frozen whole-geometry output and evidence manifest also bind to commit `39eff6e40063a4a22bfc4e6655487404c35c54c4`. All 25 issue-declared hashes are unchanged. A separate descriptor records the current shared helper without replacing the original helper pin.

The shared helper rejects an absent or altered captured file before either output writer is created. `adversarial_controls.py` exercises the actual comparison entry point after substituting complete altered in-memory Git-blob bytes for (a) the directly called OSM assembly module and (b) the helper-imported geometry module, with all expected hashes fixed. Both are rejected before any output. The originals and historical refs were not edited. The output records exact original and altered whole-file hashes. This adapter emulates altered bytes reaching the reader; it does not modify a materialized checkout or claim a general Python sandbox.

Each scientific CLI publishes an exclusive, fresh named vintage through the shared `NewVintage` writer. All output bytes and captured pins are checked before writes, ordinary files use exclusive creation, and `publication.json` is hard-linked last as the complete-run receipt. The separate writer controls exercise a preexisting sentinel, a broken symlink, an ancestor symlink, a traversal destination and an injected second-file write failure. The failure left its first partial file without a success receipt; that private control output was then removed. Control outcomes are retained under `vintages/`.

## Source meaning and preserved findings

The complete retained geoBoundaries country files contain 432 Iran ADM2 features and 126 Pakistan ADM2 features. Each target is the only exact `shapeName` match in its complete country roster. The target `shapeID`s match the two Atlas IDs, but both target `shapeISO` values are empty and the files carry no OSM relation identifier. The provider does not publish a geoBoundaries-to-OSM crosswalk; the cross-provider link remains an authored research mapping supported by several retained attributes, not an official adjudication.

The source metadata identifies the Iran file as 2017 ADM2 / `Shahrestan`, sourced to “OpenStreetMap, Wambacher”; it labels the underlying boundary ODbL 1.0. It identifies Pakistan as 2019 ADM2 / `Districts`, sourced to “geoBoundaries, Wikipedia”; metadata says “Public Domain” with an empty `licenseDetail`. Both records state the same 2023-01-19 source-data update field and 2023-12-12 build date. Those are update/build dates, not boundary observation dates or legal effective dates. The underlying Wikipedia work and rights remain unresolved. The product notice requires geoBoundaries attribution and source citation and describes product derivative code/works as CC BY 4.0. This packet makes no legal compatibility finding.

The retained OSM county snapshots identify relation 6555069 as Saravan County (`admin_level=5`, Wikidata Q1279055) and relation 3229274 as Panjgur District (`admin_level=6`, Wikidata Q2428944). Their receipts record retrieval on 2026-10-05 at 15:24:42.157753 UTC and 15:11:43.278941 UTC, respectively, and retain whole-response hashes. Relation edit dates and individual node/way edit ranges are reported separately in the comparison result. The complete OSM snapshots and the two way-membership responses are preserved at their original hashes under the existing #971 packets. OSM records carry ODbL 1.0 and require OpenStreetMap and contributors attribution; a derivative database/share-alike plan remains an engineering/publisher responsibility.

The Atlas parent links in the pinned historical part files resolve to Sistan and Baluchestan and Balochistan in the pinned hierarchy. The retained #1115 source-claims record reports OSM parent identity as Sistan and Baluchestan Province (relation 537693 / Wikidata Q939575) for Saravan, and Makran Division (16347101 / Q3308229) followed by Balochistan (357968 / Q163239) for Panjgur. This erratum checks that the captured county relation IDs and Wikidata tags agree with that prior crosswalk and that its parent IDs agree with the declared native chains. The underlying full parent relation responses were not re-fetched or newly retained here, so those parent names/IDs remain a prior-evidence input rather than a new independent raw-source extraction.

The two complete source overlays reproduce the prior ratios exactly: Saravan IoU `0.602997293451444`, geoBoundaries-covered-by-OSM `0.6814807804175339`, OSM-covered-by-geoBoundaries `0.8396380196104828`; Panjgur IoU `0.8517888797887251`, `0.908809654658024`, and `0.9313940656838654`. These are complete-footprint disagreement diagnostics, not evidence that either source footprint is accurate or should replace the other. The method transforms source vertices from EPSG:4326 longitude/latitude into EPSG:6933 with pyproj `always_xy`, then performs planar area/intersection/union operations. It does not densify edges or include a positional-accuracy model.

The shared-edge run compares complete captured county responses and the retained national-relation membership responses. Ways 239441239 (940 ordered nodes) and 239453665 (641 ordered nodes) are equal as full way objects in both county responses, have matching node sequences and coordinates, appear as outer ways in both county relations, and appear as outer ways in national relations 304938 and 307573. This establishes topology in these dated retrieved OSM records. It does not establish legal sovereignty, government approval, a historical boundary, land/water class, positional accuracy, or the source edition behind any OSM tag.

## Controls and reproduction

Two complete runs of each scientific entry point are stored in unique vintages. The payload result, positive-control and negative-control files are byte-identical across each pair; path-specific completion receipts name their distinct vintages. The exact input and executed-code closure, Python/NumPy/Shapely/GEOS/pyproj/PROJ versions, output hashes and controls are in the JSON products and `evidence-quality.json`.

From repository root, use the pinned Python 3.12.14 environment with NumPy, Shapely, GEOS and pyproj versions recorded in the outputs. Replace the example values with fresh lowercase vintage names:

```sh
python3 research/geography/saravan-panjgur-source-execution-1121-erratum/compare.py --vintage comparison-replay-a
python3 research/geography/saravan-panjgur-source-execution-1121-erratum/shared_edge.py --vintage shared-edge-replay-a
python3 research/geography/saravan-panjgur-source-execution-1121-erratum/adversarial_controls.py
python3 research/geography/saravan-panjgur-source-execution-1121-erratum/writer_controls.py
python3 research/geography/saravan-panjgur-source-execution-1121-erratum/reproducibility.py
node scripts/evidence-quality.mjs research/geography/saravan-panjgur-source-execution-1121-erratum/evidence-quality.json
```

The comparison also rejects an unknown native ID, a changed retained parent relation ID, and an invalid self-intersecting measurement polygon. The shared-edge runner rejects an unknown required way, a removed national outer-member contact, and a changed shared-node coordinate. Controls demonstrate the implemented input/measurement checks; they do not validate authority, source licensing, or geographic accuracy.

## Open findings and handoff

- The PAK underlying Wikipedia work/license and compatibility of the complete geoBoundaries/OSM source combination are unresolved. Keep the provider notices, product hashes, LFS pointers and retrieval receipts intact. Any future rights decision belongs to the publisher/legal review.
- Neither source set establishes official/legal/historical identity, an effective boundary date, positional precision, sovereignty or physical-water classification. The failed retained State Department LSIB WFS response still supplies no independent boundary geometry.
- The cross-provider mapping and OSM parent chain remain sourced research candidates. The prior raw parent-response limitation is stated above; do not promote retained prior claims into new raw-source proof.
- #991 owns its independent integration and source obligations; #971 retains the proposed seam work; closed #1115 remains its original source-only disposition. This execution-authentication repair changes none of those owners or gates.
- No correction, integration, core geography change, import, approval or publication is requested by this packet. Ordinary merged work does not create a publication request on #714.
