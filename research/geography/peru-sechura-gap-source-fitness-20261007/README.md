# Sechura source-fitness assessment

This packet addresses the one-component, one-contact family `gap-source-batch:5344ddbbdcc5dac52d0580aa` for candidate `physical-component:d15872b646c35d39fa1f0cc1bda6edc9775a46edd3c2c5278690d770ef211708` and current contact `gb:PER:ADM2:86281439B13089313750619` (Sechura). It reuses the administrative-role/crosswalk review and limited GSHHG screen in closed #496. The distinct question is the source product used by the pinned Atlas recipe: the recipe changes the registry URL to `_simplified.geojson`, while #496 retained the unsimplified product.

## Result

The exact simplified product was authenticated as 4,310,497 raw bytes, SHA-256 `4986d514b9898f7c415febd47d2ae302f79f5a0d23434cc81fb2bdbfaec623a3`, containing 196 features. The retained unsimplified product is 31,291,639 raw bytes, SHA-256 `58d0720bc01abd27bd02fb73d2ee8443fc6067352d97b752d100a18e3b97bb58`, also containing 196 features. For this single candidate, each whole product has one intersecting source feature: Sechura, shapeID `86281439B13089313750619`. In both products the Sechura feature covers the complete candidate (100% candidate-area coverage, approximately 27.6976 m² in the local projected calculation). Thus the simplified-versus-unsimplified product choice does not change this candidate's source-relative relationship.

The current Atlas Sechura feature has 81 coordinates, compared with 180 in the simplified feature and 1,680 in the unsimplified feature. It intersects the candidate only at its boundary: zero positive-area overlap and zero area coverage. This is a geometry relationship among retained files; it does not identify how or why the current geometry differs.

## Source and method limits

The source metadata records a 2020 represented-year claim, Provinces, IGN/OCHA ROLAC attribution, CC BY 3.0 IGO, a 2023-01-19 source update, and a Dec 12 2023 build. These are publisher/registry claims. They do not independently establish effective dates, authority, positional accuracy, license applicability, or terms. No registration-accuracy evidence or source-to-current feature lineage is available here.

Topological predicates use the original longitude/latitude coordinates without snapping, repair, or normalization. Areas use planar EPSG:32717 for this local candidate only and are descriptive diagnostics, not survey measurements or positional-accuracy estimates. The archived GSHHG 2.3.7/2017-06-15 support is unapproved, its observation dates are heterogeneous, and its one-centroid screen from #496 is limited. No mapped water support does not establish dry land. The source date, authority, licensing applicability, positional accuracy/registration, cause of Atlas geometry differences, physical land/water, complete partition, and ownership remain unknown.

No global producer was rerun. No source was imported, geometry repaired, snapped, buffered, simplified, filled, or approved. This packet makes no territorial, ownership, release, or publication finding. See `analysis.json`, `execution.json`, `runs/`, and `inputs/upstream/` for exact inputs, bounded code, selected complete feature bodies, reproducibility outputs, and custody. The initial parser failure is retained in `preliminary-attempt-1-stderr.txt` and `preliminary-attempts.json`; the corrected method concatenates all 14 ordered family shards before parsing the selected row.
