# Three missing named islands — engineering candidate for #503

Adds source-defined Qeqertarsuaq (Disko), Milne Land and Inaccessible Island as distinct, provisional whole-island local territories. They are absent from all 49,589 current polygons and all 19,102 archived polygons. This package does not install geography, approve regional interiors, or import historical attributes.

Existing and retired municipal/physical identities remain intact. The four related current features and original archived Sermersooq feature are copied in `related-full-old-features.json.gz`. No existing territory is expanded. SHN-4865's original identity does not explicitly establish an entire-archipelago role; consequently Inaccessible receives a new named island ID, without copying Tristan's records. GeoNames numeric island IDs are stable identifiers; country codes never choose parents.

Disko and Milne belong to the existing Qeqertalik and Sermersooq provinces: current original OSM municipal polygons contain 100% of each whole coastline. Official municipal pages support municipality identities; their landing pages do not alone prove Milne membership. Official Tristan's named outer-island page supports Inaccessible's archipelago association and complete existing adjacent-tier parent chain. `proposal.json` records source URLs, exact source hashes, short quotations, licenses, vintage, roles and remaining limits.

Original Greenland PBF and GeoNames country ZIP bytes are already retained by merged #41 under `data/macro-improvements/macro-coverage-africa-americas/`. This package preserves the exact original Inaccessible Map API XML, 362 assembled water/municipality derivatives, inland-water masks, source-index metadata, and full related prior features. Original source data is ODbL-1.0; GeoNames identity rows are CC-BY-4.0. Official pages have unspecified reuse rights; only short factual citations are reproduced. Every retained artifact is hashed in `manifest.json`.

Dry land excludes all 350 mapped Disko inland-water features, 10 Milne features and Inaccessible's Skua Pond. Whole coast equals dry land plus mapped water; mask and dry-land areas do not overlap. Mapped-water coverage is not exhaustive hydrological coverage. Modern 2026 source support never silently supplies ancient shorelines, names, owners or other attributes. All new attributes remain unknown.

Reproduce against the exact release-3 baseline pinned in `proposal.json`, using the repository's existing Python preparation dependencies:

```sh
python3 data/macro-improvements/three-island-restoration/prepare.py --root "$PWD" --output /tmp/three-island-candidate
node data/macro-improvements/three-island-restoration/grid-check.mjs "$PWD" /tmp/three-island-candidate
node --max-old-space-size=3072 scripts/stage-land-creations.mjs --before="$PWD/data" --after=/tmp/three-island-candidate/after --proofs=/tmp/three-island-candidate/creation-proofs.json --output=/tmp/three-island-migration
WORLDATLAS503_BASELINE_ROOT="$PWD" python3 test/three-island-restoration.test.py
```

Optional original-PBF reproduction uses offline `osmium==4.2.0` (not an application dependency):

```sh
python3 data/macro-improvements/three-island-restoration/reproduce-water.py --root "$PWD"
```

The producer emits a sparse `candidate-patch.json`, exact source geometry proofs, preservation report and an ephemeral after snapshot with read-only links to the hash-pinned baseline parts. Do not mutate the baseline while validating that snapshot. Root publication should compose sparse candidates from #501/#502/#503, recompute immediate child counts from membership, run the shared migration/chronology gates, regenerate bottom-up parent footprints and one canonical grid, revalidate dated products and macro certificates, and perform authorized private-record preflight before activation. Local registry absence cannot prove private hosted-record absence.

Canonical zoom-10 representation checks every candidate cell against actual old ownership runs. Positive counts with zero owned-cell conflict establish representability without assigning water cells arbitrarily. Navigation and shared canonical assets are untouched. `validation.json` and compressed reports capture the executed checks; publication is a separate task.
