# Bangladesh interior batch 1 evidence packet (#78)

Research date: 2026-10-05 UTC. This packet covers the 64 exact Bangladesh district IDs in the issue and writes only to this owned directory. Baseline is fresh `main` commit `ddf9a8d02e808f40099d55878a301478c8c5eb64`.

## Files and reproduction

- `scope.json` and `issue-context.json`: exact issue scope and contract snapshot.
- `sources/geoboundaries-9469f09/`: lawful geoBoundaries ADM1 and ADM2 source files and their exact provider metadata. Source hashes and attribution/license facts are in `source-inventory.json`.
- `baseline-unit-inventory.json`: each issue ID's frozen Atlas name, parent, source name and declared source vintage, pinned to the current membership projection.
- `source-inventory.json`: source role, vintage, licensing, current government roster inspections, retrieval and restoration limits.
- `location-assessments.json`: one assessment per scoped location. The justified finding applies only to administrative identity and district tier, not geometry.
- `province-assessments.json`: exact member counts and individual division-name/parent evidence state.
- `area-assessment.json`: area purpose/completeness limits.
- `source-geometry-screen.json`: Polygon/MultiPolygon composition and coordinate bounds; this is not a geometry validity or boundary test.
- `scope-risk-screen.json`: explicit outcomes for the issue's city fragmentation, provincial-scale units, unnamed/repeated features, multipart geography, island completeness, parent quality and neighboring granularity questions.
- `findings.json`: bounded engineering and evidence follow-ups.
- `reproduce.py` and `reproduction.json`: deterministic source-hash, native-ID, issue-roster and membership checks. Run from repository root with `python3 data/regional-review/regional-review-aeea5c053fbdeb8d/reproduce.py`.

## Findings and limits

All 64 issue IDs resolve one-to-one to the full geoBoundaries BGD ADM2 layer, whose metadata names the role as “district,” vintage 2020 and source as Bangladesh Bureau of Statistics (BBS), OCHA ROAP. The full source identifies 64 features; each source shapeName matches its Atlas name. The Bangladesh National Portal independently reports 64 districts under eight divisions. That supports the administrative subject identity and district tier. The geoBoundaries metadata also points to an HDX dataset titled as boundaries “as of 2015”; neither date establishes the legal effective date of every line.

The Atlas and pinned 2020 ADM1 layer retain the spellings Chittagong, Rajshani and Barisal. The current official division list uses Chattogram, Rajshahi and Barishal. These three scoped province names need a sourced engineering correction with stable IDs preserved; bounded follow-up #883 owns that work. The current list does not itself prove district-to-division membership. All eight division parent assignments therefore remain `insufficient-evidence` pending a dated primary crosswalk; no geometric containment inference was used. Follow-up #884 owns the exact 64-district roster/parent/boundary source restoration and coastal coverage gap.

The Bangladesh government portal pages were inspected on 2026-10-05, but direct retrieval returned HTTP 403 and the page reuse terms were not established. Their raw bytes are not retained. The source inventory gives exact restoration URLs and observed facts. Restore and revalidate those pages before any implementation that depends on exact labels or administrative orders.

The geoBoundaries files are lawfully retained under their provider-declared CC BY 3.0 IGO license with attribution. The provider's layer-specific citation/use file URL returned 404; this packet records the provider, source, pinned repository revision and source attribution instead of inventing a citation. The 2020 ADM1/ADM2 pair provides complete source rosters and a useful hierarchy comparison, but is not an independently verified legal boundary product. Geometry components, portal counts and shape IDs do not establish exact boundaries, islands/coastal completeness, topology or geographic-purpose suitability.

This packet does not certify the Bengal and Bangladesh region, approve the source polygons, change a boundary/ID/release or authorize location attribute imports. #78 completion means its complete research scope is documented; bounded open findings remain explicit.
