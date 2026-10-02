# Complete Namibia replacement stage

This is an isolated, source-backed migration proposal. **It has not changed the live atlas or any historical record.** It corrects the whole defective Namibia input, rather than patching five tiny locations, and records genuine source-boundary conflicts as publication blockers.

Run:

```sh
python scripts/stage-namibia-repair.py
python test/namibia-repair.py
```

The inputs and receipts are retained in `data/retained-geographic-sources/namibia`. The manifest pins original and retained bytes, source URLs and licenses. A fresh checkout reconstructs required caches from those retained files without network access. Each retained file is below the 16 MiB Git limit. The original licensed archive, original 2007 SHP/DBF/SHX/PRJ, source metadata, physical land, reference countries, old atlas identities and neighboring conflicts remain inspectable.

## Source-backed units and complete chains

The proposed framework has **107 COD constituencies as locations → 14 published regional constituency clusters as provinces → two existing WGSRPD geographical areas → Southern Africa region → Southern Africa subcontinent → Africa**. Zambezi uses the Caprivi Strip geographical area; other source clusters use the Namibia geographical area. Parent footprints must be rebuilt from member locations during integration.

An administrative source's level number does not fix the atlas tier. These province groups have actual published membership and contain multiple local territories; the migration does not manufacture 107 identical province/location pairs or invent an unsupported middle administrative tier. All staged parent chains are complete, adjacent and nonempty.

The source is explicitly the **former 107-constituency framework**: source boundary creation/edit date January 1, 2011, humanitarian validity January 9, 2020, later regional labels/partition, and accuracy review January 28, 2025. It is not certified as the current 121-constituency framework. Urban constituency fragmentation, particularly Windhoek, remains a purpose/granularity review item: an electoral constituency is not automatically a city, and no urban rank or unsupported municipal aggregation is inferred.

All 111 previous location IDs and their original geometry/source metadata are archived. The full 111-to-107 correspondence is diagnostic evidence, not authorization to transfer historical evidence. New IDs use stable source constituency codes. Old records remain attached to old identities unless independently dated identity evidence supports a subsequent operation.

## Physical coastline and whole-world overlay

The script inspects all **49,614 atlas locations**, not only adjacent-country names or selected examples. It intersects every spatially relevant footprint with the proposed country coverage, records hashes of every world input part, and archives all conflicting neighboring source footprints.

The independent physical land mask is Natural Earth's `ne_10m_land` from pinned revision `ca96624a56bd078437bca8184e78163e5039ad19`. It is a physical polygon layer, not a substitute country-ownership map. Clipping source territory to this layer removes about **338.43 km²** of source nonland. The resulting strict COD physical footprint is about **823,761.40 km²**. One original ring self-intersection is repaired deterministically without a material area change.

The strict country stage has two concrete blockers:

| Finding | Exhaustive result | Required treatment |
|---|---:|---|
| Overlap with existing neighboring territories | 25 locations, 331.61 km² | Resolve conflicting source boundaries explicitly; neighbors were not silently clipped. |
| Old physical land outside COD and not covered elsewhere | 580 components, 477.76 km² | Restore only source-supported land; never assign a nearest location or donate a grid cell. |

Neighbor conflicts include every affected current source unit in Angola, Botswana, South Africa and Zambia. The unresolved-land layer gives each component an explicit unassigned status. Independent modern country context divides those gaps into Namibia 395.12 km², Botswana 74.72 km², South Africa 5.61 km², Angola 2.27 km² and Zambia 0.039 km². These reference-context shares do not decide historical ownership or assign local territories.

## Geometry-only coastal restoration

The second candidate, `locations-coastal-concordance.geojson.gz`, adds only independently supported coastal pieces. The analysis reviews all **109 original records and all 107 candidate codes**. Original corrupt names are retained as evidence and ignored for matching.

A restoration requires all of the following:

- An original published footprint overlaps the COD candidate by at least 95% of its physical land.
- The combined matching original footprints and the candidate overlap by at least 95% in both directions.
- The added component already existed in the previous atlas's physical land, has no existing neighboring location coverage, and lies in Namibia's independent reference context.
- Its boundary shares an actual line with the independent physical **exterior shoreline**. Inland offsets fail this check; no buffer or nearest-distance assignment substitutes for direct source correspondence.
- Competing source extensions are exposed as disputed geometry and excluded from the safe candidate.

This restores **138.30 km²** across seven COD territories: Epupa, Khorixas, Sesfontein, Opuwo, Naminus/Luderitz, Gibeon and Arandis. There are zero competing extension overlaps and zero additional neighbor overlaps. Each affected location records the restoration method, restored area, original source, physical source and uncertainty. **No historical value is transferred.**

The remaining **339.46 km²** is still visibly unresolved. The original 25 neighbor conflicts also remain. This conservative result supplies a valid source-based coast correction while refusing to classify an inland geopolitical/source offset as a coastline repair. The 95% threshold is a documented correspondence gate, not proof that different source vintages describe the same historical identity.

## Integration and publication gates

The isolated stage is **blocked**, not a finished country replacement. Integration must first resolve or explicitly preserve the uncovered land and conflicting neighboring source claims. It must retain archived entity records, rebuild membership footprints, prepare ownership/environment values against approved new geometry, and run the complete grid audit. A finer grid cannot fix erased or wrongly labeled territory.

Files in `.cache/namibia-repair-stage`:

- `locations.geojson.gz`: strict COD territories clipped to physical land.
- `locations-coastal-concordance.geojson.gz`: strict territories plus supported coast restoration.
- `hierarchy.json`: complete membership chains.
- `archive.geojson.gz`: all old identities and geography.
- `migration.json.gz`: full-world hashes, crosswalk, conflicts and blockers.
- `coastal-extension-review.json.gz`: every source match and component decision.
- `unresolved-land.geojson.gz`: every original uncovered component, explicitly unassigned.

Copies of candidate products and receipts are durably retained beside source proofs in Git, labeled as blocked migration products. Passing structural tests does not close the documented content/source limitations.

## Current-map source-quality annotations

`data/namibia-source-quality-annotations.json` is a **metadata-only plan** for all 111 current Namibia locations and all 24 current parent groups. Generate and validate it with:

```sh
python scripts/prepare-namibia-source-annotations.py
python test/namibia-source-annotations.py
```

`validate_against_current(plan, features, units)` preflights the entire country set before an integrating caller applies patches. It checks every current ID, name, parent, source ID, source membership, reference vintage and canonical JSON geometry hash, plus every ancestor's exact Namibia-descendant IDs. It rejects partial plans and every mutation key except `metadata.source_quality_review`. Integration changes no footprint, identity, name, parent, owner, attribute or historical evidence, and therefore does not require ownership or grid recompilation.

Every location remains `pending-source-replacement`, including the three names whose normalized labels agree with the spatial winner: a plausible individual match does not certify a defective country source. Individual findings distinguish no country overlap, matching labels and differing labels without presenting spelling differences as proven identity errors. Parent annotations explicitly limit their warning to affected Namibia descendants, so an Africa-level annotation does not claim every African source is defective.

The `profile_review` object is suitable for the worldwide review/coverage country row: it gives current counts (111 active locations / 109 original features), proposed counts (107 / 14), source licenses, separate vintages, replacement blockers and retained evidence hashes. Feature/group patches are suitable for the existing collapsed Evidence section. **Do not add technical warnings or fields to the eight-attribute main panel.** Static publication must serve the evidence paths listed under `public_evidence_files`; otherwise the integrator should display source links and omit unresolved internal links rather than create dead links.
