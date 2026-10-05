# Central Africa interior batch 4 evidence packet

Issue #463 owns this directory and exactly 227 pinned location IDs. Research snapshot date: 2026-10-05 UTC. Baseline for the initial identity inventory: `b7aab8b8d353eb3510cf7323da7bc2dcde10147b`; the working branch was rebased onto the later `origin/main` commit `18ef568` before implementation. No core geography or production data was changed.

## Contents and reproduction

- `scope.json`: retained issue scope and exact member IDs.
- `issue-context.json`: issue contract and acceptance snapshot.
- `baseline-unit-inventory.json`: per-ID Atlas name, parent, reference owner, source ID/role/vintage, internal area code, and source-file hashes at the initial baseline.
- `sources/geoboundaries-9469f09/`: licensed pinned source GeoJSONs, provider API metadata responses, and provider citation/use files. Exact bytes, hashes, retrieval timestamps, source vintage, roles and license fields are in `source-inventory.json`.
- `location-assessments.json`: one individual assessment for each of 227 IDs. Identity resolution is a reproducibility control only, not proof of geography.
- `source-geometry-screen.json`: reproducible per-feature GeoJSON geometry type, component/ring/vertex counts and coordinate bounds. This is a geometry composition screen, not a topology or boundary correctness test.
- `province-assessments.json`: all 38 scoped province groups, exact baseline members/counts, linked to individual assessments.
- `area-assessments.json`: five area scope counts and explicit crosswalk limitation.
- `findings.json`: bounded sourced findings and engineering/restoration handoffs.
- `reproduce.py`: reads retained source files and packet scope and regenerates location, geometry composition, province and area assessments. Run from the repository root: `python3 data/regional-review/regional-review-42fc12dc97387a2a/reproduce.py`.
- `reproduction.json`: exact reproduction inputs/outputs and hashes (generated after final evidence edits).

## Geographic assessment

The evidence establishes that the issue's 227 IDs resolve to the retained baseline and pinned provider features. It does **not** establish legal role, exact current parent, boundary correctness, or roster completeness for the units. Assessments therefore leave 225 units at `insufficient-evidence`. The two `correction-needed` entries are bounded source-supported parent/tier concerns: Doutsita/Doutsila in Gabon and Elobey Chico in Equatorial Guinea. Neither recommendation certifies a geometry or authorizes editing shared hierarchy.

The source layer level is not treated as a territorial tier. COD ADM2 metadata itself says “territory, city” (mixed role); GAB ADM2 says “Department”; GNQ ADM2 provider metadata says “Unknown”, contrary to the issue’s migrated “District” description. Geometry composition screening found all 169 COD features as Polygon; Gabon’s 30 include one multipart feature (Bendjè); GNQ’s 28 include multipart Cogo (4 polygon components), Elobey Grande (2), and Annobón (2). These components may represent islands or coastlines, so they warrant sourced feature-level review and do not prove disconnected political units. No scoped features are empty or unnamed. Geometry validity, overlaps, shared-edge topology, exact boundaries, city fragmentation and legal multipart meaning are not established. COD source vintage is 2019, GAB 2018, GNQ 2013. COD provides 189 features, of which 169 are in this packet. GAB provides 49 features while the Ministry source reports 48 departments from DGAT May 2016. GNQ has 28 features; its 2013 vintage predates Djibloho's creation and the reported 2025–2026 changes. These differences require roster and boundary review; counts do not resolve them.

The issue's five area scopes are Congo (1 of 47), Equatorial Guinea (22 of 22), Gabon (30 of 49), Gulf of Guinea Islands (5 of 7), and Democratic Republic of the Congo (169 of 189). Exact per-location workload membership was reconstructed by following each pinned location's baseline province parent to its area parent, and these member counts match the issue pins. Internal codes still show diagnostic differences (including Doutsita coded `CON` and GNQ Elobey features coded `GAB`); those application codes are not proof of national territory or island affiliation. The area hierarchy identifies its basis as WGSRPD level 3, a botanical recording geography whose Botanical Country tier may ignore purely political factors. That source purpose alone does not demonstrate that these area groupings serve the Atlas's intended general geographic purpose. M49 was used as an independent statistical naming/classification cross-check only; it does not certify physical boundaries or all local territories. Area membership is reproduced in `area-assessments.json`; area-purpose suitability and boundary correspondence remain open. Preserve outer scopes and coordinate any future shared parent/source predecessor work across neighboring packets.

The separately owned 19-ID Gabon issue #866 is a neighboring source/country crosswalk, not overlapping source subjects; its 49-vs-48 count question is cross-vintage and remains unresolved for this packet's 30 Gabon subjects. No neighboring packet's actual Central African country-city subjects or evidence were supplied in this issue scope, so this packet records that granularity comparison as unresolved instead of treating administrative level numbers as comparable. Fragmented city territories, city/territory roles, anonymous remainders, disconnected geometry, omissions, and exact boundary alignment remain unresolved at unit level unless a finding explicitly says otherwise.

## Source and rights notes

The three geoBoundaries layers are retained as their exact pinned 9469f09 release bytes under their stated CC BY 3.0 IGO, CC BY 3.0, and CC BY 4.0 terms, alongside the exact retrieved provider metadata and citation/use files. The API metadata was retrieved from a `current` endpoint; it is retained byte-for-byte, but its download link names the pinned commit. It is provider metadata, not a signed release attestation. Retrieval timestamps and SHA-256 hashes are recorded per object.

Official DRC and Gabon legal/ministry sources and Equatorial Guinea laws/pages were inspected for facts, but raw copies are not retained where fetching failed or reuse terms are unclear. `source-inventory.json` records restoration URLs, inspection limits and transient raw hashes where available. Restore those primary materials and revalidate their exact contents before implementing follow-ups.

## Engineering handoff and acceptance boundary

Engineering should investigate the exact IDs and claims in `findings.json`, obtain current primary legal rosters and permissible authoritative boundary inputs, and preserve existing IDs/release pins until crosswalk and inter-region review are accepted. Current GNQ law/roster (#868), DRC mixed role roster (#870), Doutsita/Doutsila parent/name crosswalk (#871), and Gulf island parent/code relationships (#869) need bounded follow-up issues. The Gabon national count/vintage question also intersects the disjoint 19-ID review in #866. These children depend on this packet and remain blocked. No source gap is closed by structure checks. This packet does not certify the region, approve migration or import, authorize publication, or change hierarchy.
