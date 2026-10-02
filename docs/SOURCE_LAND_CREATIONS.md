# Source-backed missing-land additions

Genuine omitted land has no predecessor location. Keep it separate from a source
label correction, footprint replacement, or historical settlement claim. This
contract adds no historical facts and does not certify regional interiors.

Prepare a candidate geography in a separate directory. Preserve all existing
features exactly; add complete adjacent-tier parents from the reviewed geographic
scope. Each proposed location needs one JSON creation proof with `location_id`,
`parent_chain` (province through continent), `source`, and `identity_review`.

`source` contains a relative `path` to an archived GeoJSON Feature or FeatureCollection,
its exact `sha256`, feature `identity`, HTTP(S) `url`, `license`, `attribution`, and
half-open `supported_from` / `supported_to` with no year zero. Preserve the actual
coastline source, vintage and derivation separately from identity gazetteers. OSM
geometry requires OpenStreetMap contributor attribution and ODbL obligations;
comparison-only datasets are not automatically licensed replacement geometry.

`identity_review` has `status: "distinct-new-territory"`, an `evidence_url` and
`rationale`. List `same_name_existing_ids` when the name occurs in the predecessor
inventory, explaining distinct territories rather than disguising a rename.
Existing source identities and overlapping or duplicate land are rejected.

```sh
node scripts/stage-land-creations.mjs \
  --before=/path/to/predecessor-geography \
  --after=/path/to/candidate-geography \
  --proofs=/path/to/creation-proofs.json \
  --output=/path/to/new-evidence-directory
```

The command changes neither input. It independently checks source bytes, exact
geometry, valid closed longitude/latitude polygons, WGS84 land area, antimeridian
normalization, overlap and complete parent chains. Its fresh output contains the
archived source bytes, hierarchy and geometry migration manifest/receipt.
Creation relationships have `before_ids: []`, explicit `source-backed-create`
kind, and `history_transfer: false`. Geographic release preparation produces
one sourced `create` crosswalk with a null old ID per new location. Existing
merge/split/replace and archived-release contracts remain unchanged.

Use the complete ordered geometry/metadata proof chain and latest registered
identity manifests when preparing the next release. A source label repair must
have its own retained-ID metadata receipt; this pure-addition stager refuses to
rename, remove or move an existing feature.

For missing land without new factual research, `prepare-ownership-incremental.py`
and `prepare-reference-incremental.py` accept `--unknown-changed`. These modes
preserve exact unchanged claims/dictionaries, archive inapplicable changed
footprint records, and leave changed/new attributes unknown. Ownership skips
spatial derivation; environmental references skip native-raster recomputation.
Neither mode transfers direct historical evidence or broadens source intervals.
Their receipts retain prior lineage archives across successive generations.
Derivation remains available separately when supported sources warrant it.

The existing `install-reviewed-geography.mjs` checks source creation proofs,
prepared product pins and every represented canonical-grid location. Its exact
predecessor file manifest rejects stale or unexpected bytes, and its journal
retains rollback originals. Installation requires explicit validated pins and
complete staged products; this feature does not install any real geography.

A footprint change needs one new cached grid, source-gap/representation and
distortion checks, revised member-derived macro envelopes, evidence applicability
review, matched static/hosted assets, and one coordinated publisher. No arbitrary
cell reassignment is allowed. Tiny missing islands may fail the current canonical
resolution; keep that blocker explicit rather than enlarging or moving them.
The 256 MiB package and individual-asset gates still apply. Actual source
integration/publication belongs to the dependent issue, not this contract.
